#!/bin/bash
# ==========================================
# CTFd フラグ提出スクリプト
# ==========================================
# エージェントが発見したフラグをCTFdに提出し、
# 正解の場合のみ Flag.txt に書き込む。
#
# 使い方:
#   /workspace/submit_flag.sh "CyberQuest{flag_here}"
#
# 環境変数（コンテナ起動時に自動設定済み）:
#   CTFD_URL, CTFD_TOKEN, CHALLENGE_ID

FLAG="$1"

if [ -z "$FLAG" ]; then
    echo "ERROR: フラグが指定されていません"
    echo "使い方: /workspace/submit_flag.sh \"flag{...}\""
    exit 1
fi

if [ -z "$CTFD_URL" ] || [ -z "$CTFD_TOKEN" ] || [ -z "$CHALLENGE_ID" ]; then
    echo "ERROR: 環境変数 CTFD_URL, CTFD_TOKEN, CHALLENGE_ID が未設定です"
    exit 1
fi

# CTFdに提出
RESPONSE=$(curl -s -X POST "${CTFD_URL}/api/v1/challenges/attempt" \
    -H "Authorization: Token ${CTFD_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"challenge_id\": ${CHALLENGE_ID}, \"submission\": \"${FLAG}\"}" \
    2>/dev/null)

echo "CTFd Response: ${RESPONSE}"

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
    # 正解！ Flag.txt に書き込み + 確認マーカー作成
    echo "$FLAG" > /workspace/Flag.txt
    echo "$FLAG" > /workspace/.flag_confirmed
    echo ""
    echo "=========================================="
    echo "FLAG_CONFIRMED_CORRECT: ${FLAG}"
    echo "=========================================="
    exit 0
else
    # 不正解 → wrong_flags.txt に追記
    mkdir -p /workspace/SharedInfo
    echo "$FLAG" >> /workspace/SharedInfo/wrong_flags.txt
    echo ""
    echo "=========================================="
    echo "FLAG_CONFIRMED_INCORRECT: ${FLAG} (status: ${STATUS})"
    echo "=========================================="
    exit 1
fi
