"""
ナレッジ管理モジュール

過去のCTF WriteupをカテゴリNo別に管理し、
問題解答時にエージェントが参照できるようにする。
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 対応カテゴリ一覧
CATEGORIES = ["crypto", "forensics", "misc", "osint", "pwn", "rev", "web"]

# プロジェクトルートからの knowledge ディレクトリパス
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


class KnowledgeManager:
    """過去のCTF Writeupナレッジを管理するクラス"""

    def __init__(self, knowledge_dir: Optional[Path] = None):
        self.base_dir = knowledge_dir or KNOWLEDGE_DIR
        self._ensure_dirs()

    def _ensure_dirs(self):
        """カテゴリディレクトリを作成する。"""
        for cat in CATEGORIES:
            (self.base_dir / cat).mkdir(parents=True, exist_ok=True)

    # ── 一覧表示 ──

    def list_knowledge(self) -> dict[str, list[str]]:
        """
        登録済みナレッジの一覧を返す。

        Returns:
            {カテゴリ: [ファイル名リスト]} の辞書
        """
        result = {}
        for cat in CATEGORIES:
            cat_dir = self.base_dir / cat
            if cat_dir.exists():
                files = sorted(
                    f.name for f in cat_dir.iterdir()
                    if f.is_file() and f.suffix in (".md", ".txt", ".py")
                )
                if files:
                    result[cat] = files
        return result

    # ── ファイル追加 ──

    def add_file(self, file_path: str, category: str) -> str:
        """
        個別ファイルをナレッジに追加する。

        Args:
            file_path: 追加するファイルパス
            category: カテゴリ名

        Returns:
            追加先パス
        """
        cat = category.lower()
        if cat not in CATEGORIES:
            raise ValueError(f"不明なカテゴリ: {cat}（対応: {CATEGORIES}）")

        src = Path(file_path)
        if not src.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {src}")

        dst = self.base_dir / cat / src.name
        shutil.copy2(src, dst)
        logger.info("ナレッジ追加: %s → %s", src, dst)
        return str(dst)

    # ── GitHubリポジトリからの一括追加 ──

    def add_from_github(self, repo_url: str) -> int:
        """
        GitHubリポジトリからWriteupを自動取り込む。

        リポジトリのディレクトリ構造からカテゴリを推定し、
        writeup.md / README.md / *.py (ソルバースクリプト) を取り込む。

        Args:
            repo_url: GitHubリポジトリURL

        Returns:
            追加されたファイル数
        """
        # リポジトリをクローン
        tmpdir = tempfile.mkdtemp(prefix="ctf_knowledge_")
        try:
            logger.info("リポジトリをクローン中: %s", repo_url)
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, tmpdir],
                check=True, capture_output=True, text=True,
            )
            return self._import_from_directory(Path(tmpdir))
        except subprocess.CalledProcessError as e:
            logger.error("git clone失敗: %s", e.stderr)
            raise
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _import_from_directory(self, repo_dir: Path) -> int:
        """
        クローン済みリポジトリからWriteupを取り込む。

        カテゴリ推定ルール:
        1. 親ディレクトリ名がカテゴリ名に一致 (crypto/, web/ 等)
        2. ファイル内容のキーワードからカテゴリを推定
        """
        count = 0

        for cat in CATEGORIES:
            cat_dir = repo_dir / cat
            if not cat_dir.is_dir():
                continue

            # カテゴリディレクトリ内の問題ディレクトリを走査
            for challenge_dir in sorted(cat_dir.iterdir()):
                if not challenge_dir.is_dir():
                    continue

                challenge_name = self._sanitize_name(challenge_dir.name)
                imported_parts = []

                # 問題README (問題説明) を取得
                readme = challenge_dir / "README.md"
                if readme.is_file():
                    imported_parts.append(
                        f"## 問題概要\n\n{readme.read_text(errors='replace').strip()}"
                    )

                # Writeupを取得 (writeup/README.md or writeup.md)
                writeup_content = self._find_writeup(challenge_dir)
                if writeup_content:
                    imported_parts.append(
                        f"## Writeup\n\n{writeup_content}"
                    )

                # ソルバースクリプトを取得
                scripts = self._find_solver_scripts(challenge_dir)
                for script_name, script_content in scripts:
                    lang = "python" if script_name.endswith(".py") else "c"
                    imported_parts.append(
                        f"## 解法スクリプト: {script_name}\n\n```{lang}\n{script_content}\n```"
                    )

                if imported_parts:
                    # 統合ファイルを作成
                    header = f"# {challenge_dir.name} [{cat}]\n\n"
                    content = header + "\n\n---\n\n".join(imported_parts)
                    dst = self.base_dir / cat / f"{challenge_name}.md"
                    dst.write_text(content, encoding="utf-8")
                    count += 1
                    logger.info("取り込み: %s/%s → %s", cat, challenge_dir.name, dst.name)

        logger.info("計 %d 件のWriteupを取り込みました", count)
        return count

    @staticmethod
    def _find_writeup(challenge_dir: Path) -> Optional[str]:
        """writeup/README.md または writeup.md を探して内容を返す。"""
        candidates = [
            challenge_dir / "writeup" / "README.md",
            challenge_dir / "writeup.md",
        ]
        for path in candidates:
            if path.is_file():
                return path.read_text(errors="replace").strip()
        return None

    @staticmethod
    def _find_solver_scripts(challenge_dir: Path) -> list[tuple[str, str]]:
        """解法スクリプト (solve.py, soln.py, solution.py 等) を探す。"""
        scripts = []
        patterns = re.compile(r"(solve|soln|solution|exploit|poc)", re.IGNORECASE)
        for root, _, files in os.walk(challenge_dir):
            for fname in files:
                if fname.endswith((".py", ".c")) and patterns.search(fname):
                    fpath = Path(root) / fname
                    try:
                        content = fpath.read_text(errors="replace").strip()
                        if content:
                            scripts.append((fname, content))
                    except Exception:
                        pass
        return scripts

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """ファイル名に安全な文字列に変換する。"""
        # スペースをアンダースコアに、特殊文字を除去
        name = name.replace(" ", "_").replace("/", "_")
        name = re.sub(r"[^\w\-.]", "", name)
        return name.lower()

    # ── ワークスペースへのコピー ──

    def copy_to_workspace(
        self, workspace_path: Path, category: Optional[str] = None
    ) -> bool:
        """
        ナレッジファイルをワークスペースの Reference/ にコピーする。

        Args:
            workspace_path: ワークスペースのルートパス
            category: 指定カテゴリのみコピー（Noneなら全カテゴリ）

        Returns:
            コピーされたファイルがあればTrue
        """
        ref_dir = workspace_path / "Reference"
        copied = False

        categories = [category.lower()] if category else CATEGORIES

        for cat in categories:
            src_dir = self.base_dir / cat
            if not src_dir.exists():
                continue

            files = [f for f in src_dir.iterdir() if f.is_file() and f.suffix in (".md", ".txt", ".py")]
            if not files:
                continue

            dst_dir = ref_dir / cat
            dst_dir.mkdir(parents=True, exist_ok=True)
            for f in files:
                shutil.copy2(f, dst_dir / f.name)
                copied = True

        if copied:
            logger.info("参考資料を %s にコピーしました", ref_dir)
        return copied

    # ── カテゴリ推定 ──

    @staticmethod
    def guess_category(problem_text: str, ctfd_category: Optional[str] = None) -> Optional[str]:
        """
        問題のカテゴリを推定する。

        CTFdのカテゴリ情報があればそれを優先し、
        なければ問題文からキーワードで推定する。

        Args:
            problem_text: 問題文
            ctfd_category: CTFdから取得したカテゴリ名

        Returns:
            推定カテゴリ名（推定できない場合はNone）
        """
        # CTFdカテゴリを優先
        if ctfd_category:
            cat = ctfd_category.lower().strip()
            if cat in CATEGORIES:
                return cat
            # 部分一致
            for c in CATEGORIES:
                if c in cat:
                    return c

        # 問題文からキーワード推定
        text = problem_text.lower()
        keyword_map = {
            "crypto": ["cipher", "encrypt", "decrypt", "rsa", "aes", "xor", "hash",
                       "暗号", "復号", "素数", "modular"],
            "forensics": ["forensic", "memory", "disk", "pcap", "wireshark",
                          "steganography", "stego", "metadata", "exif", "hex",
                          "フォレンジック", "ステガノ"],
            "web": ["sql", "xss", "ssti", "ssrf", "cookie", "jwt", "http",
                    "html", "javascript", "php", "flask", "django", "api",
                    "deserialization", "serialize"],
            "pwn": ["buffer overflow", "bof", "rop", "shellcode", "exploit",
                    "heap", "stack", "gadget", "libc", "pwntools", "nc "],
            "rev": ["reverse", "disassembly", "decompil", "ghidra", "ida",
                    "binary", "assembly", "obfuscat", "リバース"],
            "osint": ["osint", "geolocation", "social media", "whois", "dns",
                      "investigation", "公開情報"],
            "misc": ["misc", "その他", "sanity", "welcome"],
        }

        scores = {cat: 0 for cat in CATEGORIES}
        for cat, keywords in keyword_map.items():
            for kw in keywords:
                if kw in text:
                    scores[cat] += 1

        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else None
