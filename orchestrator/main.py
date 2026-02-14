"""
CTF Solver メインオーケストレーター

CLIエントリーポイントとして機能し、以下のパイプラインを実行する:
1. CTFdから問題情報を取得
2. ヒント・配布ファイルを収集
3. プロンプトを生成
4. 複数AIエージェントを並列実行（Docker内）
5. エージェントがsubmit_flag.shで自律的にフラグ提出
6. 正解 → 次の問題 / 不正解 → ローテーションして後で再挑戦
"""

import argparse
import concurrent.futures
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

from .ctfd_client import CTFdClient
from .challenge_manager import ChallengeManager
from .hint_manager import HintManager
from .file_manager import FileManager
from .docker_manager import DockerManager
from .prompt_generator import PromptGenerator

# ログ設定
class _ExcludeAgentStreamFilter(logging.Filter):
    """agent_streamロガーのメッセージをファイルハンドラーから除外するフィルター。"""
    def filter(self, record):
        return record.name != "agent_stream"


def setup_logging(challenge_id: Optional[int] = None):
    """ログ設定を初期化し、システムログファイルも出力する。"""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format, force=True)
    if challenge_id:
        from pathlib import Path
        log_dir = Path(f"challenges/{challenge_id}/Logs/Latest")
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / "system.log", mode="a", encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(log_format))
        file_handler.addFilter(_ExcludeAgentStreamFilter())
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)


# ── 設定ファイル読み込み ─────────────────────────────────────

def _resolve_env(value: str) -> str:
    """${VAR_NAME} 形式の文字列を環境変数の値で置換する。"""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1], "")
    return value


def load_config(config_path: str = "config/config.yaml") -> dict:
    """メイン設定ファイルを読み込む。"""
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["ctfd"]["url"] = _resolve_env(cfg["ctfd"]["url"])
    cfg["ctfd"]["token"] = _resolve_env(cfg["ctfd"]["token"])
    return cfg


def load_agents(agents_path: str = "config/agents.yaml") -> dict:
    """エージェント設定ファイルを読み込む。"""
    with open(agents_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_enabled_agents(agents_cfg: dict) -> dict[str, dict]:
    """
    有効化されたエージェントをインスタンス数分展開して返す。

    agents.yamlで instances >= 1 のエージェントを展開する。
    instances: 2 の場合、agent_name#1, agent_name#2 のように展開。
    instances: 1 の場合はサフィックスなし（後方互換性）。

    後方互換: enabled: true は instances: 1、enabled: false は instances: 0 として扱う。
    """
    result = {}
    for name, cfg in agents_cfg.get("agents", {}).items():
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
                instance_name = f"{name}#{i}"
                result[instance_name] = cfg
    return result


# ── WriteUp保存ヘルパー ──────────────────────────────────────

def _save_best_writeup(
    cm: 'ChallengeManager',
    challenge_id: int,
    writeups: dict[str, Optional[str]],
    flags: dict[str, Optional[str]],
    chosen_flag: str,
):
    """正解フラグを出したエージェントのWriteUpを優先して保存する。"""
    best_writeup = None
    best_agent = None
    for agent_name, flag in flags.items():
        if flag == chosen_flag and agent_name in writeups and writeups[agent_name]:
            best_writeup = writeups[agent_name]
            best_agent = agent_name
            break
    if not best_writeup:
        for agent_name, writeup in writeups.items():
            if writeup:
                best_writeup = writeup
                best_agent = agent_name
                break
    if best_writeup:
        cm.save_writeup(challenge_id, best_writeup, best_agent)
        logger.info("WriteUp保存: エージェント %s（%d文字）", best_agent, len(best_writeup))


# ── WriteUp後追い生成 ────────────────────────────────────────

def _generate_writeup_from_log(
    docker_mgr: DockerManager,
    cm: 'ChallengeManager',
    prompt_gen: PromptGenerator,
    challenge_id: int,
    winner_agent: str,
    winner_cfg: dict,
    flag: str,
    problem_text: str,
    writeup_timeout: int = 180,
):
    """正解エージェントのログを元にWriteUpを後追い生成する。"""
    log_path = Path(f"challenges/{challenge_id}/Logs/Latest/{winner_agent}.log")
    if not log_path.exists():
        logger.warning("WriteUp後追い生成: ログファイルなし %s", log_path)
        return
    log_content = log_path.read_text(encoding="utf-8", errors="replace")
    if not log_content.strip():
        logger.warning("WriteUp後追い生成: ログが空 %s", log_path)
        return

    logger.info("WriteUp後追い生成開始: エージェント=%s, ログ=%d文字", winner_agent, len(log_content))
    writeup_prompt = prompt_gen.generate_writeup_prompt(problem_text, log_content, flag)

    cdir = cm.base_dir / str(challenge_id)
    ws = docker_mgr.prepare_workspace(cdir, hints_exist=False)
    (ws / "WriteUp").mkdir(exist_ok=True)
    (ws / "prompt.txt").write_text(writeup_prompt, encoding="utf-8")
    (ws / "solve_log.txt").write_text(log_content, encoding="utf-8")

    try:
        _, _, writeup = docker_mgr.run_agent(
            f"{winner_agent}_writeup", winner_cfg, ws, writeup_timeout,
        )
        if writeup and len(writeup.strip()) > 50:
            cm.save_writeup(challenge_id, writeup, winner_agent)
            logger.info("WriteUp後追い生成完了（%d文字）", len(writeup))
        else:
            logger.warning("WriteUp後追い生成: 有効なWriteUpが得られませんでした")
    except Exception as e:
        logger.error("WriteUp後追い生成エラー: %s", e)
    finally:
        docker_mgr.cleanup_workspace(ws)


# ── 問題の初期セットアップ（1回のみ実行） ─────────────────────

def _prepare_challenge(
    challenge_id: int,
    ctfd: CTFdClient,
    cm: ChallengeManager,
    hint_mgr: HintManager,
    file_mgr: FileManager,
    prompt_gen: PromptGenerator,
) -> Optional[dict]:
    """
    問題の事前準備を行う（ディレクトリ作成、問題取得、ヒント、ファイルDL、プロンプト生成）。
    戻り値は問題メタデータ辞書。エラー時はNone。
    """
    try:
        cdir = cm.setup_challenge_dir(challenge_id)
        setup_logging(challenge_id)

        detail = ctfd.get_challenge(challenge_id)
        problem_text = detail.get("description", "")
        challenge_name = detail.get("name", f"Challenge {challenge_id}")
        cm.save_problem(challenge_id, problem_text)
        logger.info("問題取得: %s", challenge_name)

        hints = hint_mgr.get_free_hints(challenge_id)
        hints_text = hint_mgr.format_hints(hints)
        hints_exist = hints_text is not None
        if hints_exist:
            cm.save_hints(challenge_id, hints_text)
            logger.info("ヒント %d 件取得", len(hints))

        chall_dir = cm.chall_dir(challenge_id)
        files_meta = file_mgr.download_challenge_files(challenge_id, chall_dir)
        cm.save_files_metadata(challenge_id, files_meta)
        logger.info("配布ファイル %d 件処理", len(files_meta))

        prompt = prompt_gen.generate(
            problem_text, files_meta, hints_text,
            ctfd_url=ctfd.base_url, ctfd_token=ctfd.token,
            challenge_id=challenge_id,
        )
        cm.save_prompt(challenge_id, prompt)

        return {
            "problem_text": problem_text,
            "challenge_name": challenge_name,
            "hints_exist": hints_exist,
        }
    except Exception as e:
        logger.exception("問題 %d の準備中にエラー: %s", challenge_id, e)
        return None


# ── 1ラウンド実行 ────────────────────────────────────────────

def solve_one_round(
    challenge_id: int,
    round_num: int,
    meta: dict,
    ctfd: CTFdClient,
    cm: ChallengeManager,
    docker_mgr: DockerManager,
    prompt_gen: PromptGenerator,
    enabled_agents: dict[str, dict],
    execution_cfg: dict,
) -> str:
    """
    1つの問題に対して1ラウンドだけ実行する。

    Returns:
        "solved"    - 正解が出た
        "continue"  - 不正解だったが続行可能
        "abandoned" - あきらめ判定に該当
    """
    max_no_flag_rounds = execution_cfg.get("max_no_flag_rounds", 3)
    max_duplicate_flags = execution_cfg.get("max_duplicate_flags", 2)
    writeup_timeout = execution_cfg.get("writeup_timeout", 180)
    max_retries = execution_cfg.get("max_retries", 5)

    # 段階的タイムアウト計算
    t_initial = execution_cfg.get("agent_timeout_initial", 300)
    t_increment = execution_cfg.get("agent_timeout_increment", 120)
    t_max = execution_cfg.get("agent_timeout_max", 900)
    timeout = min(t_initial + t_increment * (round_num - 1), t_max)

    # ラウンド上限チェック
    if round_num > max_retries:
        cm.mark_abandoned(challenge_id, f"最大リトライ回数 {max_retries} に到達")
        return "abandoned"

    cdir = cm.base_dir / str(challenge_id)
    attempt_count = cm.get_attempt_count(challenge_id)
    logger.info(
        "── 問題 %d: ラウンド %d/%d（タイムアウト %ds, 過去不正解 %d 回）──",
        challenge_id, round_num, max_retries, timeout, attempt_count,
    )

    # 前回のログをHistory/に退避してからLatest/を使う
    cm.rotate_logs(challenge_id)
    cm.mark_running(challenge_id)

    # 全エージェントを並列実行
    flags: dict[str, Optional[str]] = {}
    writeups: dict[str, Optional[str]] = {}
    cancel_event = threading.Event()
    confirmed_flag: Optional[str] = None
    confirmed_agent: Optional[str] = None

    def _run_one_agent(
        agent_name: str, agent_cfg: dict
    ) -> tuple[str, Optional[str], Optional[str]]:
        ws = docker_mgr.prepare_workspace(cdir, meta["hints_exist"])
        (ws / "WriteUp").mkdir(exist_ok=True)
        log_file = Path(f"challenges/{challenge_id}/Logs/Latest/{agent_name}.log")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            flag, logs, writeup = docker_mgr.run_agent(
                agent_name, agent_cfg, ws, timeout,
                cancel_event=cancel_event,
                ctfd_url=ctfd.base_url,
                ctfd_token=ctfd.token,
                challenge_id=challenge_id,
                log_file_path=log_file,
            )
            if flag:
                cm.save_agent_flag(challenge_id, agent_name, flag)
            return agent_name, flag, writeup
        finally:
            docker_mgr.cleanup_workspace(ws)

    logger.info(
        "エージェント %d 体を並列実行（timeout=%ds）: %s",
        len(enabled_agents), timeout, list(enabled_agents.keys()),
    )

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=len(enabled_agents)
    ) as pool:
        futures = {
            pool.submit(_run_one_agent, name, cfg): name
            for name, cfg in enabled_agents.items()
        }
        for fut in concurrent.futures.as_completed(futures):
            agent_name = futures[fut]
            try:
                name, flag, writeup = fut.result()
                flags[name] = flag
                if writeup:
                    writeups[name] = writeup
                if flag:
                    logger.info("エージェント %s フラグ: %s", name, flag)
                    if cancel_event.is_set() and not confirmed_flag:
                        confirmed_flag = flag
                        confirmed_agent = name
            except Exception as e:
                logger.error("エージェント %s でエラー: %s", agent_name, e)
                flags[agent_name] = None

    cm.unmark_running(challenge_id)

    # ラウンド結果の記録
    summary = {
        "round": round_num,
        "timeout": timeout,
        "agent_flags": {k: v for k, v in flags.items()},
        "confirmed_flag": confirmed_flag,
        "confirmed_agent": confirmed_agent,
        "total_agents": len(flags),
        "flags_found": sum(1 for v in flags.values() if v),
    }
    cm.save_flags_summary(challenge_id, summary)

    # ── 正解が出た場合 ──
    if confirmed_flag:
        logger.info("✓ 問題 %d 正解（エージェント %s）: %s",
                     challenge_id, confirmed_agent, confirmed_flag)
        cm.mark_solved(challenge_id, confirmed_flag)
        _save_best_writeup(cm, challenge_id, writeups, flags, confirmed_flag)

        # WriteUpが無い場合 → 後追い生成
        writeup_path = cdir / "WriteUp" / "writeup.md"
        if not writeup_path.exists() or writeup_path.stat().st_size < 50:
            logger.info("WriteUp未生成 → 後追い生成を開始")
            winner = confirmed_agent
            base_name = winner.split("#")[0] if winner else None
            winner_cfg = enabled_agents.get(winner, enabled_agents.get(base_name)) if winner else None
            if winner and winner_cfg:
                _generate_writeup_from_log(
                    docker_mgr, cm, prompt_gen,
                    challenge_id, winner, winner_cfg,
                    confirmed_flag, meta["problem_text"], writeup_timeout,
                )
        return "solved"

    # ── フラグ候補が1つも出なかった ──
    valid_flags = [v for v in flags.values() if v]
    if not valid_flags:
        no_flag = cm.increment_no_flag_count(challenge_id)
        logger.warning(
            "問題 %d: 有効なフラグ候補なし（連続 %d 回目）",
            challenge_id, no_flag,
        )
        if no_flag >= max_no_flag_rounds:
            cm.mark_abandoned(
                challenge_id,
                f"フラグ候補なし {no_flag} 回連続（上限 {max_no_flag_rounds}）",
            )
            return "abandoned"
        return "continue"

    # ── フラグ候補はあったが全て不正解 ──
    cm.reset_no_flag_count(challenge_id)
    for aname, aflag in flags.items():
        if aflag:
            cm.add_wrong_flag(challenge_id, aflag, aname)

    # 迷走検出
    for aflag in set(valid_flags):
        dup_count = cm.count_duplicate_flags(challenge_id, aflag)
        if dup_count >= max_duplicate_flags:
            cm.mark_abandoned(
                challenge_id,
                f"同一フラグ '{aflag}' が {dup_count} 回繰り返し提出（迷走）",
            )
            return "abandoned"

    logger.info("問題 %d: 全フラグ不正解、後でリトライ", challenge_id)
    return "continue"


# ── CLIエントリーポイント ────────────────────────────────────

def main():
    """
    CTF Solverのメインエントリーポイント。

    ローテーション方式で問題を解答する:
    - 各問題を1ラウンドずつ実行
    - 未解決の問題をローテーションして繰り返す
    - ラウンドが進むごとにタイムアウトが段階的に延長される
    """
    parser = argparse.ArgumentParser(
        description="CTF Solver – AI駆動の自動CTF解答システム"
    )
    parser.add_argument(
        "--config", default="config/config.yaml",
        help="config.yamlのパス（デフォルト: config/config.yaml）",
    )
    parser.add_argument(
        "--agents", default="config/agents.yaml",
        help="agents.yamlのパス（デフォルト: config/agents.yaml）",
    )
    parser.add_argument(
        "--challenge", type=int, nargs="*",
        help="解答する問題ID（省略時は全未解決問題）",
    )
    parser.add_argument(
        "--skip", type=int, nargs="+", default=[],
        help="スキップする問題ID（例: --skip 3 7 12）",
    )
    parser.add_argument(
        "--build-image", action="store_true",
        help="Dockerベースイメージをビルドして終了",
    )
    args = parser.parse_args()

    load_dotenv()
    cfg = load_config(args.config)
    agents_cfg = load_agents(args.agents)

    # 各コンポーネントを初期化
    ctfd = CTFdClient(cfg["ctfd"]["url"], cfg["ctfd"]["token"])
    cm = ChallengeManager("challenges")
    hint_mgr = HintManager(
        ctfd,
        allow_cost_hints=cfg["hints"].get("allow_cost_hints", False),
        max_cost=cfg["hints"].get("max_cost", 0),
    )
    file_mgr = FileManager(ctfd, max_size_mb=cfg["files"].get("max_size", 100))
    docker_mgr = DockerManager(
        agents_cfg.get("agents", {}), agents_cfg.get("docker", {}),
    )
    prompt_gen = PromptGenerator()

    if args.build_image:
        docker_mgr.build_base_image()
        logger.info("Dockerイメージのビルドが完了しました")
        return

    enabled = get_enabled_agents(agents_cfg)
    if not enabled:
        logger.error("有効なエージェントがありません: %s", args.agents)
        sys.exit(1)
    logger.info("有効エージェント: %s", list(enabled.keys()))

    execution_cfg = agents_cfg.get("execution", {})
    max_retries = execution_cfg.get("max_retries", 5)

    # 解答対象の問題を決定
    if args.challenge:
        challenge_ids = args.challenge
        for cid in challenge_ids:
            abandoned_path = Path(f"challenges/{cid}/.abandoned")
            if abandoned_path.exists():
                abandoned_path.unlink()
                logger.info("問題 %d: abandoned 状態をリセット（明示指定）", cid)
    else:
        challenges = ctfd.get_challenges()
        challenge_ids = [c["id"] for c in challenges]

    if args.skip:
        skip_set = set(args.skip)
        before = len(challenge_ids)
        challenge_ids = [cid for cid in challenge_ids if cid not in skip_set]
        logger.info("スキップ対象: %s（%d → %d 問題）", args.skip, before, len(challenge_ids))

    logger.info("解答対象の問題: %s", challenge_ids)

    # ── 問題の事前準備（1回のみ） ──
    # {challenge_id: メタデータ辞書}
    prepared: dict[int, dict] = {}
    for cid in challenge_ids:
        if cm.is_solved(cid):
            logger.info("問題 %d は解決済み、スキップ", cid)
            continue
        if cm.is_abandoned(cid):
            logger.info("問題 %d は断念済み、スキップ", cid)
            continue
        meta = _prepare_challenge(cid, ctfd, cm, hint_mgr, file_mgr, prompt_gen)
        if meta:
            prepared[cid] = meta

    if not prepared:
        logger.info("解答対象の問題がありません")
        return

    # ── ローテーション実行 ──
    # {challenge_id: 次のラウンド番号}
    round_tracker: dict[int, int] = {cid: 1 for cid in prepared}
    active_ids = list(prepared.keys())

    logger.info("═══ ローテーション開始: %d 問題 ═══", len(active_ids))

    while active_ids:
        next_active: list[int] = []
        for cid in active_ids:
            round_num = round_tracker[cid]
            t_initial = execution_cfg.get("agent_timeout_initial", 300)
            t_increment = execution_cfg.get("agent_timeout_increment", 120)
            t_max = execution_cfg.get("agent_timeout_max", 900)
            timeout = min(t_initial + t_increment * (round_num - 1), t_max)
            logger.info(
                "═══ 問題 %d ラウンド %d（timeout=%ds, 残り問題=%d）═══",
                cid, round_num, timeout, len(active_ids),
            )

            result = solve_one_round(
                cid, round_num, prepared[cid],
                ctfd, cm, docker_mgr, prompt_gen,
                enabled, execution_cfg,
            )

            if result == "solved":
                logger.info("✓ 問題 %d 解決済み、ローテーションから除外", cid)
            elif result == "abandoned":
                logger.info("✗ 問題 %d 断念、ローテーションから除外", cid)
            else:
                # "continue" → 次のサイクルで再挑戦
                round_tracker[cid] = round_num + 1
                if round_tracker[cid] <= max_retries:
                    next_active.append(cid)
                else:
                    cm.mark_abandoned(cid, f"最大リトライ回数 {max_retries} に到達")
                    logger.info("✗ 問題 %d 最大リトライ到達、断念", cid)

        active_ids = next_active
        if active_ids:
            logger.info(
                "── ローテーション: 残り %d 問題 %s ──",
                len(active_ids), active_ids,
            )

    logger.info("全問題の処理が完了しました")


if __name__ == "__main__":
    main()
