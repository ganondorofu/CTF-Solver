"""
CTFd APIクライアント

CTFdプラットフォームとの全通信を担当する。
問題一覧取得、ヒント取得、ファイルダウンロード、フラグ提出などを行う。
"""

import logging
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


class CTFdClient:
    """CTFd REST APIとの通信を行うクライアントクラス"""

    def __init__(self, url: str, token: str):
        """
        CTFdクライアントを初期化する。

        Args:
            url: CTFdプラットフォームのベースURL
            token: CTFd APIアクセストークン
        """
        self.base_url = url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
        })

    def _api(self, method: str, endpoint: str, **kwargs) -> dict:
        """
        CTFd APIにリクエストを送信する共通メソッド。

        Args:
            method: HTTPメソッド（GET, POST等）
            endpoint: APIエンドポイントパス
            **kwargs: requestsに渡す追加パラメータ

        Returns:
            APIレスポンスのJSONデータ

        Raises:
            requests.HTTPError: APIリクエストが失敗した場合
        """
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()

    # ── 問題取得 ─────────────────────────────────────────────

    def get_challenges(self) -> list[dict]:
        """全ての可視問題の一覧を取得する。"""
        data = self._api("GET", "/challenges")
        return data.get("data", [])

    def get_challenge(self, challenge_id: int) -> dict:
        """指定IDの問題の詳細情報を取得する。"""
        data = self._api("GET", f"/challenges/{challenge_id}")
        return data.get("data", {})

    # ── ヒント取得 ───────────────────────────────────────────

    def get_hints(self, challenge_id: int) -> list[dict]:
        """指定問題のヒントメタデータ一覧を取得する。

        403などのアクセス制限が発生する場合は空リストを返す。
        """
        try:
            data = self._api("GET", "/hints", params={"challenge_id": challenge_id})
            return data.get("data", [])
        except requests.exceptions.HTTPError as e:
            logger.warning("ヒント一覧の取得でHTTPエラー: %s (扱い: ヒント無し)", e)
            return []
        except Exception as e:
            logger.warning("ヒント一覧の取得で予期せぬエラー: %s (扱い: ヒント無し)", e)
            return []

    def get_hint_detail(self, hint_id: int) -> dict:
        """ヒントの詳細内容を取得する（無料またはアンロック済みのみ）。"""
        data = self._api("GET", f"/hints/{hint_id}")
        return data.get("data", {})

    def unlock_hint(self, hint_id: int) -> dict:
        """ヒントをアンロックする（コストが発生する場合がある）。"""
        data = self._api("POST", "/unlocks", json={
            "target": hint_id,
            "type": "hints",
        })
        return data.get("data", {})

    # ── ファイル取得 ─────────────────────────────────────────

    def get_challenge_files(self, challenge_id: int) -> list[str]:
        """指定問題の配布ファイルURL一覧を取得する。"""
        detail = self.get_challenge(challenge_id)
        return detail.get("files", [])

    def download_file(self, file_path: str) -> bytes:
        """配布ファイルをダウンロードし、バイトデータを返す。"""
        url = f"{self.base_url}/{file_path.lstrip('/')}"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.content

    # ── フラグ提出 ───────────────────────────────────────────

    def submit_flag(self, challenge_id: int, flag: str) -> dict:
        """
        フラグをCTFdに提出し、結果を返す。

        Returns:
            APIレスポンス全体: {"success": bool, "data": {"status": "...", "message": "..."}}
        """
        return self._api("POST", "/challenges/attempt", json={
            "challenge_id": challenge_id,
            "submission": flag,
        })

    # ── 解答状況 ─────────────────────────────────────────────

    def get_solves(self, challenge_id: int) -> list[dict]:
        """指定問題の解答者一覧を取得する。"""
        data = self._api("GET", f"/challenges/{challenge_id}/solves")
        return data.get("data", [])
