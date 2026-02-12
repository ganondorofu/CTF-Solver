# CTF Solver - AI駆動自動CTF解答システム

複数のAIエージェントを並列実行してCTF（Capture The Flag）問題を自動解答するシステムです。

## 🚀 特徴

- **複数AIエージェント対応**: GitHub Copilot CLI、Gemini CLI等のコーディングAIを自動実行
- **完全並列実行**: 複数エージェントが同時に問題を解き、多数決でフラグを決定
- **自動化された前処理**: 問題文・ヒント取得、配布ファイルダウンロード、プロンプト生成
- **Docker分離実行**: 各エージェントは独立したコンテナ内で安全に実行
- **不正解フラグ管理**: 過去の失敗を記録し、エージェント間で共有して重複を防止
- **CTFd統合**: CTFdプラットフォームから問題取得、フラグ自動提出

## 📋 必要な環境

### システム要件
- Linux/WSL2 または macOS
- Python 3.11+
- Docker
- 各AI CLIツール（後述）

### AIサービスアカウント
各エージェントに応じたアカウント・認証が必要です：
- **GitHub Copilot CLI**: GitHub Copilot契約
- **Gemini CLI**: Google AI Studioアカウント

## ⚙️ セットアップ

### 1. リポジトリのクローンと依存関係インストール

```bash
git clone <このリポジトリ>
cd CTF-Solver

# Python仮想環境の作成・有効化
python3 -m venv .venv
source .venv/bin/activate  # Windowsの場合: .venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env`ファイルを編集してCTFd接続情報を設定：

```bash
cp .env .env.backup
nano .env
```

```env
# CTFd接続情報（必須）
CTFD_URL=https://your-ctfd-platform.com
CTFD_TOKEN=your_ctfd_api_token_here

# Ollama接続先（Ollama使用時のみ）
OLLAMA_HOST=http://localhost:11434
```

### 3. Dockerの準備

```bash
# Docker起動確認
docker info

# 権限設定（Linuxの場合、実行後は再ログインが必要）
sudo usermod -aG docker $USER
```

### 4. AI CLIツールの認証

使用するエージェントに応じて、ホスト側で事前にログインします：

#### Claude Code CLI
```bash
# Claude CLIのインストールと認証
npm install -g @anthropic-ai/claude-code
claude login
```

#### Codex CLI  
```bash
# Codex CLIのインストールと認証
npm install -g @openai/codex
codex auth
```

#### GitHub Copilot CLI
```bash
# GitHub Copilot CLI v0.0.407（独立バイナリ版）をインストール
# 最新版をGitHubリリースページからダウンロード:
# https://github.com/github/copilot-cli/releases

# 例: Linuxの場合
curl -L -o copilot.tar.gz "https://github.com/github/copilot-cli/releases/download/v0.0.407/copilot-linux-x64.tar.gz"
tar -xzf copilot.tar.gz
sudo mv copilot /usr/local/bin/

# 認証
copilot login
```

**注意**: 旧式の `gh extension install github/gh-copilot` は使用しません。v0.0.407は独立バイナリです。

#### Gemini CLI
```bash
# Gemini CLIのインストールと認証
npm install -g @google/gemini-cli
gemini auth login
```

#### Gemini CLI (Ollama)
```bash
# Ollamaのインストール（Linux）
curl -fsSL https://ollama.com/install.sh | sh

# モデルのダウンロード
ollama pull gemma3  # または他の対応モデル

# Ollamaサーバー起動（バックグラウンド）
ollama serve &
```

### 5. Dockerイメージのビルド

```bash
# CTFエージェント用ベースイメージをビルド
python -m orchestrator.main --build-image
```

## 🎯 使用方法

### 基本的な使い方

```bash
# 仮想環境の有効化
source .venv/bin/activate

# 1. Dockerイメージをビルド（初回のみ）
python -m orchestrator.main --build-image

# 2. 特定の問題を解答（例：問題ID 222）
python -m orchestrator.main --challenge 222

# 3. 複数問題を解答
python -m orchestrator.main --challenge 100 101 102

# 4. 全ての未解決問題を解答
python -m orchestrator.main
```

### 実行例

**Docker並列実行:**
```
(.venv) ganon@host:~/CTF-Solver$ python -m orchestrator.main --challenge 222
2026-02-12 20:47:35,456 [INFO] __main__: 有効エージェント: ['copilot_cli', 'gemini_cli']
2026-02-12 20:47:35,456 [INFO] __main__: 解答対象の問題: [222]
2026-02-12 20:47:35,456 [INFO] __main__: ═══ 問題 222 の解答を開始 ═══
...
2026-02-12 11:53:16,838 [INFO] docker_manager: エージェント 2 体を並列実行: ['copilot_cli', 'gemini_cli']
2026-02-12 11:55:24,742 [INFO] docker_manager: フラグ候補収集: copilot_cli=CyberQuest{WannaCry}, gemini_cli=CyberQuest{Slammer}
2026-02-12 11:55:24,743 [INFO] flag_collector: 投票結果: CyberQuest{Slammer}（2/2 票）
2026-02-12 11:55:25,257 [INFO] __main__: 提出結果: correct – Solved!
```

### Docker Compose使用方法

**個別AI CLIエージェントの起動:**
```bash
# GitHub Copilot CLI エージェント
docker compose run --rm copilot

# CTF解析環境（全ツール搭載）
docker compose run --rm ctf-base

# CTF管理用オーケストレーター 
docker compose run --rm orchestrator

# Ollamaサーバー（バックグラウンド）
docker compose up -d ollama
```

**使用例:**
```bash
# Copilotエージェント内でCTF問題解答
docker compose run --rm copilot
> copilot -p "このバイナリを解析してフラグを見つけて" --allow-all-tools

# CTFベース環境でマニュアル解析
docker compose run --rm ctf-base
> python solve.py
> gdb ./binary

# オーケストレーター経由で自動実行
docker compose run --rm orchestrator
> python -m orchestrator.main --challenge 222 --host-mode
```

**認証設定:**
```bash
# ホスト環境で事前に認証（認証情報はコンテナに自動マウント）
copilot login

# コンテナ内で認証状況確認
docker compose run --rm copilot
> copilot --version  # 認証済みなら成功
```

### エージェントの有効化/無効化

`config/agents.yaml`でエージェントを選択：

```yaml
agents:
  claude_code:
    enabled: true     # 有効化
  codex_cli:
    enabled: false    # 無効化
  # ...他のエージェント
```

### 実行結果の確認

実行後、`challenges/<問題ID>/`に以下が生成されます：

```
challenges/123/
├── problem.txt              # 問題文
├── prompt.txt               # AI向けプロンプト  
├── Hints.txt                # 取得できたヒント
├── chall/                   # 配布ファイル
├── Flags/
│   ├── claude_code.txt      # 各エージェントのフラグ候補
│   ├── copilot_cli.txt
│   └── summary.json         # 投票結果サマリー
├── Logs/
│   ├── claude_code.log      # 各エージェントの実行ログ
│   └── copilot_cli.log
├── Solved-Flag.txt          # 正解フラグ（解決時のみ）
├── WrongFlags/              # 不正解フラグの記録
│   ├── flag_1.txt
│   └── summary.txt
└── SharedInfo/              # エージェント間共有情報
    ├── wrong_flags.txt      # 不正解フラグリスト
    └── approaches.txt       # 失敗したアプローチ
```

## 🔧 設定

### config/config.yaml

```yaml
# CTFd接続
ctfd:
  url: "${CTFD_URL}"
  token: "${CTFD_TOKEN}"

# ヒント設定
hints:
  allow_cost_hints: false     # コスト付きヒントの取得可否
  max_cost: 0                 # 許可する最大コスト

# ファイル設定  
files:
  auto_download: true         # 配布ファイル自動ダウンロード
  max_size: 100              # 最大ファイルサイズ（MB）

# フラグ評価
flag_evaluation:
  method: "voting"           # 多数決投票
  wait_time: 30              # フラグ収集待機時間（秒）
```

### config/agents.yaml

```yaml
agents:
  # 各エージェントの有効化設定
  claude_code:
    enabled: true
    type: "claude_code"
    description: "Claude Code CLI"

# 実行設定
execution:
  max_concurrent_challenges: 1    # 同時実行問題数
  agent_timeout: 600              # エージェントタイムアウト（秒）
  workspace_reset: true           # 再試行時のワークスペース初期化

# Docker設定
docker:
  network_mode: "host"            # ネットワークモード
  auto_remove: true               # コンテナ自動削除
  resources:
    memory: "4g"                  # メモリ制限
    cpu_count: 2                  # CPU数制限
```

## 🐛 トラブルシューティング

### よくある問題

#### 1. Docker権限エラー
```
Error while fetching server API version: PermissionError
```

**解決方法**:
```bash
sudo usermod -aG docker $USER
newgrp docker
# または再ログイン
```

#### 2. AI CLI認証エラー
```
Authentication failed for claude/codex/gh
```

**解決方法**: 各CLIツールで再認証
```bash
claude login
codex auth  
gh auth login
gemini auth login
```

#### 3. ヒント取得403エラー
```
403 Client Error: FORBIDDEN for url: .../hints
```

**解決方法**: 正常な動作です。ヒントなしとして処理が継続されます。

#### 4. Dockerイメージビルドエラー

**症状**: 
```
ERROR: failed to solve: failed to read dockerfile: open Dockerfile: no such file or directory
permission denied while trying to connect to the Docker daemon socket
```

**解決方法**: 段階的にビルド
```bash
# Docker権限問題を解決
sudo usermod -aG docker $USER
newgrp docker

# ベースイメージの手動ビルド（権限問題で自動ビルドが失敗する場合）
cd agents/base
sudo docker build -t ctf-agent-base:latest -f Dockerfile.base .

# または通常のビルド（権限解決後）
python -m orchestrator.main --build-image
```

#### 5. メモリ不足

**解決方法**: Dockerリソース制限を調整
```yaml
# agents.yaml
docker:
  resources:
    memory: "2g"     # 4g → 2gに削減
    cpu_count: 1     # CPU数も削減
```

### ログの確認

```bash
# 特定の問題の詳細ログ確認
cat challenges/123/Logs/claude_code.log

# 全体的な実行状況
python -m orchestrator.main --challenge 123 2>&1 | tee execution.log
```

## 📁 プロジェクト構成

```
CTF-Solver/
├── README.md                    # このファイル
├── requirements.txt             # Python依存関係
├── .env                         # 環境変数（git管理対象外）
├── .gitignore
├── config/
│   ├── config.yaml             # メイン設定
│   └── agents.yaml             # エージェント設定
├── orchestrator/               # Python制御コード
│   ├── main.py                 # メインエントリーポイント
│   ├── ctfd_client.py          # CTFd API通信
│   ├── challenge_manager.py    # ディレクトリ・状態管理
│   ├── hint_manager.py         # ヒント取得
│   ├── file_manager.py         # ファイル管理
│   ├── docker_manager.py       # Docker制御
│   ├── flag_collector.py       # フラグ評価・投票
│   └── prompt_generator.py     # プロンプト生成
├── agents/base/                # Docker関連
│   ├── Dockerfile.base         # Kali Linuxベースイメージ
│   ├── entrypoint.sh           # エージェント起動スクリプト
│   └── agent_runners/          # 各AIランナー
│       ├── base_runner.py      # 共通基底クラス
│       ├── claude_runner.py    # Claude Code対応
│       ├── codex_runner.py     # Codex CLI対応  
│       ├── copilot_runner.py   # GitHub Copilot対応
│       ├── gemini_runner.py    # Gemini CLI対応
│       └── gemini_ollama_runner.py # Ollama対応
└── challenges/                 # 実行時生成（問題ごと）
```

## 🤝 貢献

Issues、Pull Requestを歓迎します。新しいAIエージェントの追加や機能改善のご提案をお待ちしています。

## 📄 ライセンス

MIT License

---

**注意**: このツールは教育・研究目的で開発されています。CTF競技のルールを遵守し、適切な利用を心がけてください。