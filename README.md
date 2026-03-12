# CTF Solver

複数AIエージェントを並列実行してCTF問題を自動解答するシステム。
各エージェントはDockerコンテナ内で自律的に問題を選択・解析・フラグ提出を行う。

## セットアップ

```bash
# 依存関係
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# .env に CTFd 接続情報を設定
CTFD_URL=https://your-ctfd.com
CTFD_TOKEN=your_token

# Docker イメージビルド（初回のみ）
python -m orchestrator.main --build-image
```

### 🔒 セキュリティ設定

Dockerコンテナは**非rootユーザー**で実行されます（セキュリティ強化）。

`config/agents.yaml`:
```yaml
docker:
  user: "1000:1000"  # 非rootユーザー（デフォルト: 現在のユーザーUID/GID）
```

過去にrootユーザーで実行していた場合、workspaceディレクトリのパーミッションを修正：
```bash
# 権限修正スクリプト（rootが必要な場合のみ）
python3 tools/fix_workspace_permissions.py
```

## 主要コマンド

```bash
# 全未解決問題を解答（全有効エージェント並列）
python -m orchestrator.main

# 特定の問題だけ
python -m orchestrator.main --challenge 222

# 特定のエージェントだけ
python -m orchestrator.main --agent copilot_cli

# 問題をスキップ
python -m orchestrator.main --skip 100,101

# 問題一覧
python -m orchestrator.main --list

# WebUI無効
python -m orchestrator.main --no-webui

# WebUIポート変更（デフォルト: 8080）
python -m orchestrator.main --webui-port 9090
```

## ログ管理

システムは起動時に自動的に古いログをアーカイブします：

- **自動アーカイブ**: 実行開始時に既存の `.log` ファイルを `logs/archive_YYYYMMDD_HHMMSS/` に移動
- **自動クリーンアップ**: 古いアーカイブを自動削除（デフォルト: 最新10個を保持）
- **設定**: `config/config.yaml` で制御可能

```yaml
logs:
  archive_on_start: true    # 起動時アーカイブを有効化
  keep_archives: 10         # 保持するアーカイブ数
```

アーカイブ例:
```
logs/
├── archive_20260312_074326/   # 古いログ（自動作成）
│   ├── claude_code.log
│   ├── orchestrator.log
│   └── ...
├── archive_20260312_083045/   # より新しいログ
└── orchestrator.log            # 現在のログ
```

## 認証管理

```bash
# 対話式プロファイル管理
python tools/auth_manager.py
```

各CLIの認証をプロファイルとして `~/.ctf-solver/profiles/` に保存。
`agents.yaml` の `auth_profiles` で名前参照される。

## マルチエージェント協力機能

**残り問題数 < エージェント数**の場合、複数エージェントが同じ問題に協力して取り組めます。

### 動作例
```
残り問題: 2問
稼働エージェント: 5エージェント

→ Challenge #101: 3エージェントで協力
→ Challenge #205: 2エージェントで協力
```

### 仕組み
- エージェントは自律的に未解決問題を選択
- 同じ問題に複数エージェントが`claim`可能（排他制御なし）
- WebUIで「🔧 agent1, agent2, agent3 (3)」のように表示
- 誰かが正解を提出したら全員のclaimが自動解除

## エージェント設定 (`config/agents.yaml`)

```yaml
agents:
  copilot_cli:
    enabled: true
    model: "gpt-4.1"              # デフォルトモデル
    type: "copilot_cli"
    auth_profiles:
      # パターン1: 1アカウント・複数モデル
      - name: main
        models:
          - model: "claude-sonnet-4.5"
            instances: 2           # このモデルで2コンテナ
          - model: "gpt-5.1-codex"
            instances: 1
      # パターン2: 1アカウント・1モデル（省略形）
      - name: sub_account
        model: "gpt-4.1"
        instances: 1
      # パターン3: モデル指定なし（デフォルト使用）
      - name: another
        instances: 1

  codex_cli:
    enabled: true
    type: "codex_cli"
    auth_profiles:
      - name: account1
        instances: 1
      - name: account2
        instances: 0              # 0 = 無効

  claude_zai:
    enabled: true
    model: "glm-4.7-flash"
    type: "claude_zai"
    auth_profiles:
      - name: user1
        weight: 1
        env_vars:                 # プロファイル固有の環境変数
          ZAI_API_KEY: "xxx"

docker:
  network_mode: "host"
  resources:
    memory: "4g"
    cpu_count: 2
```

## ログ確認

コンソールにはフラグ提出・エラー等の重要イベントのみ表示。
全ログはファイルに記録される。

```bash
# エージェント別ログ
tail -f logs/copilot_cli_1.log

# オーケストレーターログ
tail -f logs/orchestrator.log
```

## ディレクトリ構成

```
config/agents.yaml          # エージェント設定
config/config.yaml          # CTFd接続・ヒント等
orchestrator/               # オーケストレーター
agents/base/                # Dockerfile・エントリーポイント・ランナー
tools/auth_manager.py       # 認証プロファイル管理
webui/                      # WebUI ダッシュボード
workspace/                  # エージェント作業ディレクトリ（実行時生成）
logs/                       # ログ出力先
```