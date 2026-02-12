#!/bin/bash
# ==========================================
# CTF Agent エントリーポイント
# ==========================================
# 環境変数 AGENT_TYPE に応じて適切なランナーを起動する。
# Docker コンテナ起動時に自動実行される。

set -e

echo "=========================================="
echo " CTF Agent: ${AGENT_NAME}"
echo " Type:      ${AGENT_TYPE}"
echo " Timeout:   ${AGENT_TIMEOUT}s"
echo "=========================================="
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
case "${AGENT_TYPE}" in
    claude_code)
        echo ">>> Claude Code CLI ランナーを起動..."
        python3 /agent_runners/claude_runner.py
        ;;
    codex_cli)
        echo ">>> Codex CLI ランナーを起動..."
        python3 /agent_runners/codex_runner.py
        ;;
    copilot_cli)
        echo ">>> GitHub Copilot CLI ランナーを起動..."
        python3 /agent_runners/copilot_runner.py
        ;;
    gemini_cli)
        echo ">>> Gemini CLI ランナーを起動..."
        python3 /agent_runners/gemini_runner.py
        ;;
    gemini_ollama)
        echo ">>> Gemini CLI (Ollama) ランナーを起動..."
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
else
    echo " フラグ未発見"
fi
echo "=========================================="
