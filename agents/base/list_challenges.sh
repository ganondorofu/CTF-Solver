#!/bin/bash
# ==========================================
# 問題一覧取得スクリプト
# ==========================================
# CTFd から問題一覧を取得して表示する。
#
# 使い方:
#   /workspace/list_challenges.sh

if [ -z "$RELAY_URL" ] || [ -z "$RELAY_TOKEN" ]; then
    echo "ERROR: RELAY_URL / RELAY_TOKEN が未設定です"
    exit 1
fi

RESPONSE=$(curl -s "${RELAY_URL}/challenges" \
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

solved = data.get('solved', 0)
total = data.get('total', 0)
print(f'=== CTF Challenges ({solved}/{total} solved) ===')
print()

challenges = sorted(data.get('challenges', []), key=lambda x: x.get('value', 0))
for c in challenges:
    status = 'SOLVED  ' if c.get('solved_by_me') else 'UNSOLVED'
    sid = c.get('id', 0)
    pts = c.get('value', 0)
    cat = c.get('category', '???')
    name = c.get('name', '???')
    solves = c.get('solves', 0)
    claimed = c.get('claimed_by', '')
    extra = f' [WORKING: {claimed}]' if claimed and not c.get('solved_by_me') else ''
    print(f'  [{status}] ID:{sid:4d} | {pts:4d}pts | {cat:12s} | {name} ({solves} solves){extra}')
"
