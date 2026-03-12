"""
OpenAI Codex CLI ランナー

認証: ~/.codex/auth.json がDockerマウントされるため自動認証。
使用コマンド:
    codex exec "prompt" --dangerously-bypass-approvals-and-sandbox -C /workspace
"""

import sys

sys.path.insert(0, "/agent_runners")
from base_runner import BaseRunner


class CodexRunner(BaseRunner):
    """OpenAI Codex CLIを使用する自律型エージェント"""

    def __init__(self):
        super().__init__("codex_cli")

    def execute(self):
        """Codex CLIを実行してCTF問題を解く。"""
        import os

        # 認証ディレクトリ準備（auth.jsonのみファイルマウントされる）
        codex_dir = "/root/.codex"
        os.makedirs(codex_dir, exist_ok=True)

        # config.tomlに/workspaceを信頼済みとして追加
        config_path = os.path.join(codex_dir, "config.toml")
        try:
            existing = ""
            if os.path.exists(config_path):
                existing = open(config_path).read()
            if '/workspace' not in existing:
                with open(config_path, "a") as f:
                    f.write('\n[projects."/workspace"]\ntrust_level = "trusted"\n')
        except Exception as e:
            self.logger.warning("config.toml更新失敗: %s", e)

        prompt = self.load_prompt()
        self.logger.info("プロンプトサイズ: %d 文字", len(prompt))

        cmd = [
            "codex", "exec",
            prompt,
            "--dangerously-bypass-approvals-and-sandbox",
            "-C", str(self.workspace),
        ]

        self.logger.info("実行コマンド: codex exec [省略] --dangerously-bypass-... -C /workspace")

        stdout, stderr, rc = self.run_cli(cmd)
        self.logger.info("Codex CLI 終了コード: %d", rc)

        output = stdout + "\n" + stderr
        self.logger.info("出力（先頭5000文字）:\n%s", output[:5000])

        if rc != 0:
            self.logger.warning("Codex CLI がエラー終了（rc=%d）、フラグ抽出スキップ", rc)
            return

        if self.check_flag_exists():
            return

        self.logger.info("=== フラグ未発見 ===")


if __name__ == "__main__":
    CodexRunner().run()
