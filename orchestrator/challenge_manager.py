"""
チャレンジディレクトリ管理モジュール

問題ごとのディレクトリ構造を作成・管理し、
問題の状態（実行中、解決済み等）を追跡する。
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 問題ディレクトリ内に作成するサブディレクトリ一覧
SUBDIRS = ["chall", "Flags", "WrongFlags", "WriteUp", "Logs", "SharedInfo"]


class ChallengeManager:
    """問題ごとのディレクトリ構造と状態を管理するクラス"""

    def __init__(self, base_dir: str = "challenges"):
        """
        チャレンジマネージャーを初期化する。

        Args:
            base_dir: 問題ディレクトリのベースパス
        """
        self.base_dir = Path(base_dir)

    # ── ディレクトリ構築 ─────────────────────────────────────

    def setup_challenge_dir(self, challenge_id: int) -> Path:
        """
        問題用のディレクトリ構造を一括作成する。

        作成される構造:
            challenges/{id}/
            ├── chall/          配布ファイル格納
            ├── Flags/          エージェントが発見したフラグ候補
            ├── WrongFlags/     不正解フラグの記録
            ├── WriteUp/        解法記録
            ├── Logs/           エージェントログ
            └── SharedInfo/     エージェント間共有情報
        """
        cdir = self.base_dir / str(challenge_id)
        for sub in SUBDIRS:
            (cdir / sub).mkdir(parents=True, exist_ok=True)

        # SharedInfoの初期ファイルを作成（存在しない場合のみ）
        for fname in ("wrong_flags.txt", "approaches.txt"):
            p = cdir / "SharedInfo" / fname
            if not p.exists():
                p.write_text("")

        return cdir

    # ── 状態管理 ─────────────────────────────────────────────

    def is_solved(self, challenge_id: int) -> bool:
        """問題が解決済みかどうかを返す。"""
        return (self.base_dir / str(challenge_id) / ".solved").exists()

    def is_running(self, challenge_id: int) -> bool:
        """問題が実行中かどうかを返す。"""
        return (self.base_dir / str(challenge_id) / ".running").exists()

    def mark_running(self, challenge_id: int):
        """問題を実行中としてマークする。"""
        (self.base_dir / str(challenge_id) / ".running").touch()

    def unmark_running(self, challenge_id: int):
        """問題の実行中マークを解除する。"""
        p = self.base_dir / str(challenge_id) / ".running"
        p.unlink(missing_ok=True)

    def mark_solved(self, challenge_id: int, flag: str):
        """
        問題を解決済みとしてマークし、正解フラグを保存する。

        Args:
            challenge_id: 問題ID
            flag: 正解フラグ文字列
        """
        cdir = self.base_dir / str(challenge_id)
        (cdir / "Solved-Flag.txt").write_text(flag)
        (cdir / ".solved").touch()
        self.unmark_running(challenge_id)

    # ── ファイル保存 ─────────────────────────────────────────

    def save_problem(self, challenge_id: int, text: str):
        """問題文をproblem.txtに保存する。"""
        (self.base_dir / str(challenge_id) / "problem.txt").write_text(
            text, encoding="utf-8"
        )

    def save_prompt(self, challenge_id: int, prompt: str):
        """生成したプロンプトをprompt.txtに保存する。"""
        (self.base_dir / str(challenge_id) / "prompt.txt").write_text(
            prompt, encoding="utf-8"
        )

    def save_hints(self, challenge_id: int, hints_text: str):
        """取得したヒントをHints.txtに保存する。"""
        (self.base_dir / str(challenge_id) / "Hints.txt").write_text(
            hints_text, encoding="utf-8"
        )

    def save_files_metadata(self, challenge_id: int, metadata: list[dict]):
        """配布ファイルのメタデータをJSONで保存する。"""
        p = self.base_dir / str(challenge_id) / "files_metadata.json"
        p.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ── 不正解フラグ管理 ─────────────────────────────────────

    def add_wrong_flag(
        self, challenge_id: int, flag: str, agent_name: str, approach: str = ""
    ):
        """
        不正解フラグを記録し、SharedInfoを更新する。

        Args:
            challenge_id: 問題ID
            flag: 不正解だったフラグ
            agent_name: フラグを提出したエージェント名
            approach: 使用したアプローチの説明
        """
        cdir = self.base_dir / str(challenge_id)

        # WrongFlags/flag_N.txt に個別記録
        wf_dir = cdir / "WrongFlags"
        existing = list(wf_dir.glob("flag_*.txt"))
        idx = len(existing) + 1
        (wf_dir / f"flag_{idx}.txt").write_text(
            f"agent: {agent_name}\nflag: {flag}\n"
        )

        # WrongFlags/summary.txt にサマリー追記
        with open(wf_dir / "summary.txt", "a", encoding="utf-8") as f:
            f.write(f"#{idx} [{agent_name}] {flag}\n")

        # SharedInfo/wrong_flags.txt に追記（エージェント間共有）
        with open(cdir / "SharedInfo" / "wrong_flags.txt", "a", encoding="utf-8") as f:
            f.write(f"{flag}\n")

        # SharedInfo/approaches.txt にアプローチ記録
        if approach:
            with open(
                cdir / "SharedInfo" / "approaches.txt", "a", encoding="utf-8"
            ) as f:
                f.write(f"[{agent_name}] {approach}\n")

    # ── エージェントフラグ管理 ───────────────────────────────

    def save_agent_flag(self, challenge_id: int, agent_name: str, flag: str):
        """エージェントが発見したフラグ候補を保存する。"""
        (self.base_dir / str(challenge_id) / "Flags" / f"{agent_name}.txt").write_text(
            flag
        )

    def save_flags_summary(self, challenge_id: int, summary: dict):
        """全エージェントのフラグ候補サマリーをJSONで保存する。"""
        p = self.base_dir / str(challenge_id) / "Flags" / "summary.json"
        p.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    # ── ログ管理 ─────────────────────────────────────────────

    def append_log(self, challenge_id: int, agent_name: str, content: str):
        """エージェントのログを追記する。"""
        p = self.base_dir / str(challenge_id) / "Logs" / f"{agent_name}.log"
        with open(p, "a", encoding="utf-8") as f:
            f.write(content)

    # ── パスヘルパー ─────────────────────────────────────────

    def challenge_dir(self, challenge_id: int) -> Path:
        """問題のルートディレクトリパスを返す。"""
        return self.base_dir / str(challenge_id)

    def chall_dir(self, challenge_id: int) -> Path:
        """配布ファイル格納ディレクトリパスを返す。"""
        return self.base_dir / str(challenge_id) / "chall"

    def shared_info_dir(self, challenge_id: int) -> Path:
        """エージェント間共有情報ディレクトリパスを返す。"""
        return self.base_dir / str(challenge_id) / "SharedInfo"
