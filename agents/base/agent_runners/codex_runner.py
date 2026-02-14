"""
OpenAI Codex CLI ランナー

事前準備（ホスト側で1回だけ）:
    codex login

認証: ~/.codex/ がDockerマウントされるため自動認証。

使用コマンド:
    codex exec "prompt" --full-auto -C /workspace/try
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

        `codex exec` で非対話型実行し、
        --full-auto で自動承認モードにする。
        """
        import os
        import subprocess

        self.logger.info("=== Codex実行開始: デバッグ情報 ===")

        # 認証状況の確認
        codex_dir = "/root/.codex"
        if os.path.exists(codex_dir):
            self.logger.info("認証ディレクトリ存在: %s", codex_dir)
            for f in os.listdir(codex_dir):
                self.logger.info("  ファイル: %s", f)
        else:
            self.logger.error("認証ディレクトリ未存在: %s", codex_dir)

        # codexコマンドの存在確認
        try:
            result = subprocess.run(["which", "codex"], capture_output=True, text=True)
            self.logger.info("codexパス: %s", result.stdout.strip())
        except Exception as e:
            self.logger.error("whichコマンドエラー: %s", e)

        # config.tomlに作業ディレクトリを信頼済みとして追加
        config_path = os.path.join(codex_dir, "config.toml")
        try:
            import tomllib
            existing = ""
            if os.path.exists(config_path):
                existing = open(config_path).read()
            # /workspace/tryが未登録なら追加
            if '/workspace/try' not in existing:
                with open(config_path, "a") as f:
                    f.write('\n[projects."/workspace/try"]\ntrust_level = "trusted"\n')
                self.logger.info("config.toml に /workspace/try を信頼済み追加")
        except Exception as e:
            self.logger.warning("config.toml更新失敗: %s", e)

        prompt = self.load_prompt()
        self.logger.info("プロンプトサイズ: %d 文字", len(prompt))

        # Codex CLIを非対話型・完全自動モードで実行
        # Docker内（既にサンドボックス）なので全権限を許可
        cmd = [
            "codex", "exec",
            prompt,
            "--dangerously-bypass-approvals-and-sandbox",  # Docker内なので安全
            "-C", str(self.work_dir),       # 作業ディレクトリを指定
        ]

        self.logger.info("実行コマンド: codex exec [プロンプト省略] --full-auto -C %s", self.work_dir)

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
