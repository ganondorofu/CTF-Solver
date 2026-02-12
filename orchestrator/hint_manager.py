"""
ヒント管理モジュール

CTFdからヒントを取得する。
コスト付きヒントをブロックし、無料ヒントのみを安全に取得する。
"""

import logging
from typing import Optional

from .ctfd_client import CTFdClient

logger = logging.getLogger(__name__)


class HintManager:
    """ヒントの取得とコスト制御を管理するクラス"""

    def __init__(
        self,
        client: CTFdClient,
        allow_cost_hints: bool = False,
        max_cost: int = 0,
    ):
        """
        ヒントマネージャーを初期化する。

        Args:
            client: CTFdクライアントインスタンス
            allow_cost_hints: コスト付きヒントの取得を許可するか
            max_cost: 許容する最大ヒントコスト（0=無料のみ）
        """
        self.client = client
        self.allow_cost_hints = allow_cost_hints
        self.max_cost = max_cost

    def get_free_hints(self, challenge_id: int) -> list[str]:
        """
        指定問題の無料ヒントを全て取得する。

        コスト付きヒントはallow_cost_hintsがTrueかつ
        コストがmax_cost以下の場合のみ取得する。

        Args:
            challenge_id: 問題ID

        Returns:
            ヒント内容文字列のリスト
        """
        hints_meta = self.client.get_hints(challenge_id)
        free_hints: list[str] = []

        for h in hints_meta:
            cost = h.get("cost", 0)
            hint_id = h.get("id")

            # コスト付きヒントのブロック判定
            if cost > 0:
                if not self.allow_cost_hints or cost > self.max_cost:
                    logger.info(
                        "ヒント %s をスキップ（コスト=%d、ブロック対象）",
                        hint_id,
                        cost,
                    )
                    continue

            # ヒント内容の取得を試行
            try:
                detail = self.client.get_hint_detail(hint_id)
                content = detail.get("content", "")
                if content:
                    free_hints.append(content)
                    logger.info(
                        "ヒント %s を取得（問題 %d）", hint_id, challenge_id
                    )
            except Exception as e:
                logger.warning("ヒント %s の取得に失敗: %s", hint_id, e)

        return free_hints

    def format_hints(self, hints: list[str]) -> Optional[str]:
        """
        ヒントリストを整形されたテキストに変換する。

        Args:
            hints: ヒント文字列のリスト

        Returns:
            整形されたヒントテキスト。ヒントが無い場合はNone。
        """
        if not hints:
            return None
        lines = []
        for i, h in enumerate(hints, 1):
            lines.append(f"### Hint {i}\n{h}")
        return "\n\n".join(lines)
