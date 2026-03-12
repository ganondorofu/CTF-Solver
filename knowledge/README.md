# CTF Writeupナレッジベース

過去のCTF Writeupをカテゴリ別に格納し、問題解答時にエージェントが参照できるようにするディレクトリです。

## 構成

```
knowledge/
├── crypto/       # 暗号系
├── forensics/    # フォレンジック
├── misc/         # その他
├── osint/        # OSINT
├── pwn/          # Exploit
├── rev/          # リバースエンジニアリング
└── web/          # Web
```

## 使い方

### GitHubリポから一括追加
```bash
python -m orchestrator.main --add-knowledge https://github.com/E-HAX/EHAX-CTF-2025
```

### 個別ファイル追加
```bash
python -m orchestrator.main --add-knowledge ./writeup.md --category web
```

### 一覧表示
```bash
python -m orchestrator.main --list-knowledge
```

実行時にカテゴリが一致する参考資料が `/workspace/Reference/` にマウントされます。
