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
        self.logger.info("=== Gemini実行開始: デバッグ情報 ===")
        
        # 認証状況の詳細確認
        import os
        import subprocess
        import json
        
        self.logger.info("認証ディレクトリ確認:")
        gemini_dir = "/root/.gemini"
        if os.path.exists(gemini_dir):
            self.logger.info("認証ディレクトリ存在: %s", gemini_dir)
            for f in os.listdir(gemini_dir):
                self.logger.info("  ファイル: %s", f)
                
            # 設定ファイルの内容確認と修正
            settings_file = os.path.join(gemini_dir, "settings.json")
            try:
                if os.path.exists(settings_file):
                    with open(settings_file, 'r') as f:
                        settings = json.load(f)
                    self.logger.info("現在の設定: %s", settings)
                else:
                    settings = {}
                    self.logger.info("設定ファイル新規作成")
                
                # モデルを強制設定
                settings['model'] = 'gemini-3-flash-preview'
                
                with open(settings_file, 'w') as f:
                    json.dump(settings, f, indent=2)
                    
                self.logger.info("設定ファイル更新: モデル=gemini-3-flash-preview")
                
            except Exception as e:
                self.logger.error("設定ファイル操作エラー: %s", e)
        else:
            self.logger.error("認証ディレクトリ未存在: %s", gemini_dir)
        
        # geminiコマンドの存在確認
        try:
            result = subprocess.run(["which", "gemini"], capture_output=True, text=True)
            self.logger.info("geminiパス: %s", result.stdout.strip())
        except Exception as e:
            self.logger.error("whichコマンドエラー: %s", e)
        
        # geminiバージョン確認
        try:
            result = subprocess.run(["gemini", "--version"], capture_output=True, text=True, timeout=10)
            self.logger.info("geminiバージョン: %s", result.stdout.strip())
            self.logger.info("geminiエラー出力: %s", result.stderr.strip())
        except Exception as e:
            self.logger.error("geminiバージョンチェックエラー: %s", e)
        
        prompt = self.load_prompt()
        self.logger.info("プロンプトサイズ: %d 文字", len(prompt))

        # Gemini CLIを実行（環境変数でモデル指定も併用）
        cmd = [
            "gemini",
            "--model=gemini-3-flash-preview",  # 高性能モデルを指定
            "-p", prompt,       # プロンプトを直接指定
        ]
        
        self.logger.info("実行コマンド: %s", ' '.join(cmd[:2]) + ' [プロンプト省略]')

        # 環境変数でもモデル指定
        env = os.environ.copy()
        env['GEMINI_MODEL'] = 'gemini-3-flash-preview'

        stdout, stderr, rc = self.run_cli(cmd, env=env)
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
