"""
ファイル管理モジュール

CTFdから配布ファイルをダウンロードし、
ローカルのchall/ディレクトリに保存する。
"""

import logging
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from .ctfd_client import CTFdClient

logger = logging.getLogger(__name__)


class FileManager:
    """配布ファイルのダウンロードと管理を行うクラス"""

    def __init__(self, client: CTFdClient, max_size_mb: int = 100):
        """
        ファイルマネージャーを初期化する。

        Args:
            client: CTFdクライアントインスタンス
            max_size_mb: ダウンロードを許可する最大ファイルサイズ（MB）
        """
        self.client = client
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def download_challenge_files(
        self, challenge_id: int, dest_dir: Path
    ) -> list[dict]:
        """
        指定問題の全配布ファイルをダウンロードする。

        Args:
            challenge_id: 問題ID
            dest_dir: ファイル保存先ディレクトリ

        Returns:
            各ファイルのメタデータリスト
            [{"filename": "...", "url": "...", "size": N, "status": "..."}]
        """
        file_urls = self.client.get_challenge_files(challenge_id)
        metadata: list[dict] = []

        for file_url in file_urls:
            filename = self._extract_filename(file_url)
            dest_path = dest_dir / filename

            try:
                # ファイルをダウンロード
                data = self.client.download_file(file_url)

                # サイズチェック
                if len(data) > self.max_size_bytes:
                    logger.warning(
                        "ファイル %s が大きすぎます（%d bytes）、スキップ",
                        filename,
                        len(data),
                    )
                    metadata.append({
                        "filename": filename,
                        "url": file_url,
                        "size": len(data),
                        "status": "skipped_too_large",
                    })
                    continue

                # ファイルを保存
                dest_path.write_bytes(data)
                logger.info("ダウンロード完了: %s（%d bytes）", filename, len(data))
                metadata.append({
                    "filename": filename,
                    "url": file_url,
                    "size": len(data),
                    "status": "downloaded",
                })

            except Exception as e:
                logger.error("ダウンロード失敗: %s: %s", filename, e)
                metadata.append({
                    "filename": filename,
                    "url": file_url,
                    "size": 0,
                    "status": f"error: {e}",
                })

        return metadata

    @staticmethod
    def _extract_filename(url: str) -> str:
        """
        CTFdファイルURLからファイル名を抽出する。

        CTFdのURLは /files/<hash>/filename.ext の形式。
        """
        parsed = urlparse(url)
        path = unquote(parsed.path)
        basename = os.path.basename(path)
        return basename if basename else "unknown_file"
