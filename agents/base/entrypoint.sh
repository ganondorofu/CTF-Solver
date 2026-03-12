#!/bin/bash
# ==========================================
# CTF Agent Entrypoint (v2: Autonomous Mode)
# ==========================================
# 環境変数 AGENT_TYPE に応じて適切なランナーを起動する。

set -e

echo "=== CTF Agent: ${AGENT_NAME} (${AGENT_TYPE}) ==="
echo "=== Mode: Autonomous ==="

# プロンプトの存在確認
if [ ! -f /workspace/prompt.txt ]; then
    echo "ERROR: /workspace/prompt.txt が見つかりません"
    exit 1
fi

# 作業ディレクトリを確認
mkdir -p /workspace/challenges /workspace/state

# ツールスクリプトに実行権限を付与
for script in list_challenges.sh get_challenge.sh submit_flag.sh get_status.sh; do
    [ -f "/workspace/${script}" ] && chmod +x "/workspace/${script}"
done

# AGENT_TYPE に応じたランナーを起動
case "${AGENT_TYPE}" in
    claude_code)
        chown -R agent:agent /workspace 2>/dev/null || true
        su agent -c "python3 /agent_runners/claude_runner.py"
        ;;
    claude_ollama)
        chown -R agent:agent /workspace 2>/dev/null || true
        su agent -c "python3 /agent_runners/claude_ollama_runner.py"
        ;;
    claude_zai)
        chown -R agent:agent /workspace 2>/dev/null || true
        su agent -c "python3 /agent_runners/claude_zai_runner.py"
        ;;
    kimi)
        chown -R agent:agent /workspace 2>/dev/null || true
        su agent -c "python3 /agent_runners/kimi_runner.py"
        ;;
    codex_cli)
        python3 /agent_runners/codex_runner.py
        ;;
    copilot_cli)
        python3 /agent_runners/copilot_runner.py
        ;;
    gemini_cli)
        python3 /agent_runners/gemini_runner.py
        ;;
    *)
        echo "ERROR: 未知のエージェントタイプ: ${AGENT_TYPE}"
        echo "有効なタイプ: claude_code, claude_ollama, claude_zai, kimi, codex_cli, copilot_cli, gemini_cli"
        exit 1
        ;;
esac

echo "=== エージェント ${AGENT_NAME} 終了 ==="
