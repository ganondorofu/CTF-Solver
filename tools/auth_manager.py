#!/usr/bin/env python3
"""
CTF Solver 認証プロファイル管理ツール

対話形式で各AIツールのOAuth認証情報をプロファイルとして保存・管理する。
agents.yaml の auth_profiles で名前参照でき、
instances_per_profile でプロファイルごとに何コンテナ起動するか指定できる。

使い方:
    python tools/auth_manager.py

プロファイル保存先:
    ~/.ctf-solver/profiles/{agent_type}/{profile_name}/

agents.yaml 設定例:
    claude_code:
      instances_per_profile: 2  # プロファイル1つにつき2コンテナ
      auth_profiles:
        - main        # → claude_code#1, #2
        - sneakpeek   # → claude_code#3, #4
"""

import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROFILES_BASE = Path.home() / ".ctf-solver" / "profiles"

# ──────────────────────────────────────────────────────────────────
# プロバイダ定義
#
# logout / login の形式:
#   cmd          : サイレント実行するコマンド（logout）またはインタラクティブ実行（login）
#   delete_files : ログアウト時に削除するファイルリスト（cmd の代わり）
#   steps        : 複数ステップのログインシーケンス
#                  各要素: {"cmd": [...], "desc": "説明", "optional": bool}
#   note         : ユーザーへの手動操作指示（cmd の代わり）
# ──────────────────────────────────────────────────────────────────

PROVIDERS: dict[str, dict] = {
    "claude_code": {
        "name": "Claude Code (Anthropic OAuth)",
        # ✓ claude auth logout / claude auth login が使える
        "logout": {"cmd": ["claude", "auth", "logout"]},
        "login":  {"cmd": ["claude", "auth", "login"]},
        "source_dir": Path.home() / ".claude",
        "subdirs": {
            "claude": [".credentials.json", "settings.json"],
        },
    },

    "copilot_cli": {
        "name": "GitHub Copilot CLI",
        # ✗ logout コマンドなし → config.json を削除
        "logout": {
            "delete_files": [Path.home() / ".copilot" / "config.json"],
        },
        # copilot login (OAuth device flow) → 続いて gh auth login も実施
        "login": {
            "cmd":  ["copilot", "login"],
            "note": (
                "ブラウザで認証後、以下の質問が出たら必ず y を入力してください:\n"
                "  \"Store token in plaintext config file? (y/N)\"  ← y + Enter"
            ),
        },
        "source_dir": Path.home() / ".copilot",
        "subdirs": {
            # ~/.copilot から認証ファイルのみ（session-state/ 等は除外）
            "copilot": ["config.json", "mcp-config.json"],
        },
    },

    "gemini_cli": {
        "name": "Gemini CLI (Google)",
        # ✗ auth サブコマンドなし → 認証ファイルを直接削除
        "logout": {
            "delete_files": [
                Path.home() / ".gemini" / "oauth_creds.json",
                Path.home() / ".gemini" / "google_accounts.json",
            ],
        },
        # ✗ 専用ログインコマンドなし → gemini 起動で自動 OAuth
        # ユーザーが認証を終えたら /quit または Ctrl+C で終了してもらう
        "login": {
            "cmd":  ["gemini"],
            "note": (
                "Gemini が起動します。Google OAuth が完了したら\n"
                "  /quit と入力するか Ctrl+C で終了してください。"
            ),
        },
        "source_dir": Path.home() / ".gemini",
        "subdirs": {
            # tmp/ などは不要。認証に必要なファイルのみ
            "gemini": ["oauth_creds.json", "google_accounts.json",
                       "settings.json", "installation_id"],
        },
    },

    "codex_cli": {
        "name": "Codex CLI (OpenAI)",
        "logout": {"cmd": ["codex", "auth", "logout"]},
        "login":  {"cmd": ["codex", "auth", "login"]},
        "source_dir": Path.home() / ".codex",
        "subdirs": {
            "codex": ["auth.json"],
        },
    },

    "github_cli": {
        "name": "GitHub CLI (gh)",
        "logout": {"cmd": ["gh", "auth", "logout", "--hostname", "github.com"]},
        "login":  {"cmd": ["gh", "auth", "login"]},
        "source_dir": Path.home() / ".config" / "gh",
        "subdirs": {
            "gh": ["hosts.yml", "config.yml"],
        },
    },

    "git": {
        "name": "Git",
        # ✗ logout コマンドなし → 手動で設定を削除する必要がある
        "logout": {
            "note": (
                "Git の認証情報を削除するには:\n"
                "  git config --global --unset user.name\n"
                "  git config --global --unset user.email\n"
                "  git config --global --unset credential.helper"
            ),
        },
        "login": {
            "note": (
                "Git の設定を行ってください:\n"
                "  git config --global user.name \"Your Name\"\n"
                "  git config --global user.email \"your@email.com\"\n"
                "\n設定が完了したら Enter を押してください。"
            ),
            "cmd": ["bash", "-c", "read"],
        },
        "source_dir": Path.home(),
        "subdirs": {
            "git": [".gitconfig"],
        },
    },
}


# ──────────────────────────────────────────────────────────────────
# UI ヘルパー
# ──────────────────────────────────────────────────────────────────

def _header(text: str):
    w = 52
    print(f"\n{'═' * w}")
    print(f"  {text}")
    print(f"{'═' * w}")

def _section(text: str):
    print(f"\n── {text} ──")

def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"  {prompt}{suffix}: ").strip()
    return val if val else default

def _confirm(prompt: str) -> bool:
    return input(f"  {prompt} [y/N]: ").strip().lower() == "y"

def _ok(msg: str):   print(f"  ✓ {msg}")
def _err(msg: str):  print(f"  ✗ {msg}")
def _warn(msg: str): print(f"  ! {msg}")

def _run_interactive(cmd: list[str]) -> int:
    """ターミナルを継承してコマンドを実行（OAuthフロー用）。"""
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
    return result.returncode

def _run_silent(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()

def _cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


# ──────────────────────────────────────────────────────────────────
# ログアウト処理
# ──────────────────────────────────────────────────────────────────

def _do_logout(agent_type: str) -> bool:
    provider = PROVIDERS[agent_type]
    logout_spec = provider.get("logout", {})

    if "cmd" in logout_spec:
        cmd = logout_spec["cmd"]
        if not _cmd_exists(cmd[0]):
            _warn(f"コマンドが見つかりません: {cmd[0]}（スキップ）")
            return True
        rc, out = _run_silent(cmd)
        if rc == 0:
            _ok("ログアウト完了")
        else:
            _warn(f"ログアウト応答（rc={rc}）: {out[:120]}")
        return True

    if "delete_files" in logout_spec:
        deleted = []
        for path in logout_spec["delete_files"]:
            p = Path(path)
            if p.exists():
                p.unlink()
                deleted.append(p.name)
        if deleted:
            _ok(f"認証ファイル削除: {', '.join(deleted)}")
        else:
            _warn("削除対象のファイルが見つかりませんでした（既にログアウト済み？）")
        return True

    return True  # logout spec なし = 何もしない


# ──────────────────────────────────────────────────────────────────
# ログイン処理
# ──────────────────────────────────────────────────────────────────

def _do_login(agent_type: str) -> bool:
    provider = PROVIDERS[agent_type]
    login_spec = provider.get("login", {})

    # 単一コマンドの場合
    if "cmd" in login_spec and "steps" not in login_spec:
        cmd = login_spec["cmd"]
        if not _cmd_exists(cmd[0]):
            _err(f"コマンドが見つかりません: {cmd[0]}")
            return False

        note = login_spec.get("note")
        if note:
            print(f"\n  {note}")
            print()

        rc = _run_interactive(cmd)
        if rc not in (0, 130):  # 130 = Ctrl+C
            _warn(f"終了コード: {rc}")
            return _confirm("続行しますか?")
        _ok("ログイン完了")
        return True

    # 複数ステップの場合
    if "steps" in login_spec:
        steps = login_spec["steps"]
        for i, step in enumerate(steps, 1):
            cmd      = step["cmd"]
            desc     = step.get("desc", " ".join(cmd))
            optional = step.get("optional", False)
            note     = step.get("note")
            label    = f"[{i}/{len(steps)}]"

            if not _cmd_exists(cmd[0]):
                if optional:
                    _warn(f"{label} {desc}: コマンド未インストール（スキップ）")
                    continue
                else:
                    _err(f"{label} {desc}: コマンドが見つかりません: {cmd[0]}")
                    return False

            print(f"\n  {label} {desc}")
            if note:
                print(f"\n  ⚠ {note}\n")

            rc = _run_interactive(cmd)
            if rc != 0:
                if optional:
                    _warn(f"終了コード: {rc}（任意ステップ、続行）")
                else:
                    _warn(f"終了コード: {rc}")
                    if not _confirm("続行しますか?"):
                        return False
            else:
                _ok(f"{desc} 完了")
        return True

    _warn("ログイン方法が定義されていません")
    return False


# ──────────────────────────────────────────────────────────────────
# プロファイル I/O
# ──────────────────────────────────────────────────────────────────

def _pdir(agent_type: str, profile_name: str) -> Path:
    return PROFILES_BASE / agent_type / profile_name

def list_profiles(agent_type: str) -> list[str]:
    base = PROFILES_BASE / agent_type
    if not base.exists():
        return []
    return sorted(d.name for d in base.iterdir() if d.is_dir())

def _load_meta(agent_type: str, profile_name: str) -> dict:
    f = _pdir(agent_type, profile_name) / "profile.json"
    return json.loads(f.read_text()) if f.exists() else {}

def _save_meta(agent_type: str, profile_name: str, note: str):
    pdir = _pdir(agent_type, profile_name)
    pdir.mkdir(parents=True, exist_ok=True)
    existing = _load_meta(agent_type, profile_name)
    meta = {
        "agent_type":   agent_type,
        "profile_name": profile_name,
        "created":      existing.get("created", datetime.now().isoformat()),
        "updated":      datetime.now().isoformat(),
        "note":         note or existing.get("note", ""),
    }
    (pdir / "profile.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))


def _copy_item(src: Path, dst: Path):
    """ファイルまたはディレクトリをコピー（dst が既存なら上書き）。"""
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
    elif src.is_dir():
        if dst.exists():
            shutil.rmtree(str(dst))
        shutil.copytree(str(src), str(dst))


def save_credentials(agent_type: str, profile_name: str) -> bool:
    """現在の認証情報をプロファイルディレクトリにコピーする。"""
    provider = PROVIDERS[agent_type]
    pdir = _pdir(agent_type, profile_name)
    pdir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []

    for subdir_name, spec in provider["subdirs"].items():
        if isinstance(spec, dict):
            source_dir    = spec["source"]
            files_to_copy = spec["files"]
        else:
            source_dir    = provider["source_dir"]
            files_to_copy = spec  # list | None

        if not source_dir.exists():
            _warn(f"{source_dir} が見つかりません（スキップ）")
            continue

        dst_subdir = pdir / subdir_name
        dst_subdir.mkdir(parents=True, exist_ok=True)

        if files_to_copy is None:
            for item in source_dir.iterdir():
                if item.name == "profile.json":
                    continue
                try:
                    _copy_item(item, dst_subdir / item.name)
                    copied.append(f"{subdir_name}/{item.name}")
                except Exception as e:
                    _err(f"コピー失敗 {item.name}: {e}")
        else:
            for fname in files_to_copy:
                src = source_dir / fname
                if not src.exists():
                    _warn(f"{fname} が見つかりません（スキップ）")
                    continue
                try:
                    _copy_item(src, dst_subdir / fname)
                    copied.append(f"{subdir_name}/{fname}")
                except Exception as e:
                    _err(f"コピー失敗 {fname}: {e}")

    if copied:
        _ok(f"保存: {', '.join(copied)}")
        _ok(f"保存先: {pdir}")
        return True
    else:
        _err("コピーできたファイルがありません")
        return False


def restore_credentials(agent_type: str, profile_name: str) -> bool:
    """プロファイルディレクトリから認証情報を復元する。"""
    provider = PROVIDERS[agent_type]
    pdir = _pdir(agent_type, profile_name)
    
    if not pdir.exists():
        _err(f"プロファイル '{profile_name}' が見つかりません")
        return False
    
    restored: list[str] = []
    
    for subdir_name, spec in provider["subdirs"].items():
        if isinstance(spec, dict):
            source_dir    = spec["source"]
            files_to_copy = spec["files"]
        else:
            source_dir    = provider["source_dir"]
            files_to_copy = spec  # list | None
        
        src_subdir = pdir / subdir_name
        if not src_subdir.exists():
            _warn(f"{subdir_name} ディレクトリが見つかりません（スキップ）")
            continue
        
        # 復元先ディレクトリを作成
        source_dir.mkdir(parents=True, exist_ok=True)
        
        if files_to_copy is None:
            # 全てのファイルを復元
            for item in src_subdir.iterdir():
                if item.name == "profile.json":
                    continue
                try:
                    _copy_item(item, source_dir / item.name)
                    restored.append(f"{subdir_name}/{item.name}")
                except Exception as e:
                    _err(f"復元失敗 {item.name}: {e}")
        else:
            # 指定されたファイルのみ復元
            for fname in files_to_copy:
                src = src_subdir / fname
                dst = source_dir / fname
                if not src.exists():
                    _warn(f"{fname} が見つかりません（スキップ）")
                    continue
                try:
                    _copy_item(src, dst)
                    restored.append(f"{subdir_name}/{fname}")
                except Exception as e:
                    _err(f"復元失敗 {fname}: {e}")
    
    if restored:
        _ok(f"復元: {', '.join(restored)}")
        _ok(f"復元元: {pdir}")
        return True
    else:
        _err("復元できたファイルがありません")
        return False


# ──────────────────────────────────────────────────────────────────
# アクション
# ──────────────────────────────────────────────────────────────────

def action_add(agent_type: str):
    provider = PROVIDERS[agent_type]
    _section("プロファイル追加 / 更新")

    profiles = list_profiles(agent_type)
    if profiles:
        print(f"  既存: {', '.join(profiles)}")

    profile_name = _ask("プロファイル名（例: main / account2 / work）")
    if not profile_name:
        return
    if not all(c.isalnum() or c in "-_" for c in profile_name):
        _err("プロファイル名は英数字・ハイフン・アンダースコアのみ使用可")
        return

    if _pdir(agent_type, profile_name).exists():
        if not _confirm(f"'{profile_name}' は既に存在します。上書きしますか?"):
            return

    note = _ask("メモ（任意）")

    # ログインフローをスキップするか確認
    do_auth = _confirm("ログアウト→ログインを実行しますか?（現在の認証情報だけ保存する場合は N）")

    total_steps = (2 if do_auth else 0) + 1  # logout + login + save
    step = 1

    if do_auth:
        print(f"\n[{step}/{total_steps}] ログアウト中...")
        step += 1
        _do_logout(agent_type)

        print(f"\n[{step}/{total_steps}] ログイン中...")
        step += 1
        if not _do_login(agent_type):
            if not _confirm("ログインに問題がありました。それでも認証ファイルを保存しますか?"):
                return

    print(f"\n[{step}/{total_steps}] 認証情報を保存中...")
    if save_credentials(agent_type, profile_name):
        _save_meta(agent_type, profile_name, note)
        print()
        _ok(f"プロファイル '{profile_name}' 完了")
        _show_yaml_hint(agent_type)
    else:
        _err("保存に失敗しました")


def action_list(agent_type: str):
    provider = PROVIDERS[agent_type]
    _section(f"{provider['name']} プロファイル一覧")

    profiles = list_profiles(agent_type)
    if not profiles:
        print(f"  プロファイルなし  (保存先: {PROFILES_BASE / agent_type})")
        return

    for name in profiles:
        meta  = _load_meta(agent_type, name)
        pdir  = _pdir(agent_type, name)
        files = [
            str(f.relative_to(pdir))
            for f in pdir.rglob("*")
            if f.is_file() and f.name != "profile.json"
        ]
        note    = f"  # {meta['note']}" if meta.get("note") else ""
        updated = meta.get("updated", "?")[:10]
        print(f"  [{name}]  更新: {updated}  ファイル数: {len(files)}{note}")
        for fp in sorted(files)[:8]:
            print(f"           {fp}")
        if len(files) > 8:
            print(f"           ... 他 {len(files) - 8} 件")


def action_delete(agent_type: str):
    profiles = list_profiles(agent_type)
    if not profiles:
        print("  削除できるプロファイルがありません")
        return

    print(f"  プロファイル: {', '.join(profiles)}")
    name = _ask("削除するプロファイル名")
    if name not in profiles:
        _err(f"'{name}' は存在しません")
        return

    if _confirm(f"'{name}' を完全に削除しますか?"):
        shutil.rmtree(str(_pdir(agent_type, name)))
        _ok(f"'{name}' を削除しました")


def action_restore(agent_type: str):
    """プロファイルから認証情報を復元"""
    provider = PROVIDERS[agent_type]
    _section("プロファイル復元")
    
    profiles = list_profiles(agent_type)
    if not profiles:
        print(f"  復元できるプロファイルがありません")
        return
    
    print(f"  既存プロファイル: {', '.join(profiles)}")
    profile_name = _ask("復元するプロファイル名")
    
    if not profile_name:
        return
    
    if profile_name not in profiles:
        _err(f"'{profile_name}' は存在しません")
        return
    
    # メタ情報を表示
    meta = _load_meta(agent_type, profile_name)
    print(f"\n  プロファイル情報:")
    print(f"    名前:   {profile_name}")
    print(f"    作成:   {meta.get('created', '?')[:19]}")
    print(f"    更新:   {meta.get('updated', '?')[:19]}")
    if meta.get('note'):
        print(f"    メモ:   {meta['note']}")
    print()
    
    if not _confirm("このプロファイルを復元しますか?（既存の認証情報は上書きされます）"):
        return
    
    print(f"\n認証情報を復元中...")
    if restore_credentials(agent_type, profile_name):
        print()
        _ok(f"プロファイル '{profile_name}' を復元しました")
        
        # 認証状態を確認するヒント
        if agent_type == "github_cli":
            print("\n  認証確認: gh auth status")
        elif agent_type == "git":
            print("\n  設定確認: git config --global --list")
    else:
        _err("復元に失敗しました")


def _show_yaml_hint(agent_type: str):
    profiles = list_profiles(agent_type)
    if not profiles:
        return
    profile_lines = "\n".join(f"      - {p}" for p in profiles)
    print(f"""
  ── agents.yaml への設定例 ──
  {agent_type}:
    instances_per_profile: 1   # プロファイルごとのコンテナ数
    type: "{agent_type}"
    auth_profiles:
{profile_lines}
""")


# ──────────────────────────────────────────────────────────────────
# プロバイダメニュー / メインメニュー
# ──────────────────────────────────────────────────────────────────

def provider_menu(agent_type: str):
    provider = PROVIDERS[agent_type]
    while True:
        profiles = list_profiles(agent_type)
        _header(provider["name"])
        print(f"  登録プロファイル数: {len(profiles)}"
              + (f"  ({', '.join(profiles)})" if profiles else ""))
        print()
        print("  [1] プロファイル一覧")
        print("  [2] プロファイル追加 / 更新")
        print("  [3] プロファイル復元")
        print("  [4] プロファイル削除")
        print("  [0] 戻る")

        choice = _ask("選択")
        if   choice == "1": action_list(agent_type)
        elif choice == "2": action_add(agent_type)
        elif choice == "3": action_restore(agent_type)
        elif choice == "4": action_delete(agent_type)
        elif choice == "0": break
        else: _err("無効な選択です")


def main():
    _header("CTF Solver 認証プロファイル管理")
    print(f"  保存先: {PROFILES_BASE}")

    items = list(PROVIDERS.items())

    while True:
        print("\n  プロバイダを選択:")
        for i, (key, prov) in enumerate(items, 1):
            count = len(list_profiles(key))
            badge = f"({count}件)" if count else "(未登録)"
            print(f"  [{i}] {prov['name']}  {badge}")
        print("  [0] 終了")

        choice = _ask("選択")
        if choice == "0":
            print("  終了します")
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                provider_menu(items[idx][0])
            else:
                _err("番号が範囲外です")
        except ValueError:
            _err("数字を入力してください")


if __name__ == "__main__":
    main()
