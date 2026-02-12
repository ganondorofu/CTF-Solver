"""
Claude Code CLI ランナー

Anthropicの自律型コーディングエージェント「Claude Code」を使用して
CTF問題を解く。claude CLIは以下の機能を持つ:
- ファイルの読み書き
- Bashコマンドの実行
- コードの作成・修正・実行

使用コマンド:
    claude -p "<prompt>" --dangerously-skip-permissions --output-format text
"""

import sys

sys.path.insert(0, "/agent_runners")
from base_runner import BaseRunner


class ClaudeRunner(BaseRunner):
    """Claude Code CLIを使用する自律型エージェント"""

    def __init__(self):
        super().__init__("claude_code")

    def execute(self):
        """
        Claude Code CLIを実行してCTF問題を解く。

        Claude Codeは自律的にファイルを読み、コードを書き、
        コマンドを実行してフラグを探す。
        --dangerously-skip-permissions で確認ダイアログをスキップする。
        """
        prompt = self.load_prompt()

        # Claude Code CLIを非対話モードで実行
        cmd = [
            "claude",
            "-p", prompt,                         # 非対話モード（プロンプト直接指定）
            "--dangerously-skip-permissions",      # 権限確認をスキップ
            "--output-format", "text",             # テキスト形式で出力
        ]

        stdout, stderr, rc = self.run_cli(cmd)
        self.logger.info("Claude Code 終了コード: %d", rc)

        # 出力をログに記録
        output = stdout + "\n" + stderr
        self.logger.info("出力（先頭5000文字）:\n%s", output[:5000])

        # Claude Codeが直接Flag.txtを作成している場合はそれを使用
        if self.check_flag_exists():
            return

        # 出力テキストからフラグパターンを抽出
        flag = self.extract_flag_from_output(output)
        if flag:
            self.save_flag(flag)


if __name__ == "__main__":
    ClaudeRunner().run()
