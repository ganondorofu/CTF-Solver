"""
プロンプト生成モジュール

問題文、配布ファイル情報、ヒントを組み合わせて
AIエージェントに渡すプロンプトを生成する。
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# エージェントに渡すプロンプトテンプレート
PROMPT_TEMPLATE = """\
# CTF Challenge

## 問題文
{problem_text}

## 配布ファイル
{files_info}
{hints_section}
## 作業指示
あなたはCTF（Capture The Flag）セキュリティ競技の問題を解くAIエージェントです。
以下の手順で問題を解いてください。

### 環境
- 作業ディレクトリ: /workspace/try/（自由に使用可能、コード作成・実行可能）
- 配布ファイル: /workspace/chall/（読み取り専用、問題の配布ファイル）
- 過去の不正解フラグ: /workspace/SharedInfo/wrong_flags.txt
- 過去の失敗アプローチ: /workspace/SharedInfo/approaches.txt
- **シェルコマンド実行**: `bash -c "コマンド"` でシェルコマンドが実行可能
- **Python実行**: `python3 script.py` でPythonスクリプトが実行可能

### CTFdプラットフォーム情報
- **CTFd URL**: {ctfd_url}
- **認証トークン**: {ctfd_token}
- **問題ID**: {challenge_id}

### フラグ提出方法
フラグを発見したら、以下のcurlコマンドで **直接CTFdに提出**してください：

**重要: フラグ発見後、必ずこのcurlコマンドを実行してください**

```bash
curl -X POST "{ctfd_url}/api/v1/challenges/attempt" \\
  -H "Authorization: Token {ctfd_token}" \\
  -H "Content-Type: application/json" \\
  -d '{{"challenge_id": {challenge_id}, "submission": "YOUR_FLAG_HERE"}}'
```

**提出例:**
```bash
# フラグ例: CyberQuest{{WannaCry}}
curl -X POST "{ctfd_url}/api/v1/challenges/attempt" \\
  -H "Authorization: Token {ctfd_token}" \\
  -H "Content-Type: application/json" \\
  -d '{{"challenge_id": {challenge_id}, "submission": "CyberQuest{{WannaCry}}"}}'
```

### 解法手順
1. 問題文を注意深く読み、カテゴリ（Crypto, Web, Pwn, Rev, Forensics, Misc等）を特定する
2. 配布ファイルを /workspace/chall/ から確認・分析する
3. /workspace/try/ で解法スクリプトを作成・実行する
4. /workspace/SharedInfo/wrong_flags.txt を確認し、過去に不正解だったフラグは避ける
5. /workspace/SharedInfo/approaches.txt を確認し、失敗済みアプローチと異なる方法を試す
6. **フラグを発見したら上記のcurlコマンドで直接提出する**

### 利用可能なツール・コマンド
- **ファイル操作**: `unzip`, `tar`, `ls`, `cat`, `file`, `strings`
- **バイナリ解析**: `checksec`, `objdump`, `readelf`, `nm`, `gdb`
- **ネットワーク**: `nc`, `curl`, `wget`, `nmap`
- **開発ツール**: `gcc`, `python3`, `pip3`
- **CTFツール**: `pwntools`（Pythonライブラリ）
- **テキスト処理**: `grep`, `sed`, `awk`, `head`, `tail`

### 重要な注意事項
- フラグは通常 flag{{...}} や CTF{{...}} の形式です
- 過去の不正解フラグを再提出しないでください
- 失敗したアプローチとは異なる方法を試してください
- このワークスペースは各試行で初期化されます
- 必要なツール（Python, GCC, binutils等）はインストール済みです
- **成功したフラグ提出は即座にcurlで実行してください**
- **フラグ候補を複数試して、成功まで繰り返してください**
- **必ずcurlコマンドの結果を確認し、"success":trueになるまで続けてください**
- **フラグ提出成功の確認例: {{"success": true, "data": {{"status": "correct"}}}}**
"""


class PromptGenerator:
    """問題情報からプロンプトを生成するクラス"""

    def generate(
        self,
        problem_text: str,
        files_metadata: list[dict],
        hints_text: Optional[str] = None,
        ctfd_url: str = "",
        ctfd_token: str = "",
        challenge_id: int = 0,
    ) -> str:
        """
        エージェント用のプロンプトを生成する。

        Args:
            problem_text: CTFdから取得した問題文
            files_metadata: 配布ファイルのメタデータリスト
            hints_text: 整形済みヒントテキスト（存在しない場合はNone）
            ctfd_url: CTFdプラットフォームのURL
            ctfd_token: CTFd認証トークン
            challenge_id: 問題ID

        Returns:
            完成したプロンプト文字列
        """
        # 配布ファイル情報を整形
        files_info = self._format_files(files_metadata)

        # ヒントセクションを構築（存在する場合のみ）
        hints_section = ""
        if hints_text:
            hints_section = f"\n## ヒント\n{hints_text}\n"

        return PROMPT_TEMPLATE.format(
            problem_text=problem_text,
            files_info=files_info,
            hints_section=hints_section,
            ctfd_url=ctfd_url,
            ctfd_token=ctfd_token,
            challenge_id=challenge_id,
        )

    @staticmethod
    def _format_files(metadata: list[dict]) -> str:
        """
        ファイルメタデータをプロンプト用テキストに整形する。

        Args:
            metadata: ファイルメタデータのリスト

        Returns:
            整形されたファイル情報テキスト
        """
        if not metadata:
            return "配布ファイルはありません。"

        lines = []
        for m in metadata:
            status = m.get("status", "unknown")
            name = m.get("filename", "unknown")
            size = m.get("size", 0)
            if status == "downloaded":
                lines.append(f"- {name}（{size} bytes）→ /workspace/chall/{name}")
            else:
                lines.append(f"- {name}（{status}）")
        return "\n".join(lines)
