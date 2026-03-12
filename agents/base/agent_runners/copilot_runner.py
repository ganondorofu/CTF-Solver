"""
GitHub Copilot CLI ランナー

認証: ~/.copilot/ がDockerマウントされるため自動認証。
使用コマンド:
    copilot -p "<prompt>" --allow-all --add-dir /workspace -s
"""

import sys
sys.path.insert(0, "/agent_runners")
from base_runner import BaseRunner


class CopilotRunner(BaseRunner):
    """GitHub Copilot CLIを使用するエージェント"""

    def __init__(self):
        super().__init__("copilot_cli")

    def execute(self):
        """GitHub Copilot CLIを実行する。"""
        import os
        model = os.environ.get("AGENT_MODEL", "gpt-4.1")
        prompt = self.load_prompt()
        self.logger.info("プロンプトサイズ: %d 文字, モデル: %s", len(prompt), model)

        cmd = [
            "copilot",
            "-p", prompt,
            "--model", model,
            "--allow-all",
            "--add-dir", "/workspace",
        ]

        self.logger.info("実行コマンド: copilot -p [省略] --model %s --allow-all --add-dir /workspace", model)

        stdout, stderr, rc = self.run_cli(cmd)
        self.logger.info("Copilot CLI 終了コード: %d", rc)

        output = stdout + "\n" + stderr
        self.logger.info("出力（先頭5000文字）:\n%s", output[:5000])

        if self.check_flag_exists():
            return

        # submit_flag.sh が正解時に Flag.txt と .flag_confirmed を作成するため、
        # ログからの正規表現フォールバック抽出は不要（誤検知防止）
        self.logger.info("=== フラグ未発見 ===")


if __name__ == "__main__":
    CopilotRunner().run()
