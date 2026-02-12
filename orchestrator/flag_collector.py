"""
フラグ収集・評価モジュール

複数エージェントからフラグ候補を収集し、
多数決投票で最も確からしいフラグを選択する。
"""

import logging
from collections import Counter
from typing import Optional

logger = logging.getLogger(__name__)


class FlagCollector:
    """複数エージェントのフラグを集約し、提出候補を決定するクラス"""

    def __init__(self, method: str = "voting", wait_time: int = 30):
        """
        フラグコレクターを初期化する。

        Args:
            method: フラグ選択方法（"voting"=多数決, "first"=最初の1つ）
            wait_time: エージェントからのフラグ収集待機時間（秒）
        """
        self.method = method
        self.wait_time = wait_time

    def collect_and_decide(
        self, flags: dict[str, Optional[str]]
    ) -> Optional[str]:
        """
        エージェントからのフラグ候補を評価し、提出するフラグを決定する。

        Args:
            flags: {エージェント名: フラグ文字列 or None} の辞書

        Returns:
            提出するフラグ文字列。有効なフラグが無い場合はNone。
        """
        # Noneや空文字列を除外して有効なフラグのみ抽出
        valid = {k: v for k, v in flags.items() if v}
        if not valid:
            logger.info("有効なフラグが1つも収集できませんでした")
            return None

        logger.info("収集したフラグ: %s", valid)

        # 選択方法に応じてフラグを決定
        if self.method == "voting":
            return self._vote(valid)
        elif self.method == "first":
            return next(iter(valid.values()))
        else:
            # デフォルトは多数決
            return self._vote(valid)

    def _vote(self, flags: dict[str, str]) -> str:
        """
        多数決投票でフラグを決定する。

        同数の場合は最初に発見されたフラグを優先する。

        Args:
            flags: {エージェント名: フラグ文字列} の辞書

        Returns:
            最多得票のフラグ文字列
        """
        counter = Counter(flags.values())
        winner, count = counter.most_common(1)[0]
        logger.info(
            "投票結果: '%s'（%d/%d 票）", winner, count, len(flags)
        )
        return winner

    def build_summary(
        self, flags: dict[str, Optional[str]], chosen: Optional[str]
    ) -> dict:
        """
        フラグ収集結果のサマリーを構築する。

        Args:
            flags: 全エージェントのフラグ結果
            chosen: 選択されたフラグ

        Returns:
            Flags/summary.json に保存するための辞書
        """
        return {
            "agent_flags": {k: v for k, v in flags.items()},
            "chosen_flag": chosen,
            "method": self.method,
            "total_agents": len(flags),
            "flags_found": sum(1 for v in flags.values() if v),
        }
