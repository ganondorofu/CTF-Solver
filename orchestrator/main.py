"""
CTF Solver main orchestrator (v2: autonomous agent mode)

Agents run persistently and autonomously decide which challenges to solve,
when to submit flags, and when to give up. The orchestrator only handles:
  1. CTFd relay proxy (security boundary)
  2. Docker container lifecycle (start, monitor, restart)
  3. Log collection
"""

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .ctfd_relay import CTFdRelay
from .docker_manager import DockerManager
from .log_archiver import archive_old_logs, cleanup_old_archives
from .prompt_generator import PromptGenerator

# Global state for graceful shutdown
_shutdown_flag = False
_docker_mgr = None
_relay = None
_container_infos = []


def setup_logging():
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format, force=True)
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    fh = logging.FileHandler(log_dir / "orchestrator.log", mode="a", encoding="utf-8")
    fh.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(fh)


logger = logging.getLogger(__name__)


def _signal_handler(signum, frame):
    """Handle SIGINT/SIGTERM gracefully"""
    global _shutdown_flag, _docker_mgr, _relay, _container_infos
    if _shutdown_flag:
        logger.warning("Force shutdown (second signal)")
        sys.exit(1)
    
    _shutdown_flag = True
    logger.info("Shutdown signal received - cleaning up...")
    
    if _docker_mgr:
        logger.info("Stopping containers...")
        _docker_mgr.stop_all(_container_infos)
        _docker_mgr.stop_all_ctf_containers()
    
    if _relay:
        _relay.stop()
    
    logger.info("=== CTF Solver stopped ===")
    sys.exit(0)


def _resolve_env(value: str) -> str:
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1], "")
    return value


def load_config(config_path: str = "config/config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["ctfd"]["url"] = _resolve_env(cfg["ctfd"]["url"])
    cfg["ctfd"]["token"] = _resolve_env(cfg["ctfd"]["token"])
    return cfg


def load_agents(agents_path: str = "config/agents.yaml") -> dict:
    with open(agents_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_enabled_agents(agents_cfg: dict) -> dict[str, dict]:
    """Expand enabled agents with profile/instance multiplexing."""
    profiles_base = Path.home() / ".ctf-solver" / "profiles"
    result = {}
    for name, cfg in agents_cfg.get("agents", {}).items():
        if cfg.get("enabled") is False:
            continue
        auth_profiles = cfg.get("auth_profiles", [])
        if auth_profiles:
            default_ipp = int(cfg.get("instances_per_profile", 1))
            counter = 1
            total = 0
            for entry in auth_profiles:
                if isinstance(entry, dict) and "models" in entry:
                    for m in entry["models"]:
                        total += int(m.get("instances", 1))
                else:
                    n = int(entry.get("instances", entry.get("weight", default_ipp))) if isinstance(entry, dict) else default_ipp
                    total += n
            if total == 0:
                continue
            for entry in auth_profiles:
                if isinstance(entry, dict):
                    profile_name = entry["name"]
                    profile_env_vars = entry.get("env_vars", {})
                else:
                    profile_name = str(entry)
                    profile_env_vars = {}
                # Build (model_override, instance_count, env_vars) specs
                if isinstance(entry, dict) and "models" in entry:
                    model_specs = [
                        (m.get("model"), int(m.get("instances", 1)),
                         {**profile_env_vars, **m.get("env_vars", {})})
                        for m in entry["models"]
                    ]
                else:
                    n = int(entry.get("instances", entry.get("weight", default_ipp))) if isinstance(entry, dict) else default_ipp
                    model_override = entry.get("model") if isinstance(entry, dict) else None
                    model_specs = [(model_override, n, profile_env_vars)]
                for model_override, n, merged_env in model_specs:
                    if n <= 0:
                        continue
                    instance_cfg = {**cfg, "_profile": profile_name}
                    if model_override:
                        instance_cfg["model"] = model_override
                    profile_dir_path = profiles_base / name / profile_name
                    if profile_dir_path.exists():
                        instance_cfg["_profile_dir"] = str(profile_dir_path)
                    if merged_env:
                        instance_cfg["_profile_env_vars"] = merged_env
                    for _ in range(n):
                        key = name if total == 1 else f"{name}#{counter}"
                        result[key] = instance_cfg
                        counter += 1
        else:
            instances = cfg.get("instances", None)
            if instances is None:
                enabled = cfg.get("enabled", False)
                instances = 1 if enabled else 0
            instances = int(instances)
            if instances <= 0:
                continue
            if instances == 1:
                result[name] = cfg
            else:
                for i in range(1, instances + 1):
                    result[f"{name}#{i}"] = cfg
    return result


def _free_port(port: int):
    """Kill any process holding the given port so WebUI can bind."""
    import subprocess
    try:
        out = subprocess.check_output(
            ["ss", "-tlnp", f"sport = :{port}"],
            text=True, stderr=subprocess.DEVNULL,
        )
        for line in out.splitlines():
            # extract pid from e.g. pid=12345
            for part in line.split(","):
                if part.strip().startswith("pid="):
                    pid = int(part.strip().split("=")[1].split(")")[0])
                    if pid != os.getpid():
                        logger.warning("Killing stale process %d on port %d", pid, port)
                        os.kill(pid, signal.SIGKILL)
    except Exception:
        pass


def main():
    global _shutdown_flag, _docker_mgr, _relay, _container_infos
    
    load_dotenv()
    
    # Register signal handlers early
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    parser = argparse.ArgumentParser(description="CTF Solver v2 - Autonomous Agent Mode")
    parser.add_argument("--build-image", action="store_true", help="Build Docker base image and exit")
    parser.add_argument("--agent", type=str, help="Only run specific agent types (comma-separated)")
    parser.add_argument("--challenge", type=str, help="Only these challenge IDs (comma-separated)")
    parser.add_argument("--skip", type=str, help="Skip these challenge IDs (comma-separated)")
    parser.add_argument("--list", action="store_true", help="List challenges and exit")
    parser.add_argument("--no-webui", action="store_true", help="Disable WebUI dashboard")
    parser.add_argument("--webui-port", type=int, default=8080, help="WebUI port (default: 8080)")
    args = parser.parse_args()

    # Load config first to get log settings
    config = load_config()
    
    # Archive old logs before setting up new logging
    logs_config = config.get("logs", {})
    if logs_config.get("archive_on_start", True):
        archive_old_logs()
        cleanup_old_archives(keep_count=logs_config.get("keep_archives", 10))

    setup_logging()
    agents_cfg = load_agents()

    ctfd_url = config["ctfd"]["url"]
    ctfd_token = config["ctfd"]["token"]

    if not ctfd_url or not ctfd_token:
        logger.error("CTFd URL/token not configured (check .env)")
        sys.exit(1)

    docker_mgr = DockerManager(
        agents_config=agents_cfg.get("agents", {}),
        docker_config=agents_cfg.get("docker", {}),
    )
    _docker_mgr = docker_mgr  # Store for signal handler

    if args.build_image:
        docker_mgr.build_base_image()
        return

    if args.list:
        from .ctfd_client import CTFdClient
        client = CTFdClient(ctfd_url, ctfd_token)
        challenges = client.get_challenges()
        solved_ids = client.get_solved_challenge_ids()
        for c in sorted(challenges, key=lambda x: x.get("value", 0)):
            mark = "V" if c["id"] in solved_ids else " "
            print(f"  [{mark}] ID:{c['id']:4d} | {c.get('value',0):4d}pts | {c.get('category',''):12s} | {c.get('name','')}")
        return

    enabled = get_enabled_agents(agents_cfg)
    if args.agent:
        allowed = set(args.agent.split(","))
        enabled = {k: v for k, v in enabled.items() if v.get("type", k.split("#")[0]) in allowed}

    if not enabled:
        logger.error("No enabled agents found")
        sys.exit(1)

    logger.info("=== CTF Solver v2: Autonomous Agent Mode ===")
    logger.info("Enabled agents: %s", list(enabled.keys()))

    shared_dir = Path("workspace/shared")
    shared_dir.mkdir(parents=True, exist_ok=True)

    # チャレンジフィルタ
    only_ids = set(int(x) for x in args.challenge.split(",")) if args.challenge else None
    skip_ids = set(int(x) for x in args.skip.split(",")) if args.skip else None
    if only_ids:
        logger.info("Challenge filter (only): %s", only_ids)
    if skip_ids:
        logger.info("Challenge filter (skip): %s", skip_ids)

    relay = CTFdRelay(
        ctfd_url=ctfd_url,
        ctfd_token=ctfd_token,
        hints_config=config.get("hints", {}),
        shared_dir=str(shared_dir.resolve()),
        only_challenge_ids=only_ids,
        skip_challenge_ids=skip_ids,
        ctf_ended=config.get("ctfd", {}).get("ended", False),
    )
    relay.start()
    _relay = relay  # Store for signal handler

    prompt = PromptGenerator().generate_autonomous()

    container_infos = []
    errors = []

    def _start_one(agent_name, agent_cfg):
        try:
            info = docker_mgr.run_autonomous_agent(
                agent_name=agent_name,
                agent_cfg=agent_cfg,
                relay_url=relay.url,
                relay_token=relay.relay_token,
                prompt=prompt,
                shared_dir=str(shared_dir.resolve()),
            )
            logger.info("Agent started: %s (container=%s)", agent_name, info["container"].short_id)
            return info
        except Exception as e:
            logger.error("Agent start failed: %s: %s", agent_name, e)
            return None

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=len(enabled)) as executor:
        futures = {
            executor.submit(_start_one, name, cfg): name
            for name, cfg in enabled.items()
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                container_infos.append(result)
    
    _container_infos = container_infos  # Store for signal handler

    if not container_infos:
        logger.error("No agents could be started")
        relay.stop()
        sys.exit(1)

    # WebUI 自動起動
    if not args.no_webui:
        try:
            import socket
            import threading
            import uvicorn
            from webui.app import app as webui_app, configure as webui_configure

            # ポートを掴んでいるプロセスを強制解放
            _free_port(args.webui_port)

            webui_configure(relay.url, relay.relay_token, container_infos)
            webui_thread = threading.Thread(
                target=uvicorn.run,
                kwargs={"app": webui_app, "host": "0.0.0.0", "port": args.webui_port, "log_level": "warning"},
                daemon=True,
            )
            webui_thread.start()
            logger.info("WebUI started: http://0.0.0.0:%d", args.webui_port)
        except Exception as e:
            logger.warning("WebUI start failed (continuing without): %s", e)

    logger.info("=== All agents started - monitoring (Ctrl+C to stop) ===")
    try:
        docker_mgr.monitor_containers(
            container_infos,
            relay_url=relay.url,
            relay_token=relay.relay_token,
            prompt=prompt,
            shared_dir=str(shared_dir.resolve()),
        )
    except KeyboardInterrupt:
        logger.info("Ctrl+C detected - shutting down...")
    finally:
        logger.info("Stopping all containers...")
        docker_mgr.stop_all(container_infos)
        docker_mgr.stop_all_ctf_containers()  # Stop any orphaned containers
        relay.stop()
        logger.info("=== CTF Solver stopped ===")


if __name__ == "__main__":
    main()
