#!/usr/bin/env python3
"""
CTF Writeup Generator

このスクリプトは、CTF Solverで解決した問題のwriteupを収集・生成します。
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from orchestrator.ctfd_client import CTFdClient


def load_config():
    """設定ファイルを読み込む"""
    load_dotenv()

    with open("config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    ctfd_url = os.environ.get("CTFD_URL", "")
    ctfd_token = os.environ.get("CTFD_TOKEN", "")

    if not ctfd_url or not ctfd_token:
        print("エラー: CTFD_URLとCTFD_TOKENを.envファイルに設定してください")
        sys.exit(1)

    return ctfd_url, ctfd_token


def collect_solved_challenges(challenges_dir: Path):
    """解決済み問題の情報を収集する"""
    solved = []

    if not challenges_dir.exists():
        return solved

    for challenge_path in challenges_dir.iterdir():
        if not challenge_path.is_dir():
            continue

        # .solvedファイルの存在を確認
        solved_file = challenge_path / ".solved"
        if not solved_file.exists():
            continue

        # 問題情報を収集
        challenge_info = {
            "id": challenge_path.name,
            "path": challenge_path,
        }

        # 問題文を読み込む
        problem_file = challenge_path / "problem.txt"
        if problem_file.exists():
            with open(problem_file, "r", encoding="utf-8") as f:
                challenge_info["problem"] = f.read()

        # フラグを読み込む
        flag_file = challenge_path / "Solved-Flag.txt"
        if flag_file.exists():
            with open(flag_file, "r", encoding="utf-8") as f:
                challenge_info["flag"] = f.read().strip()

        # Writeupを読み込む
        writeup_file = challenge_path / "WriteUp" / "writeup.md"
        if writeup_file.exists():
            with open(writeup_file, "r", encoding="utf-8") as f:
                challenge_info["writeup"] = f.read()

        solved.append(challenge_info)

    return solved


def generate_master_writeup(solved_challenges: list, output_path: Path):
    """すべての解決済み問題のマスターwriteupを生成する"""

    if not solved_challenges:
        print("解決済みの問題が見つかりませんでした。")
        return

    content = f"""# CTF Writeup Collection

**生成日時**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**解決済み問題数**: {len(solved_challenges)}

---

"""

    for i, challenge in enumerate(sorted(solved_challenges, key=lambda x: x["id"]), 1):
        content += f"\n## {i}. Challenge ID: {challenge['id']}\n\n"

        if "problem" in challenge:
            content += f"### 問題文\n\n{challenge['problem']}\n\n"

        if "flag" in challenge:
            content += f"### フラグ\n\n```\n{challenge['flag']}\n```\n\n"

        if "writeup" in challenge:
            content += f"### Writeup\n\n{challenge['writeup']}\n\n"
        else:
            content += "### Writeup\n\n（Writeupが生成されていません）\n\n"

        content += "---\n"

    # 出力
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✓ マスターwriteupを生成しました: {output_path}")


def generate_individual_writeups(solved_challenges: list, output_dir: Path):
    """個別の問題ごとにwriteupファイルを生成する"""

    output_dir.mkdir(parents=True, exist_ok=True)

    for challenge in solved_challenges:
        challenge_id = challenge["id"]
        output_file = output_dir / f"challenge_{challenge_id}.md"

        content = f"""# Challenge {challenge_id}

**生成日時**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

"""

        if "problem" in challenge:
            content += f"## 問題文\n\n{challenge['problem']}\n\n"

        if "flag" in challenge:
            content += f"## フラグ\n\n```\n{challenge['flag']}\n```\n\n"

        if "writeup" in challenge:
            content += f"## Writeup\n\n{challenge['writeup']}\n\n"
        else:
            content += "## Writeup\n\n（Writeupが生成されていません）\n\n"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✓ Writeupを生成: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="CTF Writeup Generator")
    parser.add_argument(
        "--output",
        type=str,
        default="writeups/master_writeup.md",
        help="マスターwriteupの出力パス（デフォルト: writeups/master_writeup.md）"
    )
    parser.add_argument(
        "--individual",
        action="store_true",
        help="個別のwriteupファイルも生成する"
    )
    parser.add_argument(
        "--individual-dir",
        type=str,
        default="writeups/individual",
        help="個別writeupの出力ディレクトリ（デフォルト: writeups/individual）"
    )

    args = parser.parse_args()

    print("=== CTF Writeup Generator ===")
    print()

    # 解決済み問題を収集
    challenges_dir = Path("challenges")
    print(f"解決済み問題を収集中: {challenges_dir}")
    solved_challenges = collect_solved_challenges(challenges_dir)
    print(f"✓ {len(solved_challenges)}個の解決済み問題を見つけました")
    print()

    if not solved_challenges:
        print("解決済みの問題がありません。")
        return

    # マスターwriteupを生成
    output_path = Path(args.output)
    print(f"マスターwriteupを生成中: {output_path}")
    generate_master_writeup(solved_challenges, output_path)
    print()

    # 個別writeupを生成（オプション）
    if args.individual:
        individual_dir = Path(args.individual_dir)
        print(f"個別writeupを生成中: {individual_dir}")
        generate_individual_writeups(solved_challenges, individual_dir)
        print()

    print("=== 完了 ===")


if __name__ == "__main__":
    main()
