"""
Google Gemini CLI ランナー

使用コマンド:
    gemini --sandbox=false --yolo -p "<prompt>"
"""

import sys

sys.path.insert(0, "/agent_runners")
from base_runner import BaseRunner


class GeminiRunner(BaseRunner):
    """Google Gemini CLIを使用する自律型エージェント"""

    def __init__(self):
        super().__init__("gemini_cli")

    def execute(self):
        """Gemini CLIを実行してCTF問題を解く。"""
        import os
        import json

        model = os.environ.get("AGENT_MODEL", "gemini-2.5-flash-preview-05-20")
        gemini_dir = "/root/.gemini"
        os.makedirs(gemini_dir, exist_ok=True)

        # settings.json にモデルを設定（v0.28+ オブジェクト形式）
        settings_file = os.path.join(gemini_dir, "settings.json")
        try:
            settings = {}
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)

            # AGENT_MODEL で指定されたモデルを設定
            settings['model'] = {'name': model}
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            self.logger.info("settings.json model設定: %s", model)
        except Exception as e:
            self.logger.warning("settings.json操作エラー: %s", e)

        # trustedFolders.json に /workspace を追加
        trusted_file = os.path.join(gemini_dir, "trustedFolders.json")
        try:
            trusted = {}
            if os.path.exists(trusted_file):
                with open(trusted_file, 'r') as f:
                    trusted = json.load(f)
            if "/workspace" not in trusted:
                trusted["/workspace"] = "TRUST_FOLDER"
                with open(trusted_file, 'w') as f:
                    json.dump(trusted, f, indent=2)
        except Exception as e:
            self.logger.warning("trustedFolders更新エラー: %s", e)

        prompt = self.load_prompt()
        self.logger.info("プロンプトサイズ: %d 文字, モデル: %s", len(prompt), model)

        # Gemini CLI実行（sandbox無効 + yoloモード、Docker内なので安全）
        cmd = [
            "gemini",
            "--sandbox=false",
            "--yolo",
            "-p", prompt,
        ]

        self.logger.info("実行コマンド: gemini --sandbox=false --yolo -p [省略] (model=%s)", model)

        stdout, stderr, rc = self.run_cli(cmd)
        self.logger.info("Gemini CLI 終了コード: %d", rc)

        output = stdout + "\n" + stderr
        self.logger.info("出力（先頭5000文字）:\n%s", output[:5000])

        if self.check_flag_exists():
            return

        self.logger.info("=== フラグ未発見 ===")


if __name__ == "__main__":
    GeminiRunner().run()
