"""
ベースランナー: 全AIエージェントランナーの共通機能を提供する。

各CLIツール固有のランナーはこのクラスを継承し、
execute() メソッドをオーバーライドする。

共通機能:
- プロンプト読み込み
- フラグ抽出（正規表現）
- 不正解フラグの確認
- CLIコマンド実行
- ログ出力
"""

import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


class BaseRunner:
    """全エージェントランナーの基底クラス"""

    def __init__(self, agent_name: str):
        """
        ベースランナーを初期化する。

        Args:
            agent_name: エージェント識別名（ログ表示用）
        """
        self.agent_name = agent_name
        self.logger = logging.getLogger(agent_name)

        # ワークスペース内のパス定義
        self.workspace = Path("/workspace")
        self.prompt_path = self.workspace / "prompt.txt"
        self.flag_path = self.workspace / "Flag.txt"
        self.work_dir = self.workspace / "try"
        self.chall_dir = self.workspace / "chall"
        self.shared_info_dir = self.workspace / "SharedInfo"

        # タイムアウト設定（環境変数から取得、デフォルト550秒）
        self.timeout = int(os.environ.get("AGENT_TIMEOUT", "550"))

    # ── ファイル読み込み ─────────────────────────────────────

    def load_prompt(self) -> str:
        """プロンプトファイルを読み込んで返す。"""
        if not self.prompt_path.exists():
            self.logger.error("prompt.txt が見つかりません")
            sys.exit(1)
        return self.prompt_path.read_text(encoding="utf-8")

    def load_wrong_flags(self) -> list[str]:
        """過去の不正解フラグ一覧を読み込んで返す。"""
        wf = self.shared_info_dir / "wrong_flags.txt"
        if wf.exists():
            return [line.strip() for line in wf.read_text().splitlines() if line.strip()]
        return []

    def load_approaches(self) -> str:
        """過去の失敗アプローチ記録を読み込んで返す。"""
        ap = self.shared_info_dir / "approaches.txt"
        if ap.exists():
            return ap.read_text(encoding="utf-8")
        return ""

    # ── フラグ操作 ───────────────────────────────────────────

    def save_flag(self, flag: str):
        """
        発見したフラグをFlag.txtに保存する。

        Args:
            flag: フラグ文字列
        """
        flag = flag.strip()
        if flag:
            self.flag_path.write_text(flag)
            self.logger.info("フラグ保存完了: %s", flag)

    def check_flag_exists(self) -> bool:
        """Flag.txtが既に存在し、内容があるか確認する。"""
        return self.flag_path.exists() and self.flag_path.read_text().strip() != ""

    def extract_flag_from_output(self, output: str) -> str | None:
        """
        テキスト出力からCTFフラグパターンを抽出する。

        一般的なフラグ形式（flag{...}, CTF{...}等）を検索し、
        過去の不正解フラグと一致するものは除外する。

        Args:
            output: CLIツールの出力テキスト

        Returns:
            抽出されたフラグ文字列。見つからない場合はNone。
        """
        # CTFで使われる一般的なフラグパターン
        patterns = [
            r'flag\{[^}]+\}',
            r'FLAG\{[^}]+\}',
            r'ctf\{[^}]+\}',
            r'CTF\{[^}]+\}',
            r'[A-Za-z0-9_]+\{[A-Za-z0-9_!@#$%^&*()\-+=,.?]+\}',
        ]

        wrong_flags = set(self.load_wrong_flags())

        for pattern in patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            for match in matches:
                # 過去の不正解フラグは除外
                if match not in wrong_flags:
                    return match

        return None

    # ── CLIコマンド実行 ──────────────────────────────────────

    def run_cli(
        self, cmd: list[str], env: dict | None = None, timeout: int | None = None
    ) -> tuple[str, str, int]:
        """
        CLIコマンドをサブプロセスとして実行する。

        Args:
            cmd: 実行するコマンドとその引数のリスト
            env: 追加の環境変数（既存環境変数にマージ）
            timeout: タイムアウト秒数（デフォルトはself.timeout）

        Returns:
            (stdout, stderr, return_code) のタプル
        """
        # 環境変数を構築
        full_env = {**os.environ}
        if env:
            full_env.update(env)

        effective_timeout = timeout if timeout is not None else self.timeout
        self.logger.info("コマンド実行: %s", " ".join(cmd))

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.work_dir),
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                env=full_env,
            )
            return proc.stdout, proc.stderr, proc.returncode

        except subprocess.TimeoutExpired:
            self.logger.warning("コマンドタイムアウト（%d秒）", effective_timeout)
            return "", "TIMEOUT", -1

        except FileNotFoundError:
            self.logger.error("コマンドが見つかりません: %s", cmd[0])
            return "", f"Command not found: {cmd[0]}", -1

    # ── メイン実行 ───────────────────────────────────────────

    def execute(self):
        """
        エージェント固有の実行ロジック。

        サブクラスでオーバーライドして、
        具体的なCLIツールの呼び出しを実装する。
        """
        raise NotImplementedError("サブクラスでexecute()を実装してください")

    def run(self):
        """
        ランナーのメインエントリーポイント。

        1. ワーキングディレクトリを準備
        2. execute()を呼び出し（サブクラスの実装）
        3. 結果を確認・ログ出力
        """
        self.logger.info("=== エージェント %s 開始 ===", self.agent_name)
        self.logger.info("ワークスペース: %s", self.workspace)

        # 作業ディレクトリを作成
        self.work_dir.mkdir(parents=True, exist_ok=True)

        try:
            self.execute()
        except Exception as e:
            self.logger.exception("エージェント実行エラー: %s", e)

        # 結果を確認
        if self.check_flag_exists():
            flag = self.flag_path.read_text().strip()
            self.logger.info("=== フラグ発見: %s ===", flag)
        else:
            self.logger.info("=== フラグ未発見 ===")
