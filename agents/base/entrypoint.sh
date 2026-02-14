#!/bin/bash
# ==========================================
# CTF Agent エントリーポイント
# ==========================================
# 環境変数 AGENT_TYPE に応じて適切なランナーを起動する。
# Docker コンテナ起動時に自動実行される。

set -e

# デバッグモードを有効化
set -x

echo "=========================================="
echo " CTF Agent: ${AGENT_NAME}"
echo " Type:      ${AGENT_TYPE}"
echo " Timeout:   ${AGENT_TIMEOUT}s"
echo "=========================================="
echo ""

# 環境変数の詳細表示
echo "=== 環境変数詳細 ==="
echo "AGENT_NAME: ${AGENT_NAME}"
echo "AGENT_TYPE: ${AGENT_TYPE}"
echo "AGENT_TIMEOUT: ${AGENT_TIMEOUT}"
echo "PATH: ${PATH}"
echo "PWD: $(pwd)"
echo ""

# インストールされているCLIツールの確認
echo "=== インストール済みCLIツール ==="
echo -n "copilot: "; which copilot 2>/dev/null && copilot --version || echo "NOT FOUND"
echo -n "codex: "; which codex 2>/dev/null && codex --version || echo "NOT FOUND"
echo -n "gemini: "; which gemini 2>/dev/null && gemini --version || echo "NOT FOUND"
echo -n "python3: "; which python3 2>/dev/null && python3 --version || echo "NOT FOUND"
echo ""

# ワークスペースの内容を表示
echo "=== ワークスペース内容 ==="
ls -la /workspace/
echo ""

# 配布ファイルの確認
if [ -d /workspace/chall ] && [ "$(ls -A /workspace/chall 2>/dev/null)" ]; then
    echo "=== 配布ファイル ==="
    ls -la /workspace/chall/
    echo ""
fi

# プロンプトの存在確認
if [ ! -f /workspace/prompt.txt ]; then
    echo "ERROR: /workspace/prompt.txt が見つかりません"
    exit 1
fi

# 作業ディレクトリを作成
mkdir -p /workspace/try

# AGENT_TYPEに応じたランナーを起動
echo "=== ランナー起動準備 ==="
echo "起動するランナー: ${AGENT_TYPE}"
echo "Pythonランナーファイル確認:"
ls -la /agent_runners/
echo ""

case "${AGENT_TYPE}" in
    claude_code)
        echo ">>> Claude Code CLI ランナーを起動..."
        echo "実行コマンド: python3 /agent_runners/claude_runner.py"
        python3 /agent_runners/claude_runner.py
        ;;
    codex_cli)
        echo ">>> Codex CLI ランナーを起動..."
        echo "実行コマンド: python3 /agent_runners/codex_runner.py"
        echo "認証ディレクトリ確認:"
        ls -la /root/.codex/ 2>/dev/null || echo "認証ディレクトリなし"
        echo "開始前最終チェック..."
        python3 /agent_runners/codex_runner.py
        ;;
    copilot_cli)
        echo ">>> GitHub Copilot CLI ランナーを起動..."
        echo "実行コマンド: python3 /agent_runners/copilot_runner.py"
        echo "認証ディレクトリ確認:"
        ls -la /root/.copilot/ 2>/dev/null || echo "認証ディレクトリなし"
        echo "開始前最終チェック..."
        python3 /agent_runners/copilot_runner.py
        ;;
    gemini_cli)
        echo ">>> Gemini CLI ランナーを起動..."
        echo "実行コマンド: python3 /agent_runners/gemini_runner.py"
        echo "認証ディレクトリ確認:"
        ls -la /root/.gemini/ 2>/dev/null || echo "認証ディレクトリなし"
        echo "Gemini設定確認:"
        cat /root/.gemini/settings.json 2>/dev/null || echo "設定ファイルなし"
        echo "開始前最終チェック..."
        python3 /agent_runners/gemini_runner.py
        ;;
    gemini_ollama)
        echo ">>> Gemini CLI (Ollama) ランナーを起動..."
        echo "実行コマンド: python3 /agent_runners/gemini_ollama_runner.py"
        python3 /agent_runners/gemini_ollama_runner.py
        ;;
    *)
        echo "ERROR: 未知のエージェントタイプ: ${AGENT_TYPE}"
        echo "有効なタイプ: claude_code, codex_cli, copilot_cli, gemini_cli, gemini_ollama"
        exit 1
        ;;
esac

# 結果の確認
echo ""
echo "=========================================="
if [ -f /workspace/Flag.txt ] && [ -s /workspace/Flag.txt ]; then
    echo " フラグ発見: $(cat /workspace/Flag.txt)"
    
    # WriteUpが未生成の場合、警告のみ（ダミーは生成しない）
    if [ ! -s /workspace/WriteUp/writeup.md ]; then
        echo " WARNING: WriteUp未生成 - エージェントがWriteUpを作成しませんでした"
    else
        echo " WriteUp確認済み: /workspace/WriteUp/writeup.md"
    fi
else
    echo " フラグ未発見"
fi
echo "=========================================="
