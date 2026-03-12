"""
CTFd Relay Proxy - コンテナとCTFd間の安全なプロキシ

コンテナに CTFd URL・トークンを渡さず、必要な API だけを公開する。
フラグ提出、問題取得、ファイルダウンロード、ヒント取得を仲介し、
コスト付きヒントは自動でブロックする。

Endpoints:
  GET  /challenges              - 問題一覧（解答状況付き）
  GET  /challenges/<id>         - 問題詳細（説明文、ファイル、ヒント）
  POST /challenges/<id>/submit  - フラグ提出
  GET  /download/<path>         - ファイルダウンロード（プロキシ）
  GET  /status                  - 全体進捗
"""

import http.server
import json
import logging
import os
import re
import secrets
import ssl
import threading
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

logger = logging.getLogger(__name__)


def _make_handler(ctfd_url, ctfd_token, hints_config, relay_token, solved_tracker, shared_dir,
                  verify_ssl=False, only_ids=None, skip_ids=None, ctf_ended=False):
    """リクエストハンドラーを生成する（クロージャで共有状態を保持）。"""

    # SSL コンテキスト（再利用）
    _ssl_ctx = ssl.create_default_context()
    if not verify_ssl:
        _ssl_ctx.check_hostname = False
        _ssl_ctx.verify_mode = ssl.CERT_NONE

    # 作業中チャレンジの排他制御
    import threading as _th
    _claimed_lock = _th.Lock()
    _claimed: dict[int, list[str]] = {}  # {challenge_id: [agent_names]}

    # チャレンジフィルタ
    _only_ids: set[int] | None = only_ids
    _skip_ids: set[int] | None = skip_ids

    # config.yamlで指定されたCTF終了フラグ
    _ctf_ended_flag: bool = ctf_ended

    # チャレンジキャッシュ（ended時にAPIが空を返してもキャッシュから返す）
    _challenges_cache: list[dict] = []
    _challenges_cache_lock = _th.Lock()

    # ローカルsolve追跡ファイル（ended時のベンチマーク用）
    _local_solves_file = os.path.join(shared_dir, "local_solves.json") if shared_dir else None

    class _Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        # ── 共通ヘルパー ─────────────────────────────────────

        def _check_auth(self):
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {relay_token}":
                self.send_response(403)
                self.end_headers()
                return False
            return True

        def _send_json(self, data, status=200):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _ctfd_api(self, method, endpoint, data=None):
            """CTFd API を呼び出す。"""
            url = f"{ctfd_url}/api/v1/{endpoint.lstrip('/')}"
            headers = {
                "Authorization": f"Token {ctfd_token}",
                "Content-Type": "application/json",
            }
            body = json.dumps(data).encode() if data else None
            req = urllib.request.Request(
                url, data=body, headers=headers, method=method,
            )
            with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx) as resp:
                return json.loads(resp.read())

        def _ctfd_download(self, file_path):
            """CTFd からファイルをダウンロードする。"""
            url = f"{ctfd_url}/{file_path.lstrip('/')}"
            req = urllib.request.Request(
                url, headers={"Authorization": f"Token {ctfd_token}"},
            )
            with urllib.request.urlopen(req, timeout=120, context=_ssl_ctx) as resp:
                return resp.read()

        def _get_solved_ids(self):
            """自チーム/ユーザーの解答済み問題 ID セットを取得。"""
            for ep in ("/teams/me/solves", "/users/me/solves"):
                try:
                    data = self._ctfd_api("GET", ep)
                    solves = data.get("data", [])
                    return {int(s["challenge_id"]) for s in solves if "challenge_id" in s}
                except Exception:
                    continue
            return set()

        def _write_solved_file(self):
            """共有ディレクトリに solved_ids.txt を書き出す。"""
            if not shared_dir:
                return
            try:
                path = os.path.join(shared_dir, "solved_ids.txt")
                ids = sorted(solved_tracker["solved_ids"])
                with open(path, "w") as f:
                    for cid in ids:
                        f.write(f"{cid}\n")
            except Exception as e:
                logger.debug("solved_ids.txt write failed: %s", e)

        def _get_free_hints(self, challenge_id):
            """無料ヒントのみ取得する（コスト付きはブロック）。"""
            if not hints_config.get("enabled", False):
                return []
            allow_cost = hints_config.get("allow_cost_hints", False)
            max_cost = hints_config.get("max_cost", 0)
            try:
                data = self._ctfd_api(
                    "GET", f"/hints?challenge_id={challenge_id}",
                )
                hints_meta = data.get("data", [])
            except Exception:
                return []
            hints = []
            for h in hints_meta:
                cost = h.get("cost", 0)
                if cost > 0 and (not allow_cost or cost > max_cost):
                    continue
                try:
                    detail = self._ctfd_api("GET", f"/hints/{h['id']}")
                    content = detail.get("data", {}).get("content", "")
                    if content:
                        hints.append(content)
                except Exception:
                    continue
            return hints

        # ── クロスエージェント情報集約 ──────────────────────────

        def _aggregate_wrong_flags(self, challenge_id):
            """全エージェントの wrong_flags から該当チャレンジの不正解フラグを集約。"""
            wrong = set()
            ws_root = os.path.join(os.getcwd(), "workspace")
            if not os.path.isdir(ws_root):
                return sorted(wrong)
            for agent_dir in os.listdir(ws_root):
                if agent_dir == "shared":
                    continue
                wf = os.path.join(ws_root, agent_dir, "state", "wrong_flags.txt")
                if os.path.isfile(wf):
                    try:
                        with open(wf, "r") as f:
                            for line in f:
                                line = line.strip()
                                if line.startswith(f"{challenge_id}:"):
                                    wrong.add(line.split(":", 1)[1])
                    except Exception:
                        pass
            return sorted(wrong)

        def _aggregate_notes(self, challenge_id):
            """全エージェントの notes.txt を集約。"""
            notes = []
            ws_root = os.path.join(os.getcwd(), "workspace")
            if not os.path.isdir(ws_root):
                return notes
            for agent_dir in sorted(os.listdir(ws_root)):
                if agent_dir == "shared":
                    continue
                nf = os.path.join(ws_root, agent_dir, "challenges", str(challenge_id), "notes.txt")
                if os.path.isfile(nf):
                    try:
                        with open(nf, "r") as f:
                            content = f.read().strip()
                        if content:
                            notes.append({"agent": agent_dir, "notes": content})
                    except Exception:
                        pass
            return notes

        # ── ルーティング ─────────────────────────────────────

        def do_GET(self):
            if not self._check_auth():
                return
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path.rstrip("/")

            if path == "/challenges":
                self._handle_list_challenges()
            elif re.match(r"^/challenges/(\d+)$", path):
                cid = int(re.match(r"^/challenges/(\d+)$", path).group(1))
                self._handle_get_challenge(cid)
            elif path.startswith("/download/"):
                # /download/<ctfd_file_path> → CTFd からプロキシ
                ctfd_path = path[len("/download/"):]
                if parsed.query:
                    ctfd_path += "?" + parsed.query
                self._handle_download(ctfd_path)
            elif path == "/status":
                self._handle_status()
            elif path == "/claimed":
                with _claimed_lock:
                    self._send_json({"claimed": dict(_claimed)})
            elif re.match(r"^/wrong_flags/(\d+)$", path):
                cid = int(re.match(r"^/wrong_flags/(\d+)$", path).group(1))
                self._send_json({"challenge_id": cid, "wrong_flags": self._aggregate_wrong_flags(cid)})
            elif re.match(r"^/notes/(\d+)$", path):
                cid = int(re.match(r"^/notes/(\d+)$", path).group(1))
                self._send_json({"challenge_id": cid, "notes": self._aggregate_notes(cid)})
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            if not self._check_auth():
                return
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path.rstrip("/")
            m = re.match(r"^/challenges/(\d+)/submit$", path)
            if m:
                self._handle_submit(int(m.group(1)))
                return

            # /claim/<id> — チャレンジを作業予約（排他制御）
            m = re.match(r"^/claim/(\d+)$", path)
            if m:
                self._handle_claim(int(m.group(1)))
                return

            # /release/<id> — 作業予約を解除
            m = re.match(r"^/release/(\d+)$", path)
            if m:
                self._handle_release(int(m.group(1)))
                return

            self.send_response(403)
            self.end_headers()

        # ── ハンドラー実装 ───────────────────────────────────

        def _load_local_solves(self):
            """ローカルに記録したsolve情報を読み込む。"""
            if not _local_solves_file or not os.path.exists(_local_solves_file):
                return {}
            try:
                with open(_local_solves_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}

        def _save_local_solve(self, challenge_id, flag, verified=False):
            """ローカルにsolveを記録する。"""
            if not _local_solves_file:
                return
            try:
                data = self._load_local_solves()
                data[str(challenge_id)] = {"flag": flag, "verified": verified}
                with open(_local_solves_file, "w") as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                logger.debug("local_solves.json write failed: %s", e)

        def _get_solved_ids_combined(self):
            """CTFd API + ローカル記録を統合したsolve IDセット。"""
            ids = self._get_solved_ids()
            local = self._load_local_solves()
            ids.update(int(k) for k in local)
            return ids

        def _check_ctf_active(self):
            """CTFが進行中か確認（情報提供用、ブロックはしない）。"""
            if _ctf_ended_flag:
                return False, "CTF ended (set in config.yaml)"
            try:
                data = self._ctfd_api("GET", "/challenges")
                if isinstance(data, dict) and data.get("data") is not None:
                    return True, None
                msg = data.get("message", "") if isinstance(data, dict) else ""
                return False, msg or "CTF is not active"
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    return False, "CTF is not accessible (403 — likely ended or not started)"
                raise
            except Exception:
                return True, None

        def _handle_list_challenges(self):
            try:
                data = self._ctfd_api("GET", "/challenges")
                challenges = data.get("data", [])
            except Exception as e:
                challenges = []
                if not _ctf_ended_flag:
                    logger.error("challenges 一覧取得エラー: %s", e)

            # キャッシュ更新: 取得できたらキャッシュ、空ならキャッシュから復元
            with _challenges_cache_lock:
                if challenges:
                    _challenges_cache.clear()
                    _challenges_cache.extend(challenges)
                elif _challenges_cache:
                    challenges = list(_challenges_cache)

            try:
                solved_ids = self._get_solved_ids_combined()
                solved_tracker["solved_ids"] = solved_ids
                self._write_solved_file()
                result = []
                for c in challenges:
                    cid = c.get("id")
                    if _only_ids is not None and cid not in _only_ids:
                        continue
                    if _skip_ids is not None and cid in _skip_ids:
                        continue
                    with _claimed_lock:
                        claimed_by = _claimed.get(cid, [])
                    result.append({
                        "id": cid,
                        "name": c.get("name", ""),
                        "category": c.get("category", ""),
                        "value": c.get("value", 0),
                        "solves": c.get("solves", 0),
                        "solved_by_me": cid in solved_ids,
                        "claimed_by": claimed_by,  # now a list of agent names
                    })
                resp = {
                    "challenges": result,
                    "total": len(result),
                    "solved": len(solved_ids),
                }
                if _ctf_ended_flag:
                    resp["ctf_ended"] = True
                self._send_json(resp)
            except Exception as e:
                logger.error("challenges 一覧取得エラー: %s", e)
                self._send_json({"error": str(e)}, 502)

        def _handle_get_challenge(self, challenge_id):
            try:
                data = self._ctfd_api("GET", f"/challenges/{challenge_id}")
                detail = data.get("data", {})
                files = []
                for f in detail.get("files", []):
                    fname = f.split("/")[-1].split("?")[0]
                    files.append({"name": fname, "path": f})
                hints = self._get_free_hints(challenge_id)
                solved_ids = self._get_solved_ids_combined()
                self._send_json({
                    "id": detail.get("id"),
                    "name": detail.get("name", ""),
                    "category": detail.get("category", ""),
                    "value": detail.get("value", 0),
                    "description": detail.get("description", ""),
                    "files": files,
                    "hints": hints,
                    "solves": detail.get("solves", 0),
                    "solved_by_me": detail.get("id") in solved_ids,
                    "connection_info": detail.get("connection_info", ""),
                })
            except Exception as e:
                logger.error("challenge 詳細取得エラー (id=%d): %s", challenge_id, e)
                self._send_json({"error": str(e)}, 502)

        def _handle_claim(self, challenge_id):
            """チャレンジの作業予約。複数エージェントでの協力作業を許可。"""
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}
            agent_name = body.get("agent", "unknown")
            with _claimed_lock:
                if challenge_id in solved_tracker["solved_ids"]:
                    self._send_json({"status": "already_solved"})
                    return
                # 複数エージェント許可: リストに追加
                if challenge_id not in _claimed:
                    _claimed[challenge_id] = []
                if agent_name not in _claimed[challenge_id]:
                    _claimed[challenge_id].append(agent_name)
                # claimed_ids.txt を更新
                self._write_claimed_file()
            self._send_json({"status": "ok", "agents": _claimed[challenge_id]})

        def _handle_release(self, challenge_id):
            """チャレンジの作業予約を解除。"""
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}
            agent_name = body.get("agent", "unknown")
            with _claimed_lock:
                if challenge_id in _claimed:
                    if agent_name in _claimed[challenge_id]:
                        _claimed[challenge_id].remove(agent_name)
                    if not _claimed[challenge_id]:  # リストが空になったら削除
                        _claimed.pop(challenge_id)
                self._write_claimed_file()
            self._send_json({"status": "ok"})

        def _write_claimed_file(self):
            """共有ディレクトリに claimed_ids.txt を書き出す。"""
            if not shared_dir:
                return
            try:
                path = os.path.join(shared_dir, "claimed_ids.txt")
                with open(path, "w") as f:
                    for cid, agents in sorted(_claimed.items()):
                        # 複数エージェントをカンマ区切りで保存
                        f.write(f"{cid}:{','.join(agents)}\n")
            except Exception:
                pass

        def _handle_download(self, file_path):
            # パストラバーサル防止（先頭スラッシュは除去）
            file_path = file_path.lstrip("/")
            if not file_path or ".." in file_path:
                self.send_response(403)
                self.end_headers()
                return
            try:
                data = self._ctfd_download(file_path)
                fname = file_path.split("/")[-1].split("?")[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header(
                    "Content-Disposition", f'attachment; filename="{fname}"',
                )
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                logger.error("ファイルダウンロードエラー (%s): %s", file_path, e)
                self.send_response(502)
                self.end_headers()

        def _handle_submit(self, challenge_id):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                flag = json.loads(body).get("flag", "")
            except Exception:
                self.send_response(400)
                self.end_headers()
                return
            if not flag:
                self.send_response(400)
                self.end_headers()
                return
            try:
                result = self._ctfd_api("POST", "/challenges/attempt", {
                    "challenge_id": challenge_id,
                    "submission": flag,
                })
                status = result.get("data", {}).get("status", "")
                if status in ("correct", "already_solved"):
                    solved_tracker["solved_ids"].add(challenge_id)
                    self._write_solved_file()
                    self._save_local_solve(challenge_id, flag, verified=True)
                    with _claimed_lock:
                        _claimed.pop(challenge_id, None)
                        self._write_claimed_file()
                    logger.info(
                        "正解: challenge_id=%d, flag=%s", challenge_id, flag,
                    )
                self._send_json(result)
            except Exception as e:
                # CTF終了時: CTFdが提出を拒否しても、ローカルに未検証フラグとして記録
                if _ctf_ended_flag:
                    self._save_local_solve(challenge_id, flag, verified=False)
                    solved_tracker["solved_ids"].add(challenge_id)
                    self._write_solved_file()
                    with _claimed_lock:
                        _claimed.pop(challenge_id, None)
                        self._write_claimed_file()
                    logger.info(
                        "ローカル記録(未検証): challenge_id=%d, flag=%s", challenge_id, flag,
                    )
                    self._send_json({
                        "success": True,
                        "data": {
                            "status": "correct",
                            "message": "Recorded locally (CTF ended, unverified)",
                        },
                    })
                    return
                logger.error("フラグ提出エラー (id=%d): %s", challenge_id, e)
                self._send_json({"error": str(e)}, 502)

        def _handle_status(self):
            try:
                solved_ids = self._get_solved_ids_combined()
                solved_tracker["solved_ids"] = solved_ids
                active, _ = self._check_ctf_active()
                try:
                    data = self._ctfd_api("GET", "/challenges")
                    total = len(data.get("data", []))
                except Exception:
                    total = 0
                # APIが空を返してもキャッシュがあればそちらを使う
                if total == 0:
                    with _challenges_cache_lock:
                        total = len(_challenges_cache)
                self._send_json({
                    "total": total,
                    "solved": len(solved_ids),
                    "solved_ids": sorted(solved_ids),
                    "ctf_ended": not active,
                })
            except Exception as e:
                self._send_json({"error": str(e)}, 502)

    return _Handler


class CTFdRelay:
    """
    CTFd リレープロキシ。

    コンテナには RELAY_URL と RELAY_TOKEN だけを渡し、
    CTFd URL やトークンは一切露出しない。
    スレッドセーフな ThreadingHTTPServer を使用する。
    """

    def __init__(self, ctfd_url: str, ctfd_token: str, hints_config: dict | None = None,
                 shared_dir: str | None = None, verify_ssl: bool = False,
                 only_challenge_ids: set[int] | None = None,
                 skip_challenge_ids: set[int] | None = None,
                 ctf_ended: bool = False):
        self.relay_token: str = secrets.token_hex(32)
        self._solved_tracker: dict = {"solved_ids": set()}
        self._shared_dir = shared_dir
        handler = _make_handler(
            ctfd_url, ctfd_token,
            hints_config or {},
            self.relay_token,
            self._solved_tracker,
            shared_dir,
            verify_ssl=verify_ssl,
            only_ids=only_challenge_ids,
            skip_ids=skip_challenge_ids,
            ctf_ended=ctf_ended,
        )
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port: int = self._server.server_address[1]
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True,
        )

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def solved_ids(self) -> set:
        return self._solved_tracker["solved_ids"]

    def start(self) -> "CTFdRelay":
        self._thread.start()
        logger.info("CTFd Relay 起動: %s", self.url)
        # キャッシュウォームアップ（起動時に全チャレンジを取得してキャッシュ）
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self.url}/challenges",
                headers={"Authorization": f"Bearer {self.relay_token}"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            n = len(data.get("challenges", []))
            logger.info("チャレンジキャッシュ: %d 問取得", n)
        except Exception as e:
            logger.warning("キャッシュウォームアップ失敗: %s", e)
        return self

    def stop(self):
        self._server.shutdown()
        logger.info("CTFd Relay 停止")
