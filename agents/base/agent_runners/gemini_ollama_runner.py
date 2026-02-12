"""
Gemini CLI（Ollama経由）ランナー

OllamaでホストされたGemmaモデルを使用してCTF問題を解く。
Ollamaはテキスト生成のみのため、以下のループで動作:
1. AIに問題を送信し、解法とコマンドを提案させる
2. 提案されたコマンドを抽出・実行
3. 実行結果をAIにフィードバック
4. フラグが見つかるまで繰り返す

OllamaのHTTP APIを直接使用して通信する。
"""

import json
import os
import re
import sys

import requests

sys.path.insert(0, "/agent_runners")
from base_runner import BaseRunner

# 最大対話ループ回数
MAX_ITERATIONS = 15


class GeminiOllamaRunner(BaseRunner):
    """Ollama経由でGemmaモデルを使用するエージェント"""

    def __init__(self):
        super().__init__("gemini_ollama")
        # Ollamaの接続先とモデル名を環境変数から取得
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.environ.get("OLLAMA_MODEL", "gemma3")

    def _chat(self, prompt: str) -> str:
        """
        Ollama APIにプロンプトを送信し、レスポンスを取得する。

        Args:
            prompt: 送信するプロンプト文字列

        Returns:
            AIのレスポンステキスト
        """
        url = f"{self.ollama_host}/api/generate"
        try:
            resp = requests.post(
                url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=300,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            self.logger.error("Ollama API エラー: %s", e)
            return ""

    def _extract_commands(self, text: str) -> list[str]:
        """
        AIレスポンスからシェルコマンドを抽出する。

        ```bash ... ``` または ``` ... ``` ブロックを検索する。

        Args:
            text: AIのレスポンステキスト

        Returns:
            コマンド文字列のリスト
        """
        blocks = re.findall(r'```(?:bash|sh|python)?\n(.*?)```', text, re.DOTALL)
        return [b.strip() for b in blocks if b.strip()]

    def execute(self):
        """
        Ollama経由のGemmaモデルでCTF問題を解く。

        テキスト生成AIとの対話ループ:
        1. 問題文を送信して解法を提案させる
        2. 提案されたコマンドを実行
        3. 実行結果をフィードバック
        4. フラグ発見またはMAX_ITERATIONSまで繰り返す
        """
        prompt = self.load_prompt()

        # 配布ファイルの一覧を取得
        chall_files = []
        if self.chall_dir.exists():
            chall_files = [f.name for f in self.chall_dir.iterdir()]

        # 初回プロンプトの構築
        system_context = (
            "あなたはCTFセキュリティ競技の問題を解くエキスパートです。\n"
            "以下の問題を解いてフラグを見つけてください。\n"
            "解法のためのシェルコマンドやPythonコードを```bash```や```python```ブロックで提示してください。\n"
            "コマンドは /workspace/try/ ディレクトリで実行されます。\n"
            f"配布ファイル: {', '.join(chall_files) if chall_files else 'なし'}\n"
            "配布ファイルは /workspace/chall/ にあります。\n\n"
        )

        conversation = system_context + prompt
        accumulated_results = ""

        for iteration in range(MAX_ITERATIONS):
            if self.check_flag_exists():
                return

            self.logger.info("=== Ollama 対話ループ %d/%d ===", iteration + 1, MAX_ITERATIONS)

            # AIにプロンプトを送信
            response = self._chat(conversation)
            if not response:
                self.logger.warning("AIからの応答がありません")
                break

            self.logger.info("AI応答（先頭2000文字）:\n%s", response[:2000])

            # 応答からフラグを抽出
            flag = self.extract_flag_from_output(response)
            if flag:
                self.save_flag(flag)
                return

            # コマンドを抽出して実行
            commands = self._extract_commands(response)
            if not commands:
                self.logger.info("実行可能なコマンドが提案されませんでした")
                # コマンドが無い場合は具体的なアクションを求める
                conversation = (
                    f"前回の応答:\n{response}\n\n"
                    "具体的に実行するコマンドを```bash```ブロックで提示してください。"
                )
                continue

            # 各コマンドを実行し結果を収集
            exec_results = []
            for i, cmd_block in enumerate(commands):
                if self.check_flag_exists():
                    return

                self.logger.info("コマンド実行 %d:\n%s", i + 1, cmd_block[:500])

                stdout, stderr, rc = self.run_cli(
                    ["bash", "-c", cmd_block],
                    timeout=120,
                )

                result = stdout + "\n" + stderr
                exec_results.append(f"コマンド {i+1} (exit={rc}):\n{result[:2000]}")

                # 実行結果からフラグを抽出
                flag = self.extract_flag_from_output(result)
                if flag:
                    self.save_flag(flag)
                    return

            # 実行結果をフィードバックとして次のプロンプトに含める
            results_text = "\n---\n".join(exec_results)
            accumulated_results += f"\n{results_text}"

            conversation = (
                f"問題:\n{prompt}\n\n"
                f"これまでの実行結果:\n{accumulated_results[-4000:]}\n\n"
                "上記の結果を踏まえて、次に試すべきアプローチを"
                "具体的なコマンド（```bash```ブロック）で提示してください。"
            )

        self.logger.info("最大ループ回数に達しました（%d回）", MAX_ITERATIONS)


if __name__ == "__main__":
    GeminiOllamaRunner().run()
