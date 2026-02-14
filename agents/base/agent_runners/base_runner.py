"""
ベースランナー: 全AIエージェントランナーの共通機能を提供する。

各CLIツール固有のランナーはこのクラスを継承し、
execute() メソッドをオーバーライドする。

共通機能:
- プロンプト読み込み
- フラグ抽出（正規表現）
- 不正解フラグの確認
- CLIコマンド実行
- ログ出力
"""

import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


class BaseRunner:
    """全エージェントランナーの基底クラス"""

    def __init__(self, agent_name: str):
        """
        ベースランナーを初期化する。

        Args:
            agent_name: エージェント識別名（ログ表示用）
        """
        self.agent_name = agent_name
        self.logger = logging.getLogger(agent_name)

        # ワークスペース内のパス定義
        self.workspace = Path("/workspace")
        self.prompt_path = self.workspace / "prompt.txt"
        self.flag_path = self.workspace / "Flag.txt"
        self.work_dir = self.workspace / "try"
        self.chall_dir = self.workspace / "chall"
        self.shared_info_dir = self.workspace / "SharedInfo"

        # タイムアウト設定（環境変数から取得、デフォルト550秒）
        self.timeout = int(os.environ.get("AGENT_TIMEOUT", "550"))

    # ── ファイル読み込み ─────────────────────────────────────

    def load_prompt(self) -> str:
        """プロンプトファイルを読み込んで返す。"""
        if not self.prompt_path.exists():
            self.logger.error("prompt.txt が見つかりません")
            sys.exit(1)
        return self.prompt_path.read_text(encoding="utf-8")

    def load_wrong_flags(self) -> list[str]:
        """過去の不正解フラグ一覧を読み込んで返す。"""
        wf = self.shared_info_dir / "wrong_flags.txt"
        if wf.exists():
            return [line.strip() for line in wf.read_text().splitlines() if line.strip()]
        return []

    def load_approaches(self) -> str:
        """過去の失敗アプローチ記録を読み込んで返す。"""
        ap = self.shared_info_dir / "approaches.txt"
        if ap.exists():
            return ap.read_text(encoding="utf-8")
        return ""

    # ── フラグ操作 ───────────────────────────────────────────

    def save_flag(self, flag: str):
        """
        発見したフラグをFlag.txtに保存する。

        Args:
            flag: フラグ文字列
        """
        flag = flag.strip()
        if flag:
            self.flag_path.write_text(flag)
            self.logger.info("フラグ保存完了: %s", flag)

    def check_flag_exists(self) -> bool:
        """Flag.txtが既に存在し、内容があるか確認する。"""
        return self.flag_path.exists() and self.flag_path.read_text().strip() != ""

    def extract_flag_from_output(self, output: str) -> str | None:
        """
        テキスト出力からCTFフラグパターンを抽出する。

        一般的なフラグ形式（flag{...}, CTF{...}等）を検索し、
        過去の不正解フラグと一致するものは除外する。
        また、curlによるCTFd提出結果からフラグを復元する。

        Args:
            output: CLIツールの出力テキスト

        Returns:
            抽出されたフラグ文字列。見つからない場合はNone。
        """
        # まずcurl提出で正解になったフラグを探す
        # エージェントがcurlで直接提出し "correct" を得た場合、
        # 直前のsubmission値を抽出する
        curl_flag = self._extract_flag_from_curl_output(output)
        if curl_flag:
            return curl_flag

        # CTFで使われる一般的なフラグパターン
        patterns = [
            r'flag\{[^}]+\}',
            r'FLAG\{[^}]+\}',
            r'ctf\{[^}]+\}',
            r'CTF\{[^}]+\}',
            r'[A-Za-z0-9_]+\{[A-Za-z0-9_!@#$%^&*()\-+=,.?]+\}',
        ]

        wrong_flags = set(self.load_wrong_flags())
        # プレースホルダーパターンを除外
        placeholders = {
            "flag{...}", "FLAG{...}", "CTF{...}", "flag{FLAG}", "YOUR_FLAG_HERE",
            "flag{example_flag_123}",
        }

        for pattern in patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            for match in matches:
                if match in wrong_flags or match in placeholders:
                    continue
                # 3文字以上の中身があるフラグのみ
                inner = re.search(r'\{(.+)\}', match)
                if inner and len(inner.group(1)) >= 3 and inner.group(1) != "...":
                    return match

        return None

    # フラグパターンと成功キーワード（docker_managerと同じロジック）
    _FLAG_RE = re.compile(r'[A-Za-z0-9_]+\{[^}]{3,}\}')
    _PLACEHOLDERS = {
        "flag{example_flag_123}", "flag{...}", "FLAG{...}", "CTF{...}", "flag{FLAG}",
        "YOUR_FLAG_HERE", "DISCOVERED_FLAG",
    }
    _SUCCESS_KEYWORDS = (
        "correct", "accepted", "success", "submitted",
        "正解", "成功", "提出しました",
        "CTFd応答: correct", "already_solved",
    )

    def _detect_flag_in_line(self, line: str) -> str | None:
        """1行からフラグ+成功シグナルを検出する。"""
        if "incorrect" in line.lower():
            return None
        flags = self._FLAG_RE.findall(line)
        candidates = [f for f in flags if f not in self._PLACEHOLDERS]
        if not candidates:
            return None
        line_lower = line.lower()
        if any(kw in line_lower for kw in self._SUCCESS_KEYWORDS):
            return candidates[-1]
        return None

    def _extract_flag_from_curl_output(self, output: str) -> str | None:
        """curl提出結果から正解フラグを抽出する。"""
        lines = output.splitlines()
        last_submission = None
        prompt_section = True

        for line in lines:
            if "コマンド実行:" in line or "=== " in line and "実行開始" in line:
                prompt_section = False
            if prompt_section:
                continue

            # JSON / エスケープ付きsubmission追跡
            m = re.search(r'"submission"\s*:\s*"([^"]+)"', line)
            if m and m.group(1) not in self._PLACEHOLDERS:
                last_submission = m.group(1)
            m2 = re.search(r'\\?"submission\\?"\s*:\\?\s*\\?"([^"\\]+)\\?"', line)
            if m2 and m2.group(1) not in self._PLACEHOLDERS:
                last_submission = m2.group(1)

            # APIレスポンス "correct"
            if '"status"' in line and '"correct"' in line and '"incorrect"' not in line:
                if last_submission:
                    return last_submission

            # 汎用: フラグ+成功キーワード同一行
            detected = self._detect_flag_in_line(line)
            if detected:
                return detected

        return None

    # ── CLIコマンド実行 ──────────────────────────────────────

    def run_cli(
        self, cmd: list[str], env: dict | None = None, timeout: int | None = None
    ) -> tuple[str, str, int]:
        """
        CLIコマンドをサブプロセスとして実行し、出力をリアルタイムでストリーミングする。

        stdout/stderrは両方とも sys.stdout に即座に出力されるため、
        Dockerコンテナのログにリアルタイムで表示される。
        同時に出力を内部バッファに蓄積して返す。

        Args:
            cmd: 実行するコマンドとその引数のリスト
            env: 追加の環境変数（既存環境変数にマージ）
            timeout: タイムアウト秒数（デフォルトはself.timeout）

        Returns:
            (stdout, stderr, return_code) のタプル
        """
        import threading

        # 環境変数を構築
        full_env = {**os.environ}
        if env:
            full_env.update(env)

        effective_timeout = timeout if timeout is not None else self.timeout
        self.logger.info("コマンド実行: %s", " ".join(cmd[:6]))

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(self.work_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=full_env,
                bufsize=1,
            )

            stdout_lines = []
            stderr_lines = []

            def _stream_reader(pipe, buf, label):
                """パイプから行を読みリアルタイム出力しつつバッファに蓄積する。"""
                try:
                    for line in iter(pipe.readline, ""):
                        sys.stdout.write(line)
                        sys.stdout.flush()
                        buf.append(line)
                except Exception:
                    pass
                finally:
                    pipe.close()

            t_out = threading.Thread(target=_stream_reader, args=(proc.stdout, stdout_lines, "stdout"), daemon=True)
            t_err = threading.Thread(target=_stream_reader, args=(proc.stderr, stderr_lines, "stderr"), daemon=True)
            t_out.start()
            t_err.start()

            try:
                proc.wait(timeout=effective_timeout)
            except subprocess.TimeoutExpired:
                self.logger.warning("コマンドタイムアウト（%d秒）", effective_timeout)
                proc.kill()
                proc.wait()
                t_out.join(timeout=5)
                t_err.join(timeout=5)
                return "".join(stdout_lines), "TIMEOUT\n" + "".join(stderr_lines), -1

            t_out.join(timeout=10)
            t_err.join(timeout=10)
            return "".join(stdout_lines), "".join(stderr_lines), proc.returncode

        except FileNotFoundError:
            self.logger.error("コマンドが見つかりません: %s", cmd[0])
            return "", f"Command not found: {cmd[0]}", -1

    # ── メイン実行 ───────────────────────────────────────────

    def execute(self):
        """
        エージェント固有の実行ロジック。

        サブクラスでオーバーライドして、
        具体的なCLIツールの呼び出しを実装する。
        """
        raise NotImplementedError("サブクラスでexecute()を実装してください")

    def run(self):
        """
        ランナーのメインエントリーポイント。

        1. ワーキングディレクトリを準備
        2. execute()を呼び出し（サブクラスの実装）
        3. 結果を確認・ログ出力
        """
        self.logger.info("=== エージェント %s 開始 ===", self.agent_name)
        self.logger.info("ワークスペース: %s", self.workspace)

        # 作業ディレクトリを作成
        self.work_dir.mkdir(parents=True, exist_ok=True)

        try:
            self.execute()
        except Exception as e:
            self.logger.exception("エージェント実行エラー: %s", e)

        # 結果を確認
        if self.check_flag_exists():
            flag = self.flag_path.read_text().strip()
            self.logger.info("=== フラグ発見: %s ===", flag)
        else:
            self.logger.info("=== フラグ未発見 ===")
