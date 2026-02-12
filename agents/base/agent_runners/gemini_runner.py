"""
Google Gemini CLI ランナー

GoogleのGemini CLIを使用してCTF問題を自律的に解く。
Gemini CLIはコードの生成・実行、ファイル分析などを行う。

使用コマンド:
    gemini -p "<prompt>"
"""

import sys

sys.path.insert(0, "/agent_runners")
from base_runner import BaseRunner


class GeminiRunner(BaseRunner):
    """Google Gemini CLIを使用する自律型エージェント"""

    def __init__(self):
        super().__init__("gemini_cli")

    def execute(self):
        """
        Gemini CLIを実行してCTF問題を解く。

        Gemini CLIは自律的にファイルを分析し、
        コードを生成・実行してフラグを探す。
        """
        prompt = self.load_prompt()

        # Gemini CLIを実行
        cmd = [
            "gemini",
            "-p", prompt,       # プロンプトを直接指定
        ]

        stdout, stderr, rc = self.run_cli(cmd)
        self.logger.info("Gemini CLI 終了コード: %d", rc)

        # 出力をログに記録
        output = stdout + "\n" + stderr
        self.logger.info("出力（先頭5000文字）:\n%s", output[:5000])

        # Gemini CLIが直接Flag.txtを作成している場合
        if self.check_flag_exists():
            return

        # 出力テキストからフラグパターンを抽出
        flag = self.extract_flag_from_output(output)
        if flag:
            self.save_flag(flag)


if __name__ == "__main__":
    GeminiRunner().run()
