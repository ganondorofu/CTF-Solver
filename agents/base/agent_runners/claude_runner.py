"""
Claude Code CLI ランナー

Anthropicの自律型コーディングエージェント「Claude Code」を使用して
CTF問題を解く。entrypoint.shでagentユーザーに切り替え済み。

使用コマンド:
    claude -p "<prompt>" --dangerously-skip-permissions --output-format stream-json --verbose
"""

import sys

sys.path.insert(0, "/agent_runners")
from base_runner import BaseRunner


class ClaudeRunner(BaseRunner):
    """Claude Code CLIを使用する自律型エージェント"""

    def __init__(self):
        super().__init__("claude_code")

    def execute(self):
        """Claude Code CLIを実行してCTF問題を解く。"""
        prompt = self.load_prompt()
        self.logger.info("プロンプトサイズ: %d 文字", len(prompt))

        cmd = [
            "claude", "-p", prompt,
            "--dangerously-skip-permissions",
            "--output-format", "stream-json",
            "--verbose",
        ]

        self.logger.info("実行コマンド: claude -p [省略] --dangerously-skip-permissions --output-format stream-json --verbose")

        stdout, stderr, rc = self.run_cli(cmd)
        self.logger.info("Claude Code 終了コード: %d", rc)

        output = stdout + "\n" + stderr
        self.logger.info("出力（先頭5000文字）:\n%s", output[:5000])

        if self.check_flag_exists():
            return

        self.logger.info("=== フラグ未発見 ===")


if __name__ == "__main__":
    ClaudeRunner().run()
