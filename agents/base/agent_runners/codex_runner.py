"""
OpenAI Codex CLI ランナー

OpenAIの自律型コーディングエージェント「Codex CLI」を使用して
CTF問題を解く。Codex CLIは以下の機能を持つ:
- ファイルの読み書き
- シェルコマンドの実行
- コードの生成・実行

使用コマンド:
    codex --approval-mode full-auto -q "<prompt>"
"""

import sys

sys.path.insert(0, "/agent_runners")
from base_runner import BaseRunner


class CodexRunner(BaseRunner):
    """OpenAI Codex CLIを使用する自律型エージェント"""

    def __init__(self):
        super().__init__("codex_cli")

    def execute(self):
        """
        Codex CLIを実行してCTF問題を解く。

        --approval-mode full-auto で全操作を自動承認し、
        -q（quiet）で非対話的に実行する。
        """
        prompt = self.load_prompt()

        # Codex CLIを完全自動モードで実行
        cmd = [
            "codex",
            "--approval-mode", "full-auto",   # 全操作を自動承認
            "-q",                              # クワイエットモード
            prompt,
        ]

        stdout, stderr, rc = self.run_cli(cmd)
        self.logger.info("Codex CLI 終了コード: %d", rc)

        # 出力をログに記録
        output = stdout + "\n" + stderr
        self.logger.info("出力（先頭5000文字）:\n%s", output[:5000])

        # Codex CLIが直接Flag.txtを作成している場合はそれを使用
        if self.check_flag_exists():
            return

        # 出力テキストからフラグパターンを抽出
        flag = self.extract_flag_from_output(output)
        if flag:
            self.save_flag(flag)


if __name__ == "__main__":
    CodexRunner().run()
