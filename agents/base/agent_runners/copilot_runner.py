"""
GitHub Copilot CLI ランナー

事前準備（ホスト側で1回だけ）:
    copilot login

認証: ~/.config/copilot/ がDockerマウントされるため自動認証。

使用コマンド:
    copilot -p "<prompt>" --allow-all-tools --silent
"""

import sys
sys.path.insert(0, "/agent_runners")
from base_runner import BaseRunner


class CopilotRunner(BaseRunner):
    """GitHub Copilot CLIを使用するエージェント"""

    def __init__(self):
        super().__init__("copilot_cli")

    def execute(self):
        """
        GitHub Copilot CLIを正しいコマンド形式で実行する。

        v0.0.407の正しいコマンド形式: copilot --model MODEL -p "プロンプト"
        認証はマウント済みの~/.copilot/を使用。
        """
        prompt = self.load_prompt()

        # v0.0.407の正しいコマンド形式
        cmd = [
            "copilot",
            "--model", "gpt-5-mini",  # 軽量モデルを使用
            "-p", prompt
        ]

        stdout, stderr, rc = self.run_cli(cmd)
        self.logger.info("Copilot CLI 終了コード: %d", rc)

        output = stdout + "\n" + stderr
        self.logger.info("出力（先頭5000文字）:\n%s", output[:5000])

        # Copilot CLIが直接Flag.txtを作成している場合
        if self.check_flag_exists():
            return

        # 出力テキストからフラグパターンを抽出
        flag = self.extract_flag_from_output(output)
        if flag:
            self.save_flag(flag)


if __name__ == "__main__":
    CopilotRunner().run()
