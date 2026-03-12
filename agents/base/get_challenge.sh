#!/bin/bash
# ==========================================
# 問題詳細取得・ファイルダウンロードスクリプト
# ==========================================
# CTFd から問題の詳細情報を取得し、配布ファイルをダウンロードする。
# /workspace/challenges/<id>/ にワークスペースを自動構築する。
#
# 使い方:
#   /workspace/get_challenge.sh <challenge_id>

ID="$1"
if [ -z "$ID" ]; then
    echo "Usage: get_challenge.sh <challenge_id>"
    exit 1
fi

if [ -z "$RELAY_URL" ] || [ -z "$RELAY_TOKEN" ]; then
    echo "ERROR: RELAY_URL / RELAY_TOKEN が未設定です"
    exit 1
fi

# ディレクトリ作成
CDIR="/workspace/challenges/${ID}"
mkdir -p "${CDIR}/chall" "${CDIR}/try"

# チャレンジを作業予約（他エージェントとの重複回避）
CLAIM_RESP=$(curl -s -X POST "${RELAY_URL}/claim/${ID}" \
    -H "Authorization: Bearer ${RELAY_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"agent\": \"${AGENT_NAME:-unknown}\"}" \
    2>/dev/null)
CLAIM_STATUS=$(echo "$CLAIM_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
if [ "$CLAIM_STATUS" = "claimed" ]; then
    CLAIMED_BY=$(echo "$CLAIM_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('by',''))" 2>/dev/null)
    echo "WARNING: Challenge ${ID} is already being worked on by ${CLAIMED_BY}. Consider choosing another challenge."
elif [ "$CLAIM_STATUS" = "already_solved" ]; then
    echo "SKIP: Challenge ${ID} is already solved."
    exit 0
fi

# 問題詳細を取得
RESPONSE=$(curl -s "${RELAY_URL}/challenges/${ID}" \
    -H "Authorization: Bearer ${RELAY_TOKEN}" \
    2>/dev/null)

if [ -z "$RESPONSE" ]; then
    echo "ERROR: リレーサーバーに接続できません"
    exit 1
fi

# 問題情報を保存・表示し、ファイルパスを抽出
FILE_PATHS=$(echo "$RESPONSE" | python3 -c "
import sys, json, os

data = json.load(sys.stdin)
cdir = '${CDIR}'

if 'error' in data:
    print(f'ERROR: {data[\"error\"]}', file=sys.stderr)
    sys.exit(1)

# problem.txt に保存
desc = data.get('description', '')
with open(os.path.join(cdir, 'problem.txt'), 'w') as f:
    f.write(desc)

# hints.txt に保存（存在する場合）
hints = data.get('hints', [])
if hints:
    with open(os.path.join(cdir, 'hints.txt'), 'w') as f:
        for i, h in enumerate(hints, 1):
            f.write(f'Hint {i}: {h}\n\n')

# 表示
print(f'=== Challenge {data.get(\"id\")}: {data.get(\"name\", \"???\")} ===', file=sys.stderr)
print(f'Category: {data.get(\"category\", \"???\")}  |  Value: {data.get(\"value\", 0)}pts  |  Solves: {data.get(\"solves\", 0)}', file=sys.stderr)
conn = data.get('connection_info', '')
if conn:
    print(f'Connection: {conn}', file=sys.stderr)
print(file=sys.stderr)
print('--- Description ---', file=sys.stderr)
print(desc, file=sys.stderr)
if hints:
    print(file=sys.stderr)
    print('--- Hints ---', file=sys.stderr)
    for i, h in enumerate(hints, 1):
        print(f'Hint {i}: {h}', file=sys.stderr)

# ファイルパスを stdout に出力（ダウンロード用）
files = data.get('files', [])
for f in files:
    print(f'{f[\"path\"]}|{f[\"name\"]}')
")

if [ $? -ne 0 ]; then
    exit 1
fi

# ファイルダウンロード（リトライ付き）
download_file() {
    local fpath="$1" fname="$2" dest="$3"
    local attempt max_attempts=3
    for attempt in $(seq 1 $max_attempts); do
        HTTP_CODE=$(curl -s -w "%{http_code}" "${RELAY_URL}/download/${fpath}" \
            -H "Authorization: Bearer ${RELAY_TOKEN}" \
            -o "${dest}" 2>/dev/null)
        FSIZE=$(stat -c%s "${dest}" 2>/dev/null || echo 0)
        if [ "$HTTP_CODE" = "200" ] && [ "$FSIZE" -gt 0 ]; then
            echo "  → ${dest} (${FSIZE} bytes)"
            return 0
        fi
        echo "  WARNING: Download failed (HTTP ${HTTP_CODE}, attempt ${attempt}/${max_attempts})"
        [ "$attempt" -lt "$max_attempts" ] && sleep 2
    done
    echo "  ERROR: Failed to download ${fname} after ${max_attempts} attempts"
    return 1
}

if [ -n "$FILE_PATHS" ]; then
    echo "$FILE_PATHS" | while IFS='|' read -r FPATH FNAME; do
        [ -z "$FPATH" ] && continue
        echo "Downloading: ${FNAME}..."
        download_file "$FPATH" "$FNAME" "${CDIR}/chall/${FNAME}"
    done
else
    echo "  (No files to download)"
fi

echo ""
echo "=== Challenge ${ID} ready ==="
echo "  Problem:  ${CDIR}/problem.txt"
echo "  Files:    ${CDIR}/chall/"
echo "  Work dir: ${CDIR}/try/"
[ -f "${CDIR}/hints.txt" ] && echo "  Hints:    ${CDIR}/hints.txt"

# 他エージェントからの情報を取得・表示
WRONG_RESP=$(curl -s "${RELAY_URL}/wrong_flags/${ID}" \
    -H "Authorization: Bearer ${RELAY_TOKEN}" 2>/dev/null)
WRONG_FLAGS=$(echo "$WRONG_RESP" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    flags = d.get('wrong_flags', [])
    if flags:
        print('\n'.join(flags))
except: pass
" 2>/dev/null)
if [ -n "$WRONG_FLAGS" ]; then
    echo ""
    echo "=== Known Wrong Flags (from all agents) ==="
    echo "$WRONG_FLAGS"
    echo "  → Do NOT resubmit these."
fi

NOTES_RESP=$(curl -s "${RELAY_URL}/notes/${ID}" \
    -H "Authorization: Bearer ${RELAY_TOKEN}" 2>/dev/null)
NOTES_TEXT=$(echo "$NOTES_RESP" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    notes = d.get('notes', [])
    for n in notes:
        print(f'[{n[\"agent\"]}]')
        print(n['notes'][:500])
        print()
except: pass
" 2>/dev/null)
if [ -n "$NOTES_TEXT" ]; then
    echo ""
    echo "=== Notes from other agents ==="
    echo "$NOTES_TEXT"
    echo "  → Use these findings. Try a DIFFERENT approach from failed ones."
fi

exit 0
