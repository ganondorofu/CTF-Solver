"""
Docker管理モジュール

各AIエージェント用のDockerコンテナを起動・監視・停止する。
ワークスペースの準備とコンテナ内へのマウントも担当する。
"""

import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

import docker
from docker.errors import ContainerError, ImageNotFound, APIError

logger = logging.getLogger(__name__)


class DockerManager:
    """Dockerコンテナのライフサイクルを管理するクラス"""

    # エージェントタイプ別認証ディレクトリマッピング
    AUTH_MOUNTS = {
        "copilot_cli": [
            "~/.config/github-copilot",
            "~/.copilot",
        ],
        "gemini_cli": [
            "~/.gemini",
            "~/.config/gemini-cli",
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
    ) -> tuple[Optional[str], str]:
        """
        エージェント用のDockerコンテナを起動し、フラグを取得する。

        コンテナ内でentrypoint.shが実行され、
        AGENT_TYPEに応じた適切なランナースクリプトが起動される。

        Args:
            agent_name: エージェントの識別名
            agent_cfg: エージェントの設定辞書
            workspace_path: マウントするワークスペースパス
            timeout: タイムアウト秒数

        Returns:
            (フラグ文字列 or None, ログ文字列) のタプル
        """
        # 環境変数を構築
        env = self._resolve_env_vars(agent_cfg)
        env["AGENT_NAME"] = agent_name
        env["AGENT_TYPE"] = agent_cfg.get("type", agent_name)
        env["AGENT_TIMEOUT"] = str(timeout - 50)  # 余裕を持たせる

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

            # Flag.txtの出現またはコンテナ終了を待機
            flag = self._wait_for_flag(container, workspace_path, timeout)

            # コンテナログを取得
            logs = container.logs().decode("utf-8", errors="replace")

            # コンテナを停止・削除
            self._cleanup_container(container)

            return flag, logs

        except (ContainerError, ImageNotFound, APIError) as e:
            logger.error("Dockerエラー（エージェント %s）: %s", agent_name, e)
            return None, str(e)

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
    ) -> Optional[str]:
        """
        Flag.txtの出現またはコンテナ終了を監視し、リアルタイムでログを出力する。

        5秒間隔でポーリングし、以下のいずれかで終了:
        - Flag.txtにフラグが書き込まれた
        - コンテナが終了した
        - タイムアウトに達した

        Args:
            container: Dockerコンテナオブジェクト
            workspace_path: ワークスペースパス
            timeout: タイムアウト秒数

        Returns:
            フラグ文字列。見つからなかった場合はNone。
        """
        flag_path = workspace_path / "Flag.txt"
        deadline = time.time() + timeout
        last_log_position = 0

        while time.time() < deadline:
            # リアルタイムログを出力
            try:
                logs = container.logs(since=last_log_position).decode("utf-8", errors="replace")
                if logs.strip():
                    print(f"\n=== {container.short_id} ログ ===")
                    print(logs, end="", flush=True)  # リアルタイム出力
                    print("=" * 50)
                    last_log_position = int(time.time())
            except Exception as e:
                logger.debug("ログ取得エラー（コンテナ削除済み？）: %s", e)

            # Flag.txtの存在と内容を確認
            if flag_path.exists():
                flag = flag_path.read_text().strip()
                if flag:
                    logger.info("フラグ発見: %s", flag)
                    return flag

            # コンテナの状態を確認
            try:
                container.reload()
                if container.status in ("exited", "dead"):
                    # コンテナ終了後に最終チェック
                    if flag_path.exists():
                        flag = flag_path.read_text().strip()
                        if flag:
                            return flag
                    logger.info("コンテナが終了（フラグなし）")
                    return None
            except Exception as e:
                # コンテナが既に削除されている場合
                logger.warning("コンテナアクセスエラー: %s", e)
                if flag_path.exists():
                    flag = flag_path.read_text().strip()
                    if flag:
                        return flag
                return None

            time.sleep(5)

        # タイムアウト
        logger.warning(
            "タイムアウト: コンテナ %s", container.short_id
        )
        self._cleanup_container(container)
        return None

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

    # ── ワークスペースのクリーンアップ ────────────────────────

    def cleanup_workspace(self, workspace_path: Path):
        """一時ワークスペースディレクトリを削除する。"""
        shutil.rmtree(workspace_path, ignore_errors=True)
