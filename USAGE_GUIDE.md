# CTF問題の解決とWriteup作成ガイド

このガイドでは、CTF Solverを使用してCTF問題を解決し、writeupを作成する方法を説明します。

## 前提条件

- Docker がインストールされている
- Python 3.8以上がインストールされている
- CTFdプラットフォームへのアクセス権とAPIトークン

## セットアップ手順

### 1. 依存関係のインストール

```bash
# Pythonパッケージをインストール
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env`ファイルを作成し、CTFdの接続情報を設定します：

```bash
# .envファイルの作成
cp .env.example .env

# .envファイルを編集
nano .env
```

必須項目：
```
CTFD_URL=https://your-ctfd-platform.com/
CTFD_TOKEN=ctfd_your_token_here
```

### 3. エージェントの設定

`config/agents.yaml`を編集して、使用するAIエージェントを有効化します：

```yaml
agents:
  copilot_cli:
    enabled: true    # 有効化
    type: "copilot_cli"
    auth_profiles:
      - name: main
        models:
          - model: "claude-sonnet-4.5"
            instances: 2  # 2つのインスタンスを起動
```

## 使用方法

### 問題の一覧表示

```bash
python -m orchestrator.main --list
```

出力例：
```
  [ ] ID:  10 |  100pts | Crypto       | Easy RSA
  [V] ID:  20 |  150pts | Web          | SQL Injection 101
  [ ] ID:  30 |  200pts | Pwn          | Buffer Overflow
```

- `[V]`: 解決済み
- `[ ]`: 未解決

### すべての問題を自動解決

```bash
python -m orchestrator.main
```

このコマンドで以下が実行されます：
1. 有効化されたすべてのエージェントを起動
2. 各エージェントが自律的に問題を選択・解決
3. フラグを自動提出
4. Writeupを自動生成

### 特定の問題のみ解決

```bash
# Challenge ID 10のみ解決
python -m orchestrator.main --challenge 10

# 複数の問題を解決
python -m orchestrator.main --challenge 10,20,30
```

### 特定の問題をスキップ

```bash
# Challenge ID 5,6,7をスキップ
python -m orchestrator.main --skip 5,6,7
```

### 特定のエージェントのみ使用

```bash
# copilot_cliエージェントのみ使用
python -m orchestrator.main --agent copilot_cli

# 複数のエージェント
python -m orchestrator.main --agent copilot_cli,codex_cli
```

### WebUIの使用

デフォルトではWebUIが自動起動します（ポート8080）：

```bash
# デフォルト（WebUI有効）
python -m orchestrator.main

# WebUIを無効化
python -m orchestrator.main --no-webui

# カスタムポート
python -m orchestrator.main --webui-port 9090
```

WebUIにアクセス：
```
http://localhost:8080
```

## Writeupの生成

### 自動生成

エージェントが問題を解決すると、自動的に以下が生成されます：
- `challenges/<id>/WriteUp/writeup.md` - 各問題のwriteup

### マスターWriteupの作成

すべての解決済み問題のwriteupを1つのファイルにまとめる：

```bash
# デフォルト出力: writeups/master_writeup.md
python create_writeup.py

# カスタム出力パス
python create_writeup.py --output my_writeups.md

# 個別ファイルも生成
python create_writeup.py --individual
```

## ディレクトリ構造

```
challenges/<challenge_id>/
├── problem.txt           # 問題文
├── hints.txt            # ヒント（存在する場合）
├── chall/               # 配布ファイル
├── try/                 # エージェントの作業ディレクトリ
├── Flags/               # フラグ候補
│   └── summary.json
├── Solved-Flag.txt      # 正解フラグ
├── WrongFlags/          # 不正解フラグ
│   └── summary.txt
├── WriteUp/
│   └── writeup.md       # 自動生成されたwriteup
├── Logs/                # エージェントログ
│   ├── agent1.log
│   └── agent2.log
└── .solved              # 解決済みマーカー
```

## ログの確認

### リアルタイムログ

```bash
# オーケストレーターログ
tail -f logs/orchestrator.log

# 特定エージェントのログ
tail -f logs/copilot_cli_1.log
```

### アーカイブログ

古いログは自動的にアーカイブされます：
```
logs/
├── archive_20260312_074326/   # 古いログ
│   ├── orchestrator.log
│   └── ...
└── orchestrator.log            # 現在のログ
```

## トラブルシューティング

### Dockerイメージのビルド

初回実行時またはDockerfileを更新した場合：

```bash
python -m orchestrator.main --build-image
```

### ワークスペースのパーミッション問題

```bash
python3 tools/fix_workspace_permissions.py
```

### CTFdへの接続エラー

1. `.env`ファイルのCTFD_URLとCTFD_TOKENを確認
2. CTFdプラットフォームが稼働中か確認
3. ネットワーク接続を確認

```bash
# 接続テスト
curl -H "Authorization: Token YOUR_TOKEN" https://your-ctfd.com/api/v1/challenges
```

### エージェントが起動しない

1. Dockerが実行中か確認：`docker ps`
2. 認証プロファイルが正しく設定されているか確認
3. エージェントログを確認：`tail -f logs/orchestrator.log`

## 高度な使用方法

### 複数エージェントによる協力

問題数がエージェント数より少ない場合、複数エージェントが同じ問題に協力します：

```
残り問題: 2問
稼働エージェント: 5エージェント

→ Challenge #101: 3エージェントで協力
→ Challenge #205: 2エージェントで協力
```

### カスタムプロンプトの使用

`orchestrator/prompt_generator.py`を編集してプロンプトをカスタマイズできます。

### ヒント取得の制御

`config/config.yaml`でヒント取得を制御：

```yaml
hints:
  enabled: true              # ヒント取得を有効化
  allow_cost_hints: false    # 有料ヒントを禁止
  max_cost: 0                # 最大コスト（0=無料のみ）
```

## ベストプラクティス

1. **段階的実行**: 最初は`--list`で問題を確認
2. **ログ監視**: `tail -f logs/orchestrator.log`でリアルタイム監視
3. **定期的なバックアップ**: `challenges/`ディレクトリをバックアップ
4. **エージェント数の調整**: システムリソースに応じてインスタンス数を調整
5. **Writeupの確認**: 自動生成後、内容を確認・補完

## まとめ

このシステムを使用することで：
- ✅ 複数AIエージェントによる並列解答
- ✅ 自動フラグ提出
- ✅ Writeupの自動生成
- ✅ WebUIによるリアルタイム監視
- ✅ 完全な自律動作

問題が発生した場合は、ログを確認するか、GitHubのIssueで報告してください。
