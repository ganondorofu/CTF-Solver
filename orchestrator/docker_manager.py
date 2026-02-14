"""
Docker管理モジュール

各AIエージェント用のDockerコンテナを起動・監視・停止する。
ワークスペースの準備とコンテナ内へのマウントも担当する。
"""

import logging
import os
import re
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

import docker
from docker.errors import ContainerError, ImageNotFound, APIError

logger = logging.getLogger(__name__)

# エージェント出力ストリーミング用ロガー（system.logに流さない）
agent_stream_logger = logging.getLogger("agent_stream")
agent_stream_logger.propagate = False  # ルートロガーに伝播しない
if not agent_stream_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    agent_stream_logger.addHandler(_handler)
    agent_stream_logger.setLevel(logging.INFO)

# WriteUp作成の最大猶予時間（秒）— コンテナ終了 or ファイル出現で早期終了
WRITEUP_GRACE_PERIOD = 300


class DockerManager:
    """Dockerコンテナのライフサイクルを管理するクラス"""

    # エージェントタイプ別認証ディレクトリマッピング
    AUTH_MOUNTS = {
        "copilot_cli": [
            "~/.config/github-copilot",
            "~/.config/gh",
            "~/.copilot",
        ],
        "gemini_cli": [
            "~/.gemini",
            "~/.config/gemini-cli",
        ],
        "codex_cli": [
            "~/.codex",
        ],
    }

    def __init__(self, agents_config: dict, docker_config: dict):
        """
        Dockerマネージャーを初期化する。

        Args:
            agents_config: agents.yamlのagentsセクション
            docker_config: agents.yamlのdockerセクション
        """
        self.agents_config = agents_config
        self.docker_config = docker_config
        
        try:
            self.client = docker.from_env()
            # Docker接続テスト
            self.client.ping()
        except docker.errors.DockerException as e:
            if "permission denied" in str(e).lower():
                raise RuntimeError(
                    "Docker権限エラー: ユーザーがdockerグループに所属していないか、"
                    "Docker Desktop WSL統合が無効です。\n"
                    "解決方法:\n"
                    "1. sudo usermod -aG docker $USER && newgrp docker\n"
                    "2. Docker Desktop → Settings → Resources → WSL Integration → 有効化"
                ) from e
            else:
                raise RuntimeError(f"Docker接続エラー: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Docker初期化失敗: {e}") from e

        # キャンセルされたエージェントのログを保持する辞書
        self._cancelled_logs: dict[str, str] = {}

    # ── Dockerイメージのビルド ────────────────────────────────

    def build_base_image(
        self, dockerfile_dir: str = "agents/base"
    ):
        """
        共有ベースイメージをビルドする。

        全エージェントが使用する共通のDockerイメージを
        Dockerfile.baseから構築する。

        Args:
            dockerfile_dir: Dockerfileが格納されたディレクトリ
        """
        path = Path(dockerfile_dir)
        logger.info("ベースイメージをビルド中: %s", path)
        self.client.images.build(
            path=str(path),
            dockerfile="Dockerfile.base",
            tag="ctf-agent-base:latest",
            rm=True,
        )
        logger.info("ベースイメージのビルド完了")

    # ── ワークスペースの準備 ──────────────────────────────────

    def prepare_workspace(
        self,
        challenge_dir: Path,
        hints_exist: bool,
    ) -> Path:
        """
        Docker内にマウントするワークスペースディレクトリを準備する。

        ホスト側に一時ディレクトリを作成し、以下をコピー:
        - problem.txt: 問題文
        - prompt.txt: 生成済みプロンプト
        - Hints.txt: ヒント（存在する場合のみ）
        - chall/: 配布ファイル（読み取り専用コピー）
        - SharedInfo/: エージェント間共有情報
        - try/: 作業ディレクトリ（空）

        Args:
            challenge_dir: ホスト側の問題ディレクトリ
            hints_exist: ヒントファイルが存在するかどうか

        Returns:
            準備されたワークスペースのパス
        """
        ws = Path(tempfile.mkdtemp(prefix="ctf_ws_"))

        # 問題文とプロンプトをコピー
        for fname in ("problem.txt", "prompt.txt"):
            src = challenge_dir / fname
            if src.exists():
                shutil.copy2(src, ws / fname)

        # ヒントファイルをコピー（存在する場合のみ）
        if hints_exist:
            src = challenge_dir / "Hints.txt"
            if src.exists():
                shutil.copy2(src, ws / "Hints.txt")

        # 配布ファイルディレクトリをコピー
        src_chall = challenge_dir / "chall"
        if src_chall.exists():
            shutil.copytree(src_chall, ws / "chall")
        else:
            (ws / "chall").mkdir()

        # 共有情報ディレクトリをコピー
        src_si = challenge_dir / "SharedInfo"
        if src_si.exists():
            shutil.copytree(src_si, ws / "SharedInfo")
        else:
            (ws / "SharedInfo").mkdir()

        # 作業ディレクトリを作成
        (ws / "try").mkdir(exist_ok=True)

        # submit_flag.sh をワークスペースにコピー（Dockerイメージ内にもある）
        submit_src = Path(__file__).parent.parent / "agents" / "base" / "submit_flag.sh"
        if submit_src.exists():
            shutil.copy2(submit_src, ws / "submit_flag.sh")
            (ws / "submit_flag.sh").chmod(0o755)

        return ws

    # ── エージェント用環境変数の解決 ─────────────────────────

    def _resolve_env_vars(self, agent_cfg: dict) -> dict:
        """
        エージェント設定からDocker環境変数を解決する。

        ${VAR_NAME} 形式の値をホストの環境変数で置換する。

        Args:
            agent_cfg: エージェントの設定辞書

        Returns:
            解決済みの環境変数辞書
        """
        env = {}
        env_vars = agent_cfg.get("env_vars", {})
        for key, value in env_vars.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # ${VAR} → ホスト環境変数から取得
                host_var = value[2:-1]
                env[key] = os.environ.get(host_var, "")
            else:
                env[key] = str(value)
        return env

    # ── コンテナの実行 ───────────────────────────────────────

    def run_agent(
        self,
        agent_name: str,
        agent_cfg: dict,
        workspace_path: Path,
        timeout: int = 600,
        cancel_event: Optional[threading.Event] = None,
        ctfd_url: str = "",
        ctfd_token: str = "",
        challenge_id: int = 0,
        log_file_path: Optional[Path] = None,
    ) -> tuple[Optional[str], str, Optional[str]]:
        """
        エージェント用のDockerコンテナを起動し、フラグを取得する。

        コンテナ内でentrypoint.shが実行され、
        AGENT_TYPEに応じた適切なランナースクリプトが起動される。

        Args:
            agent_name: エージェントの識別名
            agent_cfg: エージェントの設定辞書
            workspace_path: マウントするワークスペースパス
            timeout: タイムアウト秒数
            cancel_event: 他エージェント正解時のキャンセルシグナル
            ctfd_url: CTFd URL（submit_flag.sh用）
            ctfd_token: CTFd認証トークン（submit_flag.sh用）
            challenge_id: 問題ID（submit_flag.sh用）
            log_file_path: リアルタイムログ出力先ファイルパス（Noneの場合はファイル書き込みなし）

        Returns:
            (フラグ文字列 or None, ログ文字列, writeupテキスト or None) のタプル
        """
        # 環境変数を構築
        env = self._resolve_env_vars(agent_cfg)
        env["AGENT_NAME"] = agent_name
        env["AGENT_TYPE"] = agent_cfg.get("type", agent_name)
        env["AGENT_TIMEOUT"] = str(timeout - 50)  # 余裕を持たせる
        # submit_flag.sh 用
        env["CTFD_URL"] = ctfd_url
        env["CTFD_TOKEN"] = ctfd_token
        env["CHALLENGE_ID"] = str(challenge_id)

        # Ollamaモデル名（Ollama使用時のみ）
        if "ollama_model" in agent_cfg:
            env["OLLAMA_MODEL"] = agent_cfg["ollama_model"]

        # Dockerリソース設定
        resources = self.docker_config.get("resources", {})
        mem_limit = resources.get("memory", "4g")
        cpu_count = resources.get("cpu_count", 2)

        try:
            # 認証ディレクトリマウントを構築
            volumes = {
                str(workspace_path): {"bind": "/workspace", "mode": "rw"},
            }
            
            # エージェントタイプに応じた認証マウントを追加
            auth_dirs = self._get_auth_mounts(agent_cfg.get("type", agent_name))
            volumes.update(auth_dirs)

            # コンテナを起動
            container = self.client.containers.run(
                image="ctf-agent-base:latest",
                command="/bin/bash /entrypoint.sh",
                environment=env,
                volumes=volumes,
                network_mode=self.docker_config.get("network_mode", "host"),
                mem_limit=mem_limit,
                cpu_count=cpu_count,
                detach=True,
                auto_remove=False,
            )

            logger.info(
                "コンテナ起動: %s（エージェント: %s）",
                container.short_id,
                agent_name,
            )
            
            # エージェント起動の詳細ログ
            logger.info(
                "エージェント %s: イメージ=%s, 環境変数=%s, ボリューム数=%d",
                agent_name, 
                "ctf-agent-base:latest",
                list(env.keys()),
                len(volumes),
            )

            # Flag.txtの出現またはコンテナ終了を待機
            flag = self._wait_for_flag(
                container, workspace_path, timeout, agent_name, cancel_event,
                log_file_path=log_file_path,
            )

            # キャンセルされた場合（他エージェントが正解済み）
            if cancel_event and cancel_event.is_set() and not flag:
                logger.info("[%s] 他エージェントが正解済み → 中断", agent_name)
                logs = self._cancelled_logs.pop(agent_name, "")
                if not logs:
                    try:
                        logs = container.logs().decode("utf-8", errors="replace")
                    except Exception:
                        logs = ""
                    self._cleanup_container(container)
                return None, logs, None

            # コンテナログを取得（クリーンアップ前に）
            try:
                logs = container.logs().decode("utf-8", errors="replace")
            except Exception as e:
                logger.warning("[%s] コンテナログ取得失敗: %s", agent_name, e)
                logs = ""

            # Flag.txtにフラグが無い場合 OR 信頼性の低いフラグの場合、
            # ログからcurl成功の提出を抽出して上書き
            writeup_path = workspace_path / "WriteUp" / "writeup.md"
            curl_flag = self._extract_flag_from_logs(logs, agent_name) if logs else None
            if curl_flag:
                if not flag or flag != curl_flag:
                    logger.info(
                        "[%s] ログから確認済み正解フラグで上書き: %s → %s",
                        agent_name, flag, curl_flag
                    )
                flag = curl_flag

            # WriteUpからフラグ抽出（最終フォールバック）
            if not flag:
                writeup_flag = self._extract_flag_from_writeup(writeup_path, agent_name)
                if writeup_flag:
                    flag = writeup_flag

            # 正解確定 → 他エージェントにキャンセル通知
            if flag and cancel_event and not cancel_event.is_set():
                logger.info("[%s] 正解フラグ確定 → 他エージェントにキャンセル通知", agent_name)
                cancel_event.set()

            # WriteUpを回収（存在する場合、書き込み完了を確認）
            writeup = None
            if writeup_path.exists() and writeup_path.stat().st_size > 0:
                # 書き込み途中でないことを確認
                size1 = writeup_path.stat().st_size
                time.sleep(2)
                size2 = writeup_path.stat().st_size if writeup_path.exists() else 0
                if size2 > 0 and size1 != size2:
                    # まだ書き込み中 → 追加で待機
                    logger.debug("[%s] WriteUp書き込み中（%d → %d bytes）、追加待機", agent_name, size1, size2)
                    time.sleep(5)
                writeup = writeup_path.read_text(encoding="utf-8", errors="replace")
                logger.info("[%s] WriteUp回収完了（%d文字）", agent_name, len(writeup))

            # コンテナを停止・削除
            self._cleanup_container(container)

            return flag, logs, writeup

        except (ContainerError, ImageNotFound, APIError) as e:
            logger.error("Dockerエラー（エージェント %s）: %s", agent_name, e)
            return None, str(e), None

    def _get_auth_mounts(self, agent_type: str) -> dict:
        """
        エージェントタイプに応じた認証ディレクトリマウントを構築する。

        Args:
            agent_type: エージェントのタイプ (copilot_cli, gemini_cli等)

        Returns:
            Dockerボリュームマウント用の辞書
        """
        mounts = {}
        auth_dirs = self.AUTH_MOUNTS.get(agent_type, [])
        
        logger.info("エージェント %s: 認証ディレクトリ候補 %s", agent_type, auth_dirs)
        
        for auth_dir in auth_dirs:
            host_path = Path(auth_dir).expanduser()
            if host_path.exists():
                container_path = auth_dir.replace("~", "/root")
                mounts[str(host_path)] = {
                    "bind": container_path, 
                    "mode": "rw"  # 読み書き可能（CLIツールが一時ファイル作成のため）
                }
                logger.info(
                    "認証マウント追加: %s → %s (rw)", 
                    host_path, 
                    container_path
                )
            else:
                logger.warning(
                    "認証ディレクトリ未存在（スキップ）: %s", 
                    host_path
                )
        
        if not mounts:
            logger.warning("エージェント %s: 認証マウント未設定", agent_type)
        
        return mounts

    def _wait_for_flag(
        self,
        container,
        workspace_path: Path,
        timeout: int,
        agent_name: str = "unknown",
        cancel_event: Optional[threading.Event] = None,
        log_file_path: Optional[Path] = None,
    ) -> Optional[str]:
        """
        .flag_confirmed の出現またはコンテナ終了を監視し、リアルタイムでログを出力する。

        submit_flag.sh が正解フラグを確認すると .flag_confirmed を作成する。
        5秒間隔でポーリングし、以下のいずれかで終了:
        - .flag_confirmed にフラグが書き込まれた（CTFd確認済み正解）
        - コンテナが終了した
        - タイムアウトに達した
        - cancel_eventが設定された（他エージェントが正解）

        Args:
            container: Dockerコンテナオブジェクト
            workspace_path: ワークスペースパス
            timeout: タイムアウト秒数
            agent_name: エージェント名（ログ用）
            cancel_event: キャンセルシグナル
            log_file_path: リアルタイムログ書き込み先（Noneならファイル書き込みなし）

        Returns:
            フラグ文字列。見つからなかった場合はNone。
        """
        confirmed_path = workspace_path / ".flag_confirmed"
        flag_path = workspace_path / "Flag.txt"
        writeup_path = workspace_path / "WriteUp" / "writeup.md"
        deadline = time.time() + timeout
        log_byte_offset = 0  # ログのバイトオフセット（差分取得用）
        iteration_count = 0
        detected_flag = None  # 正解検出済みフラグ
        grace_deadline = None  # WriteUp作成猶予の期限

        # リアルタイムログファイルを開く（追記モード）
        log_fh = None
        if log_file_path:
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            log_fh = open(log_file_path, "a", encoding="utf-8")

        logger.info(
            "[%s] フラグ監視開始: コンテナ=%s, タイムアウト=%d秒",
            agent_name, container.short_id, timeout
        )

        try:
            while time.time() < deadline:
                iteration_count += 1

                # ── .flag_confirmed チェック（cancel_eventより先に確認） ──
                if not detected_flag and confirmed_path.exists():
                    flag = confirmed_path.read_text().strip()
                    if flag:
                        logger.info("[%s] ★ CTFd確認済み正解フラグ: %s", agent_name, flag)
                        detected_flag = flag
                        if cancel_event and not cancel_event.is_set():
                            cancel_event.set()
                        grace_deadline = time.time() + WRITEUP_GRACE_PERIOD
                        logger.info("[%s] WriteUp待機開始（最大%d秒）", agent_name, WRITEUP_GRACE_PERIOD)

                # ── キャンセルチェック（他エージェントが正解済み、自分は未検出） ──
                if cancel_event and cancel_event.is_set() and not detected_flag:
                    logger.info("[%s] キャンセルシグナル受信 → コンテナ停止", agent_name)
                    try:
                        final_logs = container.logs().decode("utf-8", errors="replace")
                        self._cancelled_logs[agent_name] = final_logs
                        # キャンセル時も残りのログをファイルに書き込み
                        if log_fh:
                            remaining = final_logs[log_byte_offset:]
                            if remaining:
                                log_fh.write(remaining)
                    except Exception:
                        self._cancelled_logs[agent_name] = ""
                    self._cleanup_container(container)
                    return None

                # ── WriteUp猶予期限チェック ──
                if grace_deadline:
                    if writeup_path.exists() and writeup_path.stat().st_size > 0:
                        # ファイルが安定（書き込み完了）するまで待つ
                        size1 = writeup_path.stat().st_size
                        time.sleep(3)
                        size2 = writeup_path.stat().st_size if writeup_path.exists() else 0
                        if size2 > 0 and size1 == size2:
                            logger.info("[%s] WriteUpファイル検出（%d bytes、安定確認済み） → 終了", agent_name, size2)
                            return detected_flag
                        else:
                            logger.debug("[%s] WriteUp書き込み中（%d → %d bytes）、待機継続", agent_name, size1, size2)
                    if time.time() > grace_deadline:
                        # 期限到達時もファイルが存在すれば最終チェック
                        if writeup_path.exists() and writeup_path.stat().st_size > 0:
                            logger.info("[%s] WriteUp猶予期限到達（WriteUp回収済み %d bytes） → 終了", agent_name, writeup_path.stat().st_size)
                        else:
                            logger.warning("[%s] WriteUp猶予期限(%d秒)到達（WriteUp未生成） → 終了", agent_name, WRITEUP_GRACE_PERIOD)
                        return detected_flag

                try:
                    # コンテナの詳細状態確認
                    container.reload()
                    status = container.status
                    
                    if iteration_count == 1:
                        logger.info(
                            "[%s] 監視サイクル %d: ステータス=%s",
                            agent_name, iteration_count, status
                        )
                    
                    # リアルタイムログを出力（バイトオフセットで差分取得）
                    try:
                        all_logs = container.logs().decode("utf-8", errors="replace")
                        new_part = all_logs[log_byte_offset:]
                        if new_part.strip():
                            for line in new_part.splitlines():
                                if line.strip():
                                    agent_stream_logger.info("[%s] %s", agent_name, line)
                            # リアルタイムでログファイルに書き込み
                            if log_fh:
                                log_fh.write(new_part)
                                log_fh.flush()
                            log_byte_offset = len(all_logs)
                            
                            # リアルタイムで正解フラグを検出
                            if not detected_flag:
                                detected = self._detect_correct_in_logs(new_part, agent_name)
                                if detected:
                                    logger.info("[%s] ★ リアルタイムで正解検出: %s", agent_name, detected)
                                    detected_flag = detected
                                    self.save_flag_to_workspace(workspace_path, detected)
                                    if cancel_event and not cancel_event.is_set():
                                        cancel_event.set()
                                    grace_deadline = time.time() + WRITEUP_GRACE_PERIOD
                                    logger.info("[%s] WriteUp待機開始（最大%d秒、ファイル出現で早期終了）", agent_name, WRITEUP_GRACE_PERIOD)
                    except Exception as e:
                        logger.debug("[%s] ログ取得エラー: %s", agent_name, e)

                    # コンテナの状態を確認
                    if status in ("exited", "dead"):
                        if detected_flag:
                            # コンテナ終了直後、ファイルI/Oの安定を待つ
                            time.sleep(2)
                            if writeup_path.exists() and writeup_path.stat().st_size > 0:
                                logger.info("[%s] 正解エージェント終了（WriteUp回収済み %d bytes）", agent_name, writeup_path.stat().st_size)
                            else:
                                logger.warning("[%s] 正解エージェント終了（WriteUp無し） — エージェントがWriteUpを作成しませんでした", agent_name)
                            return detected_flag
                        
                        logger.info("[%s] コンテナ終了検出: %s", agent_name, status)
                        # コンテナ終了後に最終フラグチェック（.flag_confirmed優先）
                        if confirmed_path.exists():
                            flag = confirmed_path.read_text().strip()
                            if flag:
                                logger.info("[%s] ★ 終了後CTFd確認済みフラグ発見: %s", agent_name, flag)
                                return flag
                        if flag_path.exists():
                            flag = flag_path.read_text().strip()
                            if flag:
                                logger.info("[%s] 終了後Flag.txt発見: %s", agent_name, flag)
                                return flag

                        # ログ全体から最終抽出
                        try:
                            full_logs = container.logs().decode("utf-8", errors="replace")
                            log_flag = self._extract_flag_from_logs(full_logs, agent_name)
                            if log_flag:
                                return log_flag
                        except Exception:
                            pass

                        # WriteUpからフラグ抽出（最終フォールバック）
                        writeup_flag = self._extract_flag_from_writeup(writeup_path, agent_name)
                        if writeup_flag:
                            return writeup_flag
                        
                        logger.info("[%s] コンテナが終了（フラグなし）", agent_name)
                        return None

                    # 10分経過時の中間報告
                    if iteration_count == 120:
                        logger.warning("[%s] 10分経過、まだ実行中...", agent_name)

                except Exception as e:
                    logger.error("[%s] 監視エラー: %s", agent_name, e)
                    if detected_flag:
                        return detected_flag
                    if flag_path.exists():
                        flag = flag_path.read_text().strip()
                        if flag:
                            logger.info("[%s] エラー後フラグ発見: %s", agent_name, flag)
                            return flag
                    return None

                time.sleep(5)

            # タイムアウト
            logger.warning("[%s] タイムアウト: コンテナ %s", agent_name, container.short_id)
            self._cleanup_container(container)
            return detected_flag
        finally:
            if log_fh:
                log_fh.close()

    # ── フラグ検出の共通ロジック ────────────────────────────────

    # フラグのような文字列を抽出する正規表現
    _FLAG_RE = re.compile(r'[A-Za-z0-9_]+\{[^}]{3,}\}')
    # プレースホルダー除外セット
    _PLACEHOLDERS = {
        "flag{example_flag_123}", "flag{...}", "FLAG{...}", "CTF{...}", "flag{FLAG}",
        "YOUR_FLAG_HERE", "DISCOVERED_FLAG",
    }
    # 成功キーワード（行内に存在すれば正解と判断）
    _SUCCESS_KEYWORDS = (
        "correct", "accepted", "success", "submitted",
        "正解", "成功", "提出しました",
        "CTFd応答: correct", "already_solved",
    )

    def _detect_flag_in_line(self, line: str) -> Optional[str]:
        """
        1行からフラグ+成功シグナルを検出する。

        対応する出力形式:
        - submit_flag.sh: "FLAG_CONFIRMED_CORRECT: CyberQuest{...}" (最も信頼性高)
        - JSON: {"status": "correct"} （"incorrect"は除外）
        - codex: エスケープ付き \"submission\":\"FLAG\" + correct
        - copilot自然言語: 「攻略成功...CyberQuest{...}（CTFd応答: correct）」
        - 一般: 任意の FLAG{} パターン + 成功キーワードが同一行に存在

        Returns:
            検出されたフラグ文字列。見つからない場合はNone。
        """
        # "incorrect" を含む行は不正解なのでスキップ
        # ただし FLAG_CONFIRMED_CORRECT は除外しない
        line_lower = line.lower()
        if "incorrect" in line_lower and "flag_confirmed_correct" not in line_lower:
            return None

        # FLAG_CONFIRMED_CORRECT: ... を最優先検出
        if "FLAG_CONFIRMED_CORRECT:" in line:
            flags_in_line = self._FLAG_RE.findall(line)
            candidates = [f for f in flags_in_line if f not in self._PLACEHOLDERS]
            if candidates:
                return candidates[-1]

        # 行内にフラグパターンがあるか
        flags_in_line = self._FLAG_RE.findall(line)
        if not flags_in_line:
            return None

        # プレースホルダー除外
        candidates = [f for f in flags_in_line if f not in self._PLACEHOLDERS]
        if not candidates:
            return None

        # 成功キーワードが同一行にあるか
        has_success = any(kw in line_lower for kw in self._SUCCESS_KEYWORDS)
        if has_success:
            return candidates[-1]  # 最後のフラグ候補（提出結果に近い方）

        return None

    def _extract_flag_from_writeup(self, writeup_path: Path, agent_name: str) -> Optional[str]:
        """WriteUpファイルからフラグを抽出する（最終フォールバック）。"""
        try:
            if not writeup_path.exists() or writeup_path.stat().st_size == 0:
                return None
            content = writeup_path.read_text(errors="replace")
            flags = self._FLAG_RE.findall(content)
            candidates = [f for f in flags if f not in self._PLACEHOLDERS]
            if candidates:
                flag = candidates[-1]
                logger.info("[%s] WriteUpからフラグ抽出: %s", agent_name, flag)
                return flag
        except Exception as e:
            logger.debug("[%s] WriteUp読み取りエラー: %s", agent_name, e)
        return None

    def _extract_flag_from_logs(self, logs: str, agent_name: str) -> Optional[str]:
        """
        コンテナログからcurl提出で正解になったフラグを抽出する。
        """
        lines = logs.splitlines()
        last_submission = None

        for line in lines:
            # submission値を追跡（JSON / エスケープ付き）
            m = re.search(r'"submission"\s*:\s*"([^"]+)"', line)
            if m and m.group(1) not in self._PLACEHOLDERS:
                last_submission = m.group(1)
            m2 = re.search(r'\\?"submission\\?"\s*:\\?\s*\\?"([^"\\]+)\\?"', line)
            if m2 and m2.group(1) not in self._PLACEHOLDERS:
                last_submission = m2.group(1)

            # APIレスポンスで "correct" → 直前のsubmissionを返す
            if '"status"' in line and '"correct"' in line and '"incorrect"' not in line:
                if last_submission:
                    logger.info("[%s] ログからcurl成功フラグ抽出: %s", agent_name, last_submission)
                    return last_submission

            # 汎用: フラグ+成功キーワードが同一行にあれば検出
            detected = self._detect_flag_in_line(line)
            if detected:
                logger.info("[%s] ログからフラグ抽出: %s", agent_name, detected)
                return detected

        return None

    def _detect_correct_in_logs(self, logs: str, agent_name: str) -> Optional[str]:
        """
        ログの断片からcurl提出の正解を即座に検出する（リアルタイム用）。
        """
        lines = logs.splitlines()
        last_submission = None

        for line in lines:
            # submission値を追跡
            m = re.search(r'"submission"\s*:\s*"([^"]+)"', line)
            if m and m.group(1) not in self._PLACEHOLDERS:
                last_submission = m.group(1)
            m2 = re.search(r'\\?"submission\\?"\s*:\\?\s*\\?"([^"\\]+)\\?"', line)
            if m2 and m2.group(1) not in self._PLACEHOLDERS:
                last_submission = m2.group(1)

            # APIレスポンス "correct" → 直前のsubmission
            if '"status"' in line and '"correct"' in line and '"incorrect"' not in line:
                if last_submission:
                    return last_submission

            # 汎用: フラグ+成功キーワード同一行
            detected = self._detect_flag_in_line(line)
            if detected:
                return detected

        return None

    # ── コンテナ操作ヘルパー ─────────────────────────────────

    def _cleanup_container(self, container):
        """コンテナを安全に停止・削除する。"""
        try:
            container.stop(timeout=10)
        except Exception:
            pass
        try:
            container.remove(force=True)
        except Exception:
            pass

    def save_flag_to_workspace(self, workspace_path: Path, flag: str):
        """ワークスペースのFlag.txtにフラグを書き込む。"""
        (workspace_path / "Flag.txt").write_text(flag)

    # ── ワークスペースのクリーンアップ ────────────────────────

    def cleanup_workspace(self, workspace_path: Path):
        """一時ワークスペースディレクトリを削除する。"""
        shutil.rmtree(workspace_path, ignore_errors=True)
