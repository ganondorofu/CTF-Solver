"""
Claude Code CLI（Ollama経由）ランナー

Claude Code CLIをOllamaバックエンドで使用してCTF問題を解く。
entrypoint.shでagentユーザーに切り替え済み。

環境変数:
    OLLAMA_HOST: OllamaサーバーのURL
    OLLAMA_MODEL: 使用するモデル名
"""

import os
import sys

sys.path.insert(0, "/agent_runners")
from base_runner import BaseRunner


class ClaudeOllamaRunner(BaseRunner):
    """Claude Code CLI + Ollamaバックエンドで動作するエージェント"""

    def __init__(self):
        super().__init__("claude_ollama")
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.environ.get("OLLAMA_MODEL", "qwen3-coder")

    def execute(self):
        """Claude Code CLIをOllama経由で実行する。"""
        prompt = self.load_prompt()
        self.logger.info("プロンプトサイズ: %d 文字, モデル: %s", len(prompt), self.model)

        # Ollama用の環境変数を設定
        os.environ["ANTHROPIC_AUTH_TOKEN"] = "ollama"
        os.environ["ANTHROPIC_API_KEY"] = ""
        os.environ["ANTHROPIC_BASE_URL"] = self.ollama_host

        cmd = [
            "claude", "-p", prompt,
            "--model", self.model,
            "--dangerously-skip-permissions",
            "--output-format", "stream-json",
            "--verbose",
        ]

        self.logger.info("実行コマンド: claude -p [省略] --model %s --dangerously-skip-permissions", self.model)

        stdout, stderr, rc = self.run_cli(cmd)
        self.logger.info("Claude Code (Ollama) 終了コード: %d", rc)

        output = stdout + "\n" + stderr
        self.logger.info("出力（先頭5000文字）:\n%s", output[:5000])

        if self.check_flag_exists():
            return

        self.logger.info("=== フラグ未発見 ===")


if __name__ == "__main__":
    ClaudeOllamaRunner().run()
