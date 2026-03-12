#!/bin/bash
# ==========================================
# CTFd フラグ提出スクリプト
# ==========================================
# エージェントが発見したフラグをCTFdに提出する。
# 既提出・不正解フラグは再提出せずスキップする。
#
# 使い方:
#   /workspace/submit_flag.sh <challenge_id> "CyberQuest{flag_here}"
#
# 環境変数（コンテナ起動時に自動設定済み）:
#   RELAY_URL   - リレープロキシURL
#   RELAY_TOKEN - セッショントークン

CHALLENGE_ID="$1"
FLAG="$2"

if [ -z "$CHALLENGE_ID" ] || [ -z "$FLAG" ]; then
    echo "Usage: submit_flag.sh <challenge_id> \"flag{...}\""
    exit 1
fi

if [ -z "$RELAY_URL" ] || [ -z "$RELAY_TOKEN" ]; then
    echo "ERROR: 環境変数 RELAY_URL, RELAY_TOKEN が未設定です"
    exit 1
fi

# ── 重複チェック ──────────────────────────────────────────────
STATE_DIR="/workspace/state"
mkdir -p "$STATE_DIR"
SUBMITTED_LOG="${STATE_DIR}/submitted_flags.txt"
WRONG_FLAGS="${STATE_DIR}/wrong_flags.txt"

# 同じフラグが提出済みかチェック
if [ -f "$SUBMITTED_LOG" ] && grep -qFx "${CHALLENGE_ID}:${FLAG}" "$SUBMITTED_LOG"; then
    echo "FLAG_SKIP_DUPLICATE: このフラグは既に提出済みです: ${FLAG}"
    exit 1
fi

# ── フラグ提出（リレー経由、CTFd に直接アクセスしない） ──────
# jq で安全に JSON エスケープ（フラグに " や \ が含まれても壊れない）
JSON_BODY=$(jq -n --arg flag "$FLAG" '{flag: $flag}')

RESPONSE=$(curl -s -X POST "${RELAY_URL}/challenges/${CHALLENGE_ID}/submit" \
    -H "Authorization: Bearer ${RELAY_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$JSON_BODY" \
    2>/dev/null)

if [ -z "$RESPONSE" ]; then
    echo "ERROR: リレーサーバーに接続できません（提出未完了、再試行可能）"
    exit 1
fi

echo "CTFd Response: ${RESPONSE}"

# 提出成功後にログに記録（API応答確認後）
echo "${CHALLENGE_ID}:${FLAG}" >> "$SUBMITTED_LOG"

# ステータスを抽出
STATUS=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('data', {}).get('status', 'unknown'))
except:
    print('error')
" 2>/dev/null)

if [ "$STATUS" = "correct" ] || [ "$STATUS" = "already_solved" ]; then
    # 正解記録
    echo "${CHALLENGE_ID}" >> "${STATE_DIR}/solved_ids.txt"
    echo ""
    echo "=========================================="
    echo "FLAG_CONFIRMED_CORRECT: ${FLAG}"
    echo "  Challenge ID: ${CHALLENGE_ID}"
    echo "=========================================="
    exit 0
else
    # 不正解記録
    echo "${CHALLENGE_ID}:${FLAG}" >> "$WRONG_FLAGS"
    echo ""
    echo "=========================================="
    echo "FLAG_CONFIRMED_INCORRECT: ${FLAG} (status: ${STATUS})"
    echo "  Challenge ID: ${CHALLENGE_ID}"
    echo "=========================================="
    exit 1
fi
