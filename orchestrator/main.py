"""
CTF Solver メインオーケストレーター

CLIエントリーポイントとして機能し、以下のパイプラインを実行する:
1. CTFdから問題情報を取得
2. ヒント・配布ファイルを収集
3. プロンプトを生成
4. 複数AIエージェントを並列実行（Docker内）
5. フラグ候補を収集・多数決で決定
6. CTFdにフラグを提出
7. 不正解の場合は再試行
"""

import argparse
import concurrent.futures
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

from .ctfd_client import CTFdClient
from .challenge_manager import ChallengeManager
from .hint_manager import HintManager
from .file_manager import FileManager
from .docker_manager import DockerManager
from .flag_collector import FlagCollector
from .prompt_generator import PromptGenerator

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── 設定ファイル読み込み ─────────────────────────────────────

def _resolve_env(value: str) -> str:
    """
    ${VAR_NAME} 形式の文字列を環境変数の値で置換する。

    Args:
        value: 置換対象の文字列

    Returns:
        環境変数で置換された文字列
    """
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1], "")
    return value


def load_config(config_path: str = "config/config.yaml") -> dict:
    """
    メイン設定ファイルを読み込む。

    CTFd接続情報の環境変数を解決する。

    Args:
        config_path: config.yamlのパス

    Returns:
        設定辞書
    """
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["ctfd"]["url"] = _resolve_env(cfg["ctfd"]["url"])
    cfg["ctfd"]["token"] = _resolve_env(cfg["ctfd"]["token"])
    return cfg


def load_agents(agents_path: str = "config/agents.yaml") -> dict:
    """
    エージェント設定ファイルを読み込む。

    Args:
        agents_path: agents.yamlのパス

    Returns:
        エージェント設定辞書
    """
    with open(agents_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_enabled_agents(agents_cfg: dict) -> dict[str, dict]:
    """
    有効化されたエージェントのみを抽出する。

    agents.yamlでenabled: trueのエージェントのみ返す。

    Args:
        agents_cfg: agents.yaml全体の設定辞書

    Returns:
        {エージェント名: 設定辞書} の辞書
    """
    return {
        name: cfg
        for name, cfg in agents_cfg.get("agents", {}).items()
        if cfg.get("enabled", False)
    }


# ── 単一問題の解答パイプライン ───────────────────────────────

def solve_challenge(
    challenge_id: int,
    ctfd: CTFdClient,
    cm: ChallengeManager,
    hint_mgr: HintManager,
    file_mgr: FileManager,
    docker_mgr: DockerManager,
    flag_col: FlagCollector,
    prompt_gen: PromptGenerator,
    enabled_agents: dict[str, dict],
    execution_cfg: dict,
):
    """
    1つの問題に対する完全な解答パイプラインを実行する。

    処理フロー:
    1. ディレクトリ構造を作成
    2. 問題詳細・ヒント・ファイルを取得
    3. プロンプトを生成
    4. 全エージェントを並列実行
    5. フラグ候補を多数決で選択
    6. CTFdにフラグを提出
    7. 結果に応じて解決マーク or 不正解記録

    Args:
        challenge_id: 問題ID
        ctfd: CTFdクライアント
        cm: チャレンジマネージャー
        hint_mgr: ヒントマネージャー
        file_mgr: ファイルマネージャー
        docker_mgr: Dockerマネージャー
        flag_col: フラグコレクター
        prompt_gen: プロンプトジェネレーター
        enabled_agents: 有効エージェント辞書
        execution_cfg: 実行設定辞書
    """
    # 解決済みチェック
    if cm.is_solved(challenge_id):
        logger.info("問題 %d は解決済み、スキップ", challenge_id)
        return

    logger.info("═══ 問題 %d の解答を開始 ═══", challenge_id)

    # 1. ディレクトリ構造を作成
    cdir = cm.setup_challenge_dir(challenge_id)
    cm.mark_running(challenge_id)

    try:
        # 2. 問題詳細を取得
        detail = ctfd.get_challenge(challenge_id)
        problem_text = detail.get("description", "")
        challenge_name = detail.get("name", f"Challenge {challenge_id}")
        cm.save_problem(challenge_id, problem_text)
        logger.info("問題取得: %s", challenge_name)

        # 3. ヒントを取得（無料のみ）
        hints = hint_mgr.get_free_hints(challenge_id)
        hints_text = hint_mgr.format_hints(hints)
        hints_exist = hints_text is not None
        if hints_exist:
            cm.save_hints(challenge_id, hints_text)
            logger.info("ヒント %d 件取得", len(hints))

        # 4. 配布ファイルをダウンロード
        chall_dir = cm.chall_dir(challenge_id)
        files_meta = file_mgr.download_challenge_files(challenge_id, chall_dir)
        cm.save_files_metadata(challenge_id, files_meta)
        logger.info("配布ファイル %d 件処理", len(files_meta))

        # 5. プロンプトを生成
        prompt = prompt_gen.generate(
            problem_text, 
            files_meta, 
            hints_text,
            ctfd_url=ctfd.base_url,
            ctfd_token=ctfd.token,
            challenge_id=challenge_id,
        )
        cm.save_prompt(challenge_id, prompt)

        # 6. 全エージェントを並列実行
        timeout = execution_cfg.get("agent_timeout", 600)
        flags: dict[str, Optional[str]] = {}

        def _run_one_agent(
            agent_name: str, agent_cfg: dict
        ) -> tuple[str, Optional[str]]:
            """
            1つのエージェントをDockerコンテナで実行する。

            ワークスペースの準備→コンテナ実行→ログ保存→クリーンアップ。
            """
            ws = docker_mgr.prepare_workspace(cdir, hints_exist)
            try:
                flag, logs = docker_mgr.run_agent(
                    agent_name, agent_cfg, ws, timeout
                )
                # ログを保存
                cm.append_log(challenge_id, agent_name, logs)
                # フラグ候補を保存
                if flag:
                    cm.save_agent_flag(challenge_id, agent_name, flag)
                return agent_name, flag
            finally:
                docker_mgr.cleanup_workspace(ws)

        # ThreadPoolExecutorで全エージェントを並列実行
        logger.info(
            "エージェント %d 体を並列実行: %s",
            len(enabled_agents),
            list(enabled_agents.keys()),
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
                    name, flag = fut.result()
                    flags[name] = flag
                    if flag:
                        logger.info(
                            "エージェント %s がフラグ候補を発見: %s",
                            name,
                            flag,
                        )
                except Exception as e:
                    logger.error("エージェント %s でエラー: %s", agent_name, e)
                    flags[agent_name] = None

        # 7. フラグを多数決で選択
        chosen = flag_col.collect_and_decide(flags)
        summary = flag_col.build_summary(flags, chosen)
        cm.save_flags_summary(challenge_id, summary)

        if not chosen:
            logger.warning("問題 %d: 有効なフラグ候補なし", challenge_id)
            cm.unmark_running(challenge_id)
            return

        # AIエージェント自身が提出するため、オーケストレーター提出は無効化
        logger.info("フラグ候補発見: %s（AIエージェント自身が提出予定）", chosen)
        
        # 解決確認のみ（AIが成功提出済みかチェック）
        # TODO: CTFdに問題解決状態をクエリして確認
        logger.info("✓ 問題 %d: AIエージェントによる直接提出待機中", challenge_id)
        cm.unmark_running(challenge_id)

    except Exception as e:
        logger.exception("問題 %d の処理中にエラー: %s", challenge_id, e)
        cm.unmark_running(challenge_id)


# ── CLIエントリーポイント ────────────────────────────────────

def main():
    """
    CTF Solverのメインエントリーポイント。

    使用方法:
        python -m orchestrator.main                    # 全問題を解答
        python -m orchestrator.main --challenge 1 2 3  # 指定問題を解答
        python -m orchestrator.main --build-image      # Dockerイメージをビルド
    """
    parser = argparse.ArgumentParser(
        description="CTF Solver – AI駆動の自動CTF解答システム"
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="config.yamlのパス（デフォルト: config/config.yaml）",
    )
    parser.add_argument(
        "--agents",
        default="config/agents.yaml",
        help="agents.yamlのパス（デフォルト: config/agents.yaml）",
    )
    parser.add_argument(
        "--challenge",
        type=int,
        nargs="*",
        help="解答する問題ID（省略時は全未解決問題）",
    )
    parser.add_argument(
        "--build-image",
        action="store_true",
        help="Dockerベースイメージをビルドして終了",
    )
    args = parser.parse_args()

    # .envファイルから環境変数を読み込む
    load_dotenv()

    # 設定ファイルを読み込む
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
    file_mgr = FileManager(
        ctfd, max_size_mb=cfg["files"].get("max_size", 100)
    )
    
    # Dockerマネージャー初期化
    docker_mgr = DockerManager(
        agents_cfg.get("agents", {}),
        agents_cfg.get("docker", {}),
    )
        
    flag_col = FlagCollector(
        method=cfg["flag_evaluation"].get("method", "voting"),
        wait_time=cfg["flag_evaluation"].get("wait_time", 30),
    )
    prompt_gen = PromptGenerator()

    # Dockerイメージビルドモード
    if args.build_image:
        docker_mgr.build_base_image()
        logger.info("Dockerイメージのビルドが完了しました")
        return

    # 有効なエージェントを取得
    enabled = get_enabled_agents(agents_cfg)
        
    if not enabled:
        logger.error(
            "有効なエージェントがありません: %s", args.agents
        )
        sys.exit(1)

    logger.info("有効エージェント: %s", list(enabled.keys()))

    execution_cfg = agents_cfg.get("execution", {})

    # 解答対象の問題を決定
    if args.challenge:
        challenge_ids = args.challenge
    else:
        # CTFdから全問題を取得
        challenges = ctfd.get_challenges()
        challenge_ids = [c["id"] for c in challenges]

    logger.info("解答対象の問題: %s", challenge_ids)

    # 各問題を順次解答
    for cid in challenge_ids:
        solve_challenge(
            cid,
            ctfd,
            cm,
            hint_mgr,
            file_mgr,
            docker_mgr,
            flag_col,
            prompt_gen,
            enabled,
            execution_cfg,
        )

    logger.info("全問題の処理が完了しました")


if __name__ == "__main__":
    main()
