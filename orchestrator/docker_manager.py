"""
Docker Manager (v2: autonomous agent mode)

Manages container lifecycle: build image, prepare workspace,
launch persistent agent containers, monitor, and stop.
"""

import logging
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

import docker
from docker.errors import ContainerError, ImageNotFound, APIError

import re

logger = logging.getLogger(__name__)

PROFILES_BASE = Path.home() / ".ctf-solver" / "profiles"

# コンソールに表示する重要キーワード（ファイルには全て書き込む）
_CONSOLE_KEYWORDS = re.compile(
    r"FLAG_CONFIRMED|FLAG_SUBMITTED|CHALLENGE_SOLVED|CHALLENGE_CLAIMED"
    r"|=== Challenge|error|Error|ERROR|exception|Exception"
    r"|Traceback|timeout|Timeout",
    re.IGNORECASE,
)


class DockerManager:
    """Dockerコンテナのライフサイクルを管理するクラス"""

    AUTH_CREDENTIAL_FILES: dict[str, dict[str, list[str] | None]] = {
        "claude_code": {
            "~/.claude": [".credentials.json", "settings.json"],
        },
        "claude_zai": {
            "~/.claude": [".credentials.json", "settings.json"],
        },
        "kimi": {
            "~/.claude": [".credentials.json", "settings.json"],
        },
        "claude_ollama": {
            "~/.claude": [".credentials.json", "settings.json"],
        },
        "copilot_cli": {
            "~/.copilot": ["config.json", "mcp-config.json"],
        },
        "gemini_cli": {
            "~/.gemini": None,
            "~/.config/gemini-cli": None,
        },
        "codex_cli": {
            "~/.codex": ["auth.json"],
        },
    }

    PROFILE_SUBDIRS: dict[str, list[tuple[str, str, list[str] | None]]] = {
        "claude_code": [
            ("claude", "/home/agent/.claude", [".credentials.json", "settings.json"]),
        ],
        "claude_zai": [
            ("claude", "/home/agent/.claude", [".credentials.json", "settings.json"]),
        ],
        "kimi": [
            ("claude", "/home/agent/.claude", [".credentials.json", "settings.json"]),
        ],
        "claude_ollama": [
            ("claude", "/home/agent/.claude", [".credentials.json", "settings.json"]),
        ],
        "copilot_cli": [
            ("copilot", "/root/.copilot", ["config.json", "mcp-config.json"]),
        ],
        "gemini_cli": [
            ("gemini", "/root/.gemini", None),
        ],
        "codex_cli": [
            ("codex", "/root/.codex", ["auth.json"]),
        ],
    }

    AUTH_MOUNTS = {
        "claude_code":   ["~/.claude"],
        "claude_zai":    ["~/.claude"],
        "kimi":          ["~/.claude"],
        "claude_ollama": ["~/.claude"],
        "copilot_cli":   ["~/.copilot"],
        "gemini_cli":    ["~/.gemini", "~/.config/gemini-cli"],
        "codex_cli":     ["~/.codex/auth.json"],
    }

    def __init__(self, agents_config: dict, docker_config: dict):
        self.agents_config = agents_config
        self.docker_config = docker_config or {}
        try:
            self.client = docker.from_env(timeout=300)
            self.client.ping()
        except docker.errors.DockerException as e:
            if "permission denied" in str(e).lower():
                raise RuntimeError(
                    "Docker permission error: sudo usermod -aG docker $USER && newgrp docker"
                ) from e
            raise RuntimeError(f"Docker connection error: {e}") from e

    # -- Docker image build --

    def build_base_image(self, dockerfile_dir: str = "agents/base"):
        path = Path(dockerfile_dir)
        logger.info("Building base image: %s", path)
        self.client.images.build(
            path=str(path),
            dockerfile="Dockerfile.base",
            tag="ctf-agent-base:latest",
            rm=True,
        )
        logger.info("Base image build complete")

    # -- Env var resolution --

    def _resolve_env_vars(self, agent_cfg: dict) -> dict:
        def _resolve_one(value) -> str:
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                return os.environ.get(value[2:-1], "")
            return str(value)
        env = {}
        for key, value in agent_cfg.get("env_vars", {}).items():
            env[key] = _resolve_one(value)
        for key, value in agent_cfg.get("_profile_env_vars", {}).items():
            env[key] = _resolve_one(value)
        return env

    # -- Auth mount construction --

    def _create_ephemeral_from_profile(
        self, agent_type: str, profile_dir: Path,
    ) -> tuple[dict, list[Path], list[tuple[Path, Path]]]:
        """Returns (mounts, temp_dirs, writeback_pairs) where writeback_pairs is [(temp_dir, original_src)]."""
        subdirs = self.PROFILE_SUBDIRS.get(agent_type, [])
        if not subdirs:
            return {}, [], []
        mounts: dict = {}
        temp_dirs: list[Path] = []
        writeback_pairs: list[tuple[Path, Path]] = []
        for subdir_name, container_path, files_to_copy in subdirs:
            src = profile_dir / subdir_name
            if not src.exists():
                continue
            tmp = Path(tempfile.mkdtemp(prefix="ctf-auth-"))
            temp_dirs.append(tmp)
            writeback_pairs.append((tmp, src))
            try:
                if files_to_copy is None:
                    for item in src.iterdir():
                        dst = tmp / item.name
                        if item.is_file():
                            shutil.copy2(str(item), str(dst))
                        elif item.is_dir():
                            shutil.copytree(str(item), str(dst))
                else:
                    for fname in files_to_copy:
                        f = src / fname
                        if not f.exists():
                            continue
                        if f.is_file():
                            shutil.copy2(str(f), str(tmp / fname))
                        else:
                            shutil.copytree(str(f), str(tmp / fname))
            except Exception as e:
                logger.warning("Profile copy failed %s: %s", src, e)
            mounts[str(tmp)] = {"bind": container_path, "mode": "rw"}
        return mounts, temp_dirs, writeback_pairs

    def _create_ephemeral_auth(
        self, agent_type: str, agent_cfg: dict, agent_name: str,
    ) -> tuple[dict, list[Path], list[tuple[Path, Path]]]:
        """Create ephemeral auth directory copies for container mounting.
        Returns (mounts, temp_dirs, writeback_pairs).
        """
        profile_dir_str = agent_cfg.get("_profile_dir")
        if profile_dir_str:
            profile_dir = Path(profile_dir_str)
            return self._create_ephemeral_from_profile(agent_type, profile_dir)

        cred_map = self.AUTH_CREDENTIAL_FILES.get(agent_type)
        if cred_map is None:
            return self._get_auth_mounts(agent_type), [], []

        auth_profiles: list = agent_cfg.get("auth_profiles", [])
        primary_override: str | None = None
        if auth_profiles:
            idx = (int(agent_name.split("#")[1]) - 1) if "#" in agent_name else 0
            idx = idx % len(auth_profiles)
            entry = auth_profiles[idx]
            primary_override = entry.get("name", "") if isinstance(entry, dict) else str(entry)

        primary_dir = next(iter(cred_map), None)
        effective_cred_map: dict[str, list[str] | None] = {}
        for auth_path_str, files_to_copy in cred_map.items():
            if primary_override and auth_path_str == primary_dir:
                effective_cred_map[primary_override] = files_to_copy
            else:
                effective_cred_map[auth_path_str] = files_to_copy

        mounts: dict = {}
        temp_dirs: list[Path] = []
        writeback_pairs: list[tuple[Path, Path]] = []
        for auth_path_str, files_to_copy in effective_cred_map.items():
            host_path = Path(auth_path_str).expanduser()
            if not host_path.exists():
                continue
            tmp_dir = Path(tempfile.mkdtemp(prefix="ctf-auth-"))
            temp_dirs.append(tmp_dir)
            # writeback先: ファイル単体の場合はその親、ディレクトリの場合はそのまま
            writeback_src = host_path.parent if host_path.is_file() else host_path
            writeback_pairs.append((tmp_dir, writeback_src))
            try:
                if host_path.is_file():
                    shutil.copy2(str(host_path), str(tmp_dir / host_path.name))
                elif files_to_copy is None:
                    for item in host_path.iterdir():
                        dst = tmp_dir / item.name
                        if item.is_file():
                            shutil.copy2(str(item), str(dst))
                        elif item.is_dir():
                            shutil.copytree(str(item), str(dst))
                else:
                    for fname in files_to_copy:
                        src = host_path / fname
                        if not src.exists():
                            continue
                        dst = tmp_dir / fname
                        if src.is_file():
                            shutil.copy2(str(src), str(dst))
                        else:
                            shutil.copytree(str(src), str(dst))
            except Exception as e:
                logger.warning("Auth file copy failed %s: %s", host_path, e)

            if agent_type in ("claude_code", "claude_ollama", "claude_zai", "kimi") and "/.claude" in auth_path_str:
                container_path = "/home/agent/.claude"
            else:
                container_path = auth_path_str.replace("~", "/root")
            mounts[str(tmp_dir)] = {"bind": container_path, "mode": "rw"}

        return mounts, temp_dirs, writeback_pairs

    def _get_auth_mounts(self, agent_type: str) -> dict:
        mounts = {}
        for auth_path in self.AUTH_MOUNTS.get(agent_type, []):
            host_path = Path(auth_path).expanduser()
            if host_path.exists():
                if agent_type in ("claude_code", "claude_ollama", "claude_zai", "kimi") and "/.claude" in auth_path:
                    container_path = "/home/agent/.claude"
                else:
                    container_path = auth_path.replace("~", "/root")
                mode = "ro" if host_path.is_file() else "rw"
                mounts[str(host_path)] = {"bind": container_path, "mode": mode}
        return mounts

    # -- Workspace preparation (autonomous mode) --

    def _prepare_workspace(self, agent_name: str, prompt: str) -> Path:
        ws = Path("workspace") / agent_name.replace("#", "_")
        ws.mkdir(parents=True, exist_ok=True)
        (ws / "challenges").mkdir(exist_ok=True)
        (ws / "state").mkdir(exist_ok=True)

        (ws / "prompt.txt").write_text(prompt, encoding="utf-8")

        base_dir = Path(__file__).parent.parent / "agents" / "base"
        for script in ("list_challenges.sh", "get_challenge.sh", "submit_flag.sh", "get_status.sh"):
            src = base_dir / script
            if src.exists():
                shutil.copy2(src, ws / script)
                (ws / script).chmod(0o755)

        search_mcp = base_dir / "search_mcp.py"
        if search_mcp.exists():
            shutil.copy2(search_mcp, ws / "search_mcp.py")

        knowledge_dir = Path(__file__).parent.parent / "knowledge"
        if knowledge_dir.exists():
            try:
                from .knowledge_manager import KnowledgeManager
                km = KnowledgeManager(knowledge_dir)
                km.copy_to_workspace(ws)
            except Exception as e:
                logger.debug("Knowledge copy skipped: %s", e)

        return ws

    # -- Container launch (autonomous mode) --

    def run_autonomous_agent(
        self,
        agent_name: str,
        agent_cfg: dict,
        relay_url: str,
        relay_token: str,
        prompt: str,
        shared_dir: str | None = None,
    ) -> dict:
        ws = self._prepare_workspace(agent_name, prompt)

        env = self._resolve_env_vars(agent_cfg)
        env["AGENT_NAME"] = agent_name
        env["AGENT_TYPE"] = agent_cfg.get("type", agent_name)
        env["AGENT_TIMEOUT"] = "0"
        env["RELAY_URL"] = relay_url
        env["RELAY_TOKEN"] = relay_token

        model = agent_cfg.get("model")
        if model:
            env["AGENT_MODEL"] = str(model)
            agent_type = agent_cfg.get("type", "")
            if agent_type in ("claude_zai", "claude_ollama", "claude_code"):
                env.setdefault("ZAI_MODEL_HAIKU", str(model))
                env.setdefault("ZAI_MODEL_SONNET", str(model))
                env.setdefault("ZAI_MODEL_OPUS", str(model))
        if "ollama_model" in agent_cfg:
            env["OLLAMA_MODEL"] = agent_cfg["ollama_model"]

        resources = self.docker_config.get("resources", {})

        volumes = {
            str(ws.resolve()): {"bind": "/workspace", "mode": "rw"},
        }

        if shared_dir:
            volumes[shared_dir] = {"bind": "/workspace/shared", "mode": "ro"}

        auth_mounts, temp_dirs, writeback_pairs = self._create_ephemeral_auth(
            agent_cfg.get("type", agent_name), agent_cfg, agent_name,
        )
        volumes.update(auth_mounts)

        # 非rootユーザーで実行（デフォルト: 現在のユーザーUID/GID）
        docker_user = self.docker_config.get("user")
        if not docker_user:
            import os
            docker_user = f"{os.getuid()}:{os.getgid()}"

        container = self.client.containers.run(
            image="ctf-agent-base:latest",
            command="/bin/bash /entrypoint.sh",
            environment=env,
            volumes=volumes,
            network_mode=self.docker_config.get("network_mode", "host"),
            user=docker_user,
            mem_limit=resources.get("memory", "4g"),
            cpu_count=resources.get("cpu_count", 2),
            detach=True,
            auto_remove=False,
        )

        logger.info(
            "Container started: %s (agent=%s, type=%s)",
            container.short_id, agent_name, agent_cfg.get("type", "unknown"),
        )

        return {
            "container": container,
            "workspace": ws,
            "temp_dirs": temp_dirs,
            "writeback_pairs": writeback_pairs,
            "agent_name": agent_name,
            "agent_cfg": agent_cfg,
        }

    # -- Container monitoring --

    def monitor_containers(self, container_infos: list[dict], check_interval: int = 30,
                           relay_url: str = "", relay_token: str = "",
                           prompt: str = "", shared_dir: str = ""):
        stop_event = threading.Event()

        for info in container_infos:
            t = threading.Thread(
                target=self._stream_logs,
                args=(info["container"], info["agent_name"], info["workspace"]),
                daemon=True,
            )
            t.start()

        while not stop_event.is_set():
            for info in container_infos:
                try:
                    info["container"].reload()
                    status = info["container"].status
                    if status == "exited" and not info.get("_exit_handled"):
                        exit_code = info["container"].attrs.get("State", {}).get("ExitCode", -1)
                        logger.info(
                            "Agent %s: exited (code=%s)", info["agent_name"], exit_code,
                        )
                        if not info.get("_writeback_done"):
                            self._writeback_auth(info)
                            info["_writeback_done"] = True
                        info["_exit_handled"] = True

                        # Auto-restart if relay info available
                        if relay_url and prompt:
                            try:
                                info["container"].remove(force=True)
                                for tmp in info.get("temp_dirs", []):
                                    shutil.rmtree(tmp, ignore_errors=True)
                                logger.info("Restarting agent: %s", info["agent_name"])
                                new_info = self.run_autonomous_agent(
                                    agent_name=info["agent_name"],
                                    agent_cfg=info["agent_cfg"],
                                    relay_url=relay_url,
                                    relay_token=relay_token,
                                    prompt=prompt,
                                    shared_dir=shared_dir or None,
                                )
                                info["container"] = new_info["container"]
                                info["workspace"] = new_info["workspace"]
                                info["temp_dirs"] = new_info["temp_dirs"]
                                info["writeback_pairs"] = new_info["writeback_pairs"]
                                info["_exit_handled"] = False
                                info["_writeback_done"] = False
                                t = threading.Thread(
                                    target=self._stream_logs,
                                    args=(new_info["container"], info["agent_name"], new_info["workspace"]),
                                    daemon=True,
                                )
                                t.start()
                                logger.info("Agent restarted: %s (container=%s)",
                                            info["agent_name"], new_info["container"].short_id)
                            except Exception as e:
                                logger.error("Agent restart failed %s: %s", info["agent_name"], e)
                except Exception as e:
                    logger.warning("Status check failed %s: %s", info["agent_name"], e)

            stop_event.wait(check_interval)

    def _writeback_auth(self, info: dict):
        """Copy updated auth files back from temp dirs to original profile dirs."""
        for tmp_dir, original_dir in info.get("writeback_pairs", []):
            errors = []
            for item in tmp_dir.iterdir():
                try:
                    dst = original_dir / item.name
                    if item.is_file():
                        shutil.copy2(str(item), str(dst))
                    elif item.is_dir():
                        if dst.exists():
                            shutil.rmtree(str(dst))
                        shutil.copytree(str(item), str(dst))
                except PermissionError:
                    errors.append(item.name)
                except Exception as e:
                    errors.append(f"{item.name}: {e}")
            if errors:
                logger.debug("Auth writeback skipped (permission): %s → %s: %s",
                             tmp_dir, original_dir, errors)
            else:
                logger.debug("Auth writeback: %s → %s", tmp_dir, original_dir)

    def stop_all(self, container_infos: list[dict]):
        """Stop tracked containers"""
        for info in container_infos:
            try:
                info["container"].reload()
                if info["container"].status == "running":
                    logger.info("Stopping: %s", info["agent_name"])
                    info["container"].stop(timeout=10)
                self._writeback_auth(info)
                info["container"].remove(force=True)
            except (Exception, KeyboardInterrupt):
                # 二重Ctrl+Cでも残りのクリーンアップを続行
                try:
                    self._writeback_auth(info)
                    info["container"].remove(force=True)
                except Exception:
                    pass
            for tmp in info.get("temp_dirs", []):
                shutil.rmtree(tmp, ignore_errors=True)
    
    def stop_all_ctf_containers(self):
        """Stop all CTF-related containers (including orphaned ones)"""
        try:
            containers = self.client.containers.list(all=True)
            ctf_containers = [c for c in containers if c.image.tags and any("ctf-agent" in tag for tag in c.image.tags)]
            
            if ctf_containers:
                logger.info("Stopping %d CTF containers...", len(ctf_containers))
                for container in ctf_containers:
                    try:
                        if container.status == "running":
                            container.stop(timeout=10)
                        container.remove(force=True)
                        logger.debug("Removed container: %s", container.short_id)
                    except Exception as e:
                        logger.warning("Failed to stop container %s: %s", container.short_id, e)
            else:
                logger.info("No CTF containers found")
        except Exception as e:
            logger.error("Failed to stop all containers: %s", e)

    def _stream_logs(self, container, agent_name: str, workspace: Path):
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        safe_name = agent_name.replace("#", "_")
        central_log = log_dir / f"{safe_name}.log"
        workspace_log = workspace / "agent.log"
        try:
            for chunk in container.logs(stream=True, follow=True):
                text = chunk.decode("utf-8", errors="replace")
                # ファイルには全て書き込む
                for path in (workspace_log, central_log):
                    with open(path, "a", encoding="utf-8") as f:
                        f.write(text)
                # コンソールには重要な行だけ表示
                for line in text.splitlines(True):
                    if _CONSOLE_KEYWORDS.search(line):
                        sys.stdout.write(f"[{agent_name}] {line}")
                sys.stdout.flush()
        except Exception:
            pass
