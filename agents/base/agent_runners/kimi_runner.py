"""
Claude Code CLI（Kimi / Moonshot AI 経由）ランナー

Claude Code CLIをMoonshot AIバックエンド（kimi-k2.5等）で使用してCTF問題を解く。
entrypoint.shでagentユーザーに切り替え済み。

環境変数:
    KIMI_API_KEY: Moonshot AIのAPIキー
"""

import os
import sys

sys.path.insert(0, "/agent_runners")
from base_runner import BaseRunner


class KimiRunner(BaseRunner):
    """Claude Code CLI + Moonshot AI（Kimi）バックエンドで動作するエージェント"""

    def __init__(self):
        super().__init__("kimi")
        self.api_key = os.environ.get("KIMI_API_KEY", "")
        # AGENT_MODEL が model: キーから渡される
        # KIMI_MODEL で個別上書き可能
        self.model = os.environ.get("KIMI_MODEL", os.environ.get("AGENT_MODEL", "kimi-k2.5"))

    def execute(self):
        """Claude Code CLIをMoonshot AI経由で実行する。"""
        if not self.api_key:
            self.logger.error("KIMI_API_KEY が未設定です。agents.yaml の env_vars を確認してください。")
            return

        prompt = self.load_prompt()
        self.logger.info(
            "プロンプトサイズ: %d 文字, モデル: %s",
            len(prompt), self.model,
        )

        # Moonshot AI 用の環境変数を設定
        os.environ["ANTHROPIC_AUTH_TOKEN"]  = self.api_key
        os.environ["ANTHROPIC_API_KEY"]     = ""
        os.environ["ANTHROPIC_BASE_URL"]    = "https://api.moonshot.ai/anthropic"
        os.environ["ANTHROPIC_MODEL"]       = self.model
        os.environ["ANTHROPIC_SMALL_FAST_MODEL"] = self.model
        os.environ["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
        os.environ["API_TIMEOUT_MS"]        = "1800000"

        cmd = [
            "claude", "-p", prompt,
            "--dangerously-skip-permissions",
            "--output-format", "stream-json",
            "--verbose",
        ]

        self.logger.info(
            "実行コマンド: claude -p [省略] --dangerously-skip-permissions "
            "--output-format stream-json --verbose (via Moonshot AI, model=%s)",
            self.model,
        )

        stdout, stderr, rc = self.run_cli(cmd)
        self.logger.info("Claude Code (Kimi) 終了コード: %d", rc)

        output = stdout + "\n" + stderr
        self.logger.info("出力（先頭5000文字）:\n%s", output[:5000])

        if self.check_flag_exists():
            return

        self.logger.info("=== フラグ未発見 ===")


if __name__ == "__main__":
    KimiRunner().run()
