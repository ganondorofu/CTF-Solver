#!/bin/bash
# ==========================================
# 進捗確認スクリプト
# ==========================================
# CTFd での解答状況を確認する。
#
# 使い方:
#   /workspace/get_status.sh

if [ -z "$RELAY_URL" ] || [ -z "$RELAY_TOKEN" ]; then
    echo "ERROR: RELAY_URL / RELAY_TOKEN が未設定です"
    exit 1
fi

RESPONSE=$(curl -s "${RELAY_URL}/status" \
    -H "Authorization: Bearer ${RELAY_TOKEN}" \
    2>/dev/null)

if [ -z "$RESPONSE" ]; then
    echo "ERROR: リレーサーバーに接続できません"
    exit 1
fi

echo "$RESPONSE" | python3 -c "
import sys, json

data = json.load(sys.stdin)
if 'error' in data:
    print(f'ERROR: {data[\"error\"]}')
    sys.exit(1)

total = data.get('total', 0)
solved = data.get('solved', 0)
solved_ids = data.get('solved_ids', [])
remaining = total - solved

print(f'=== CTF Progress ===')
print(f'  Solved:    {solved}/{total}')
print(f'  Remaining: {remaining}')
if solved_ids:
    print(f'  Solved IDs: {solved_ids}')
"
