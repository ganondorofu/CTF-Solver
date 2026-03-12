"""
Claude Code CLI（z.ai GLM経由）ランナー

Claude Code CLIをz.aiバックエンド（GLMモデル）で使用してCTF問題を解く。
entrypoint.shでagentユーザーに切り替え済み。

環境変数:
    ZAI_API_KEY: z.aiのAPIキー
"""

import os
import sys

sys.path.insert(0, "/agent_runners")
from base_runner import BaseRunner


class ClaudeZaiRunner(BaseRunner):
    """Claude Code CLI + z.ai（GLM）バックエンドで動作するエージェント"""

    def __init__(self):
        super().__init__("claude_zai")
        self.api_key = os.environ.get("ZAI_API_KEY", "")
        # AGENT_MODEL が model: キーから渡される（全tierのデフォルト）
        # ZAI_MODEL_* で個別上書き可能
        default_model = os.environ.get("AGENT_MODEL", "glm-4.7")
        self.model_haiku  = os.environ.get("ZAI_MODEL_HAIKU",  default_model)
        self.model_sonnet = os.environ.get("ZAI_MODEL_SONNET", default_model)
        self.model_opus   = os.environ.get("ZAI_MODEL_OPUS",   default_model)

    def execute(self):
        """Claude Code CLIをz.ai経由で実行する。"""
        if not self.api_key:
            self.logger.error("ZAI_API_KEY が未設定です。agents.yaml の env_vars を確認してください。")
            return

        prompt = self.load_prompt()
        self.logger.info(
            "プロンプトサイズ: %d 文字, モデル: sonnet=%s / haiku=%s",
            len(prompt), self.model_sonnet, self.model_haiku,
        )

        # z.ai 用の環境変数を設定
        os.environ["ANTHROPIC_AUTH_TOKEN"] = self.api_key
        os.environ["ANTHROPIC_API_KEY"] = ""
        os.environ["ANTHROPIC_BASE_URL"] = "https://api.z.ai/api/anthropic"
        os.environ["API_TIMEOUT_MS"] = "3000000"
        os.environ["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
        os.environ["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = self.model_haiku
        os.environ["ANTHROPIC_DEFAULT_SONNET_MODEL"] = self.model_sonnet
        os.environ["ANTHROPIC_DEFAULT_OPUS_MODEL"] = self.model_opus

        cmd = [
            "claude", "-p", prompt,
            "--dangerously-skip-permissions",
            "--output-format", "stream-json",
            "--verbose",
        ]

        self.logger.info(
            "実行コマンド: claude -p [省略] --dangerously-skip-permissions "
            "--output-format stream-json --verbose (via z.ai, model=%s)",
            self.model_sonnet,
        )

        stdout, stderr, rc = self.run_cli(cmd)
        self.logger.info("Claude Code (z.ai) 終了コード: %d", rc)

        output = stdout + "\n" + stderr
        self.logger.info("出力（先頭5000文字）:\n%s", output[:5000])

        if self.check_flag_exists():
            return

        self.logger.info("=== フラグ未発見 ===")


if __name__ == "__main__":
    ClaudeZaiRunner().run()
