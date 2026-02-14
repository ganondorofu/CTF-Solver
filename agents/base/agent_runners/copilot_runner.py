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
        self.logger.info("=== Copilot実行開始: デバッグ情報 ===")
        
        # 認証状況の詳細確認
        import os
        import subprocess
        
        self.logger.info("認証ディレクトリ確認:")
        copilot_dir = "/root/.copilot"
        if os.path.exists(copilot_dir):
            self.logger.info("認証ディレクトリ存在: %s", copilot_dir)
            for f in os.listdir(copilot_dir):
                self.logger.info("  ファイル: %s", f)
        else:
            self.logger.error("認証ディレクトリ未存在: %s", copilot_dir)
        
        # copilotコマンドの存在確認
        try:
            result = subprocess.run(["which", "copilot"], capture_output=True, text=True)
            self.logger.info("copilotパス: %s", result.stdout.strip())
        except Exception as e:
            self.logger.error("whichコマンドエラー: %s", e)
        
        # copilotバージョン確認
        try:
            result = subprocess.run(["copilot", "--version"], capture_output=True, text=True, timeout=10)
            self.logger.info("copilotバージョン: %s", result.stdout.strip())
            self.logger.info("copilotエラー出力: %s", result.stderr.strip())
        except Exception as e:
            self.logger.error("copilotバージョンチェックエラー: %s", e)
        
        prompt = self.load_prompt()
        self.logger.info("プロンプトサイズ: %d 文字", len(prompt))

        # v0.0.407の正しいコマンド形式（権限許可付き）
        cmd = [
            "copilot",
            "-p", prompt,                 # プロンプトを非対話型で実行
            "--model", "gpt-5-mini",      # 軽量モデルを使用
            "--allow-all",                # 全権限を許可（ファイル操作・コマンド実行・URL）
            "--add-dir", "/workspace",    # ワークスペースへのアクセスを許可
            "-s",                         # サイレントモード（スクリプト向け出力）
        ]
        
        self.logger.info("実行コマンド: %s", ' '.join(cmd[:4]) + ' [プロンプト省略]')

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
