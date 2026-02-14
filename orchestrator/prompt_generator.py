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

### フラグ提出方法（最重要）
フラグを発見したら、**必ず以下のコマンドで提出してください**：

```bash
/workspace/submit_flag.sh "発見したフラグ"
```

このスクリプトはCTFdに自動提出し、結果を表示します：
- 正解の場合: "FLAG_CORRECT: ..." と表示され、自動的に記録されます
- 不正解の場合: "FLAG_INCORRECT: ..." と表示されます

**submit_flag.sh を使えば、Flag.txt への保存やcurl実行は不要です。**
**複数のフラグ候補がある場合は、それぞれ submit_flag.sh で試してください。**

### 解法手順
1. 問題文を注意深く読み、カテゴリ（Crypto, Web, Pwn, Rev, Forensics, Misc等）を特定する
2. 配布ファイルを /workspace/chall/ から確認・分析する
3. /workspace/try/ で解法スクリプトを作成・実行する
4. /workspace/SharedInfo/wrong_flags.txt を確認し、過去に不正解だったフラグは避ける
5. /workspace/SharedInfo/approaches.txt を確認し、失敗済みアプローチと異なる方法を試す
6. **フラグを発見したら `/workspace/submit_flag.sh "フラグ"` で提出する**

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
- **フラグ候補を複数試して、正解まで繰り返してください**

### WriteUp作成（最重要・必須）
**submit_flag.sh で正解（FLAG_CORRECT）が確認されたら、必ず次の作業を完了してからセッションを終了してください。**
WriteUpの作成は任意ではありません。正解後の**最優先タスク**です。

以下のパスに**日本語のMarkdown形式**でWriteUpを作成してください：

```
/workspace/WriteUp/writeup.md
```

WriteUpには**必ず**以下をすべて含めてください：
1. **問題の概要** — 問題文の要約とカテゴリ（Crypto, Web, Pwn等）
2. **解法のアプローチ** — どのようなテクニック・ツールを使ったか
3. **具体的な手順** — 実行したコマンドやコードを含む詳細な再現手順
4. **発見したフラグ** — 最終的に正解したフラグ

**注意: WriteUpを書かずにセッションを終了しないでください。WriteUpが無い場合、解答は不完全とみなされます。**
"""

# WriteUp後追い生成用プロンプトテンプレート
WRITEUP_PROMPT_TEMPLATE = """\
# WriteUp作成タスク

あなたはCTF（Capture The Flag）のWriteUp作成アシスタントです。
以下のエージェントの実行ログを読み、**日本語のMarkdown形式**でWriteUpを作成してください。

## 問題文
{problem_text}

## エージェントの実行ログ
```
{log_content}
```

## 正解フラグ
```
{flag}
```

## 指示
上記のログを分析し、以下の構成でWriteUpを `/workspace/WriteUp/writeup.md` に作成してください：

1. **問題の概要** — 問題文の要約とカテゴリ（Crypto, Web, Pwn, Rev, Forensics, Misc等）
2. **解法のアプローチ** — ログから読み取れるテクニック・ツール
3. **具体的な手順** — ログに基づく再現可能な手順（実行コマンドやコードを含む）
4. **発見したフラグ** — 最終的に正解したフラグ

**ログの内容を正確に反映してください。推測で手順を補わないでください。**
**WriteUpファイルを書き終えたら、すぐにセッションを終了してください。**
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

    def generate_writeup_prompt(
        self,
        problem_text: str,
        log_content: str,
        flag: str,
    ) -> str:
        """
        WriteUp後追い生成用のプロンプトを生成する。

        Args:
            problem_text: 問題文
            log_content: 正解エージェントの実行ログ
            flag: 正解フラグ

        Returns:
            WriteUp生成用プロンプト文字列
        """
        # ログが長すぎる場合は末尾を優先（解法に近い部分）
        max_log_chars = 50000
        if len(log_content) > max_log_chars:
            log_content = "...(前略)...\n" + log_content[-max_log_chars:]

        return WRITEUP_PROMPT_TEMPLATE.format(
            problem_text=problem_text,
            log_content=log_content,
            flag=flag,
        )
