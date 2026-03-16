# CTF Challenge Setup and Writeup

このドキュメントは、指定されたCTFdプラットフォームでCTF問題を解決し、writeupを作成するための手順を説明します。

## 設定情報

- **CTFd URL**: https://cq-revengers.singularitybattlequest.club/
- **トークン**: ctfd_81b66c28072637c947ac573b78a099e5ae7e96db817bbd602e64edc2bf768ef5

## セットアップ済みの内容

### 1. 環境設定ファイル (.env)

CTFdへの接続情報が設定されています：

```bash
CTFD_URL=https://cq-revengers.singularitybattlequest.club/
CTFD_TOKEN=ctfd_81b66c28072637c947ac573b78a099e5ae7e96db817bbd602e64edc2bf768ef5
```

### 2. バグ修正

`orchestrator/main.py`の`signal`モジュールのインポート競合を修正しました。

### 3. Writeup生成スクリプト

`create_writeup.py`スクリプトを作成し、解決済み問題のwriteupを自動生成できるようにしました。

## 使用方法

### 問題一覧の取得

```bash
python -m orchestrator.main --list
```

### 全問題の自動解決

```bash
python -m orchestrator.main
```

### Writeupの生成

```bash
# すべての解決済み問題のwriteupをまとめて生成
python create_writeup.py

# 個別ファイルとしても生成
python create_writeup.py --individual
```

## 現在の状態

⚠️ **注意**: 指定されたCTFdドメイン（cq-revengers.singularitybattlequest.club）は現在DNSで解決できません。

これは以下の理由が考えられます：
1. CTFイベントが終了し、サーバーが停止した
2. ドメインが変更された
3. 一時的なネットワーク問題

### 代替案

CTFが有効な場合は、以下の手順でシステムを使用できます：

1. **正しいURLの確認**: CTF主催者から正しいURLを取得
2. **`.env`の更新**: 正しいURLとトークンを設定
3. **システムの実行**: 上記のコマンドで問題を解決

## 詳細なドキュメント

詳しい使用方法は`USAGE_GUIDE.md`を参照してください。

## システムの機能

このCTF Solverシステムは以下の機能を提供します：

- ✅ **マルチエージェント並列実行**: 複数のAIエージェントが同時に問題を解決
- ✅ **自動フラグ提出**: 見つかったフラグを自動的にCTFdに提出
- ✅ **Writeup自動生成**: 各問題の解法を日本語でドキュメント化
- ✅ **WebUIダッシュボード**: リアルタイムで進捗を監視
- ✅ **失敗フラグの共有**: エージェント間で不正解フラグを共有して重複を防止
- ✅ **エージェント協力**: 残り問題が少ない場合、複数エージェントが協力

## トラブルシューティング

### DNS解決エラー

```
socket.gaierror: [Errno -5] No address associated with hostname
```

このエラーは、CTFdドメインが解決できない場合に発生します。

**解決方法**:
1. CTF主催者に最新のURL/トークンを確認
2. `.env`ファイルを更新
3. 再度実行

### Docker関連の問題

```bash
# Dockerイメージの再ビルド
python -m orchestrator.main --build-image

# ワークスペースのパーミッション修正
python3 tools/fix_workspace_permissions.py
```

## まとめ

- ✅ システムのセットアップ完了
- ✅ バグ修正完了
- ✅ Writeup生成スクリプト作成
- ⚠️ CTFdサーバーへの接続が必要（現在は未接続）

CTFが有効になれば、このシステムを使用して自動的に問題を解決し、writeupを生成できます。
