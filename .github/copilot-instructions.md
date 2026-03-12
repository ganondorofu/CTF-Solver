## 最終的な実装計画（シンプル版）

### 並列化戦略

```
問題1 → 有効化された全エージェントを並列実行
  ├── Claude Code
  ├── OpenAI o1
  ├── Claude Computer Use
  ├── Gemini Thinking
  └── ...（agents.yamlで有効化されたもの）

開発段階: 1問題 × 有効エージェント数
```

### ディレクトリ構造

```
challenges/123/
├── problem.txt              # 問題文
├── prompt.txt               # 共通プロンプト（1つ）
├── Hints.txt                # 無料ヒント（存在する場合のみ）
├── files_metadata.json      # ファイル情報
│
├── chall/                   # 配布ファイル（読み取り専用）
│   └── (ダウンロードファイル)
│
├── Flags/                   # フラグ候補
│   ├── claude_code.txt
│   ├── openai_o1.txt
│   └── summary.json
│
├── Solved-Flag.txt
│
├── WrongFlags/
│   ├── flag_1.txt
│   └── summary.txt          # 不正解サマリー
│
├── WriteUp/
│   └── writeup.md
│
├── Logs/
│   ├── claude_code.log
│   ├── openai_o1.log
│   └── ...
│
├── SharedInfo/
│   ├── wrong_flags.txt
│   └── approaches.txt
│
└── (.running, .solved等)
```

**Docker環境（エージェント実行時）**
```
/workspace/                  # Dockerコンテナ内（毎回初期化）
├── problem.txt
├── prompt.txt
├── Hints.txt               # 存在する場合のみ
├── chall/                  # 配布ファイル
├── try/                    # 作業ディレクトリ（自由に使用）
├── SharedInfo/             # 読み取り専用
│   ├── wrong_flags.txt
│   └── approaches.txt
└── Flag.txt                # フラグ発見時にここに保存
```

### agents.yaml（シンプル版）

```yaml
agents:
  claude_code:
    enabled: true
    model: "claude-3-5-sonnet-20241022"
    api_key: "${ANTHROPIC_API_KEY}"
    
  openai_o1:
    enabled: true
    model: "o1"
    api_key: "${OPENAI_API_KEY}"
    
  claude_computer_use:
    enabled: false
    model: "claude-3-5-sonnet-20241022"
    api_key: "${ANTHROPIC_API_KEY}"
    
  gemini_thinking:
    enabled: true
    model: "gemini-2.0-flash-thinking-exp"
    api_key: "${GOOGLE_API_KEY}"
    
  gemini_ollama:
    enabled: false
    model: "gemini-2.0"
    ollama_host: "http://localhost:11434"

# 実行設定
execution:
  max_concurrent_challenges: 1      # 同時実行問題数
  agent_timeout: 600                # エージェントタイムアウト（秒）
  challenge_timeout: 1800           # 問題タイムアウト（秒）
  workspace_reset: true             # 再試行時にワークスペース初期化

# Docker設定
docker:
  network_mode: "bridge"
  auto_remove: true
  resources:
    memory: "2g"
    cpu_count: 2
```

### config.yaml（シンプル版）

```yaml
ctfd:
  url: "https://ctfd.example.com"
  token: "${CTFD_TOKEN}"

hints:
  allow_cost_hints: false           # コスト付きヒント完全ブロック
  max_cost: 0

files:
  auto_download: true
  max_size: 100

flag_evaluation:
  method: "voting"                  # 多数決
  wait_time: 30                     # フラグ収集待機時間（秒）
```

### プロンプト（1つのみ、ヒントは条件付き）

```
# CTF Challenge

## 問題
{problem_text}

## 配布ファイル
{files_info}

{hints_section}  # ヒントが存在する場合のみ挿入

## 指示
- 作業ディレクトリ: /workspace/try/（自由に使用可能）
- 配布ファイル: /workspace/chall/（読み取り専用）
- フラグ発見時: /workspace/Flag.txt に保存
- 過去の不正解: /workspace/SharedInfo/wrong_flags.txt
- 不正解アプローチ: /workspace/SharedInfo/approaches.txt

## 注意
- 不正解フラグは再提出しない
- 別のアプローチを試す
- このワークスペースは試行ごとに初期化されます
```

### システムフロー

**1. 初期化**
- CTFdから問題取得
- ホスト側にディレクトリ作成（challenges/123/）

**2. 前処理**
- 無料ヒント取得（存在する場合、コスト付きブロック）
- 配布ファイルダウンロード
- プロンプト生成

**3. エージェント実行**
```
for each 有効なエージェント:
    1. Dockerコンテナ起動（新規）
    2. /workspace/ を初期化してマウント
       - problem.txt
       - prompt.txt
       - Hints.txt（存在する場合）
       - chall/（読み取り専用）
       - SharedInfo/（読み取り専用）
    3. エージェントAI実行
    4. Flag.txt を監視
    5. フラグ発見時にホストに転送
    6. コンテナ終了・削除
```

**4. 再試行**
```
if フラグが不正解:
    1. WrongFlags/に追加
    2. summary.txt更新
    3. SharedInfo/更新
    4. 新しいDockerコンテナで再実行（ワークスペース初期化済み）
```

**5. フラグ評価**
- 全エージェントからフラグ収集（30秒待機）
- 多数決で提出するフラグを決定
- CTFdに提出

**6. 結果処理**
- 正解 → Solved-Flag.txt保存、.solved作成
- 不正解 → WrongFlags/に追加、再試行

### project構成

```
project/
├── orchestrator/
│   ├── main.py
│   ├── ctfd_client.py
│   ├── challenge_manager.py
│   ├── hint_manager.py
│   ├── file_manager.py
│   ├── docker_manager.py
│   ├── flag_collector.py
│   └── prompt_generator.py
│
├── agents/
│   ├── base/
│   │   └── Dockerfile.base
│   │
│   └── entrypoint.sh          # 共通エントリーポイント
│
├── config/
│   ├── config.yaml
│   └── agents.yaml
│
├── challenges/                # 実行時に生成
│
└── requirements.txt
```

### 開発フェーズ

**Week 1: 基礎**
- CTFd連携
- ディレクトリ自動生成
- ヒント管理（コスト付きブロック、存在チェック）
- ファイル管理
- 1エージェントで動作確認

**Week 2: 並列化**
- agents.yamlから有効エージェント読み込み
- 複数エージェント並列実行
- Dockerワークスペース初期化
- フラグ収集・投票

**Week 3: 本番準備**
- 不正解サマリー自動生成
- 再試行ロジック
- エラーハンドリング
- 実戦テスト