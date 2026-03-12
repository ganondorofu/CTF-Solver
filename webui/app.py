"""
CTF Solver WebUI (v3: Enhanced Dashboard)

FastAPI + WebSocket でリアルタイムダッシュボードを提供する。
v3: 詳細情報表示、カテゴリ分析、提出履歴、アクティビティフィード対応。
"""

import asyncio
import json
import logging
import re
import time
import urllib.request
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

app = FastAPI(title="CTF Solver Dashboard")

# ── 設定（起動時に main.py から注入される） ──────────────────
BASE_DIR = Path(__file__).parent.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
LOGS_DIR = BASE_DIR / "logs"
SHARED_DIR = WORKSPACE_DIR / "shared"

_relay_url: str = ""
_relay_token: str = ""
_container_infos: list = []
_start_time: float = 0.0


def configure(relay_url: str, relay_token: str, container_infos: list):
    global _relay_url, _relay_token, _container_infos, _start_time
    _relay_url = relay_url
    _relay_token = relay_token
    _container_infos = container_infos
    _start_time = time.time()


# ── Relay helpers ────────────────────────────────────────────

def _relay_get(path: str, timeout: int = 5):
    if not _relay_url:
        return None
    try:
        req = urllib.request.Request(
            f"{_relay_url}{path}",
            headers={"Authorization": f"Bearer {_relay_token}"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


# ── Data ─────────────────────────────────────────────────────

def _read_solved_ids() -> set[int]:
    p = SHARED_DIR / "solved_ids.txt"
    if not p.exists():
        return set()
    try:
        return {int(line.strip()) for line in p.read_text().splitlines() if line.strip()}
    except Exception:
        return set()


def _read_claimed() -> dict:
    p = SHARED_DIR / "claimed_ids.txt"
    if not p.exists():
        return {}
    try:
        result = {}
        for line in p.read_text().splitlines():
            if ":" in line:
                cid, agents_str = line.strip().split(":", 1)
                # カンマ区切りでエージェントのリストを取得
                result[int(cid)] = agents_str.split(",")
        return result
    except Exception:
        return {}


def _read_local_solves() -> dict:
    p = SHARED_DIR / "local_solves.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _safe_name_to_agent(safe: str) -> str:
    """Reverse safe_name (e.g. codex_cli_1) back to agent name (codex_cli#1)."""
    m = re.match(r'^(.+)_(\d+)$', safe)
    return f"{m.group(1)}#{m.group(2)}" if m else safe


def _read_wrong_flags() -> list[dict]:
    """Read flag submission history from agent logs."""
    results = []
    try:
        for log_path in LOGS_DIR.glob("*.log"):
            agent = _safe_name_to_agent(log_path.stem)
            try:
                text = log_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for m in re.finditer(
                r"^FLAG_CONFIRMED_INCORRECT:\s*(.+?)(?:\s*\(status:.*?\))?\s*$",
                text, re.MULTILINE,
            ):
                flag = m.group(1).strip()
                if flag:
                    results.append({"agent": agent, "flag": flag, "status": "incorrect"})
            for m in re.finditer(
                r"^FLAG_CONFIRMED_CORRECT:\s*(.+?)$", text, re.MULTILINE,
            ):
                flag = m.group(1).strip()
                if flag:
                    results.append({"agent": agent, "flag": flag, "status": "correct"})
    except Exception:
        pass
    return results


_challenges_cache: list[dict] = []
_challenges_cache_time: float = 0


def get_challenges() -> list[dict]:
    global _challenges_cache, _challenges_cache_time
    now = time.time()
    if now - _challenges_cache_time > 5:
        data = _relay_get("/challenges")
        if data and data.get("challenges"):
            _challenges_cache = data["challenges"]
            _challenges_cache_time = now
    return _challenges_cache


def get_agents_status() -> list[dict]:
    claimed = _read_claimed()
    claimed_by_agent: dict[str, list[int]] = {}
    for cid, agents in claimed.items():
        # agents is now a list
        for agent in agents:
            claimed_by_agent.setdefault(agent, []).append(cid)
    result = []
    for info in _container_infos:
        name = info["agent_name"]
        agent_type = info["agent_cfg"].get("type", name)
        model = info["agent_cfg"].get("model", "")
        status = "unknown"
        try:
            info["container"].reload()
            status = info["container"].status
        except Exception:
            status = "exited"
        result.append({
            "name": name,
            "type": agent_type,
            "model": model,
            "status": status,
            "container_id": info["container"].short_id,
            "working_on": claimed_by_agent.get(name, []),
        })
    return result


def get_overview() -> dict:
    challenges = get_challenges()
    solved_ids = _read_solved_ids()
    status = _relay_get("/status") or {}
    total = status.get("total", len(challenges)) or len(challenges)
    solved = max(len(solved_ids), status.get("solved", 0))
    total_points = sum(c.get("value", 0) for c in challenges)
    solved_points = sum(c.get("value", 0) for c in challenges if c.get("id") in solved_ids)
    agents = get_agents_status()
    running_agents = sum(1 for a in agents if a["status"] == "running")

    # Category breakdown
    cats: dict[str, dict] = {}
    for c in challenges:
        cat = c.get("category", "Other") or "Other"
        if cat not in cats:
            cats[cat] = {"total": 0, "solved": 0, "points": 0, "solved_points": 0}
        cats[cat]["total"] += 1
        cats[cat]["points"] += c.get("value", 0)
        if c.get("id") in solved_ids:
            cats[cat]["solved"] += 1
            cats[cat]["solved_points"] += c.get("value", 0)

    elapsed = int(time.time() - _start_time) if _start_time else 0

    return {
        "total": total,
        "solved": solved,
        "remaining": max(0, total - solved),
        "total_points": total_points,
        "solved_points": solved_points,
        "agents": agents,
        "running_agents": running_agents,
        "ctf_ended": status.get("ctf_ended", False),
        "categories": cats,
        "elapsed_seconds": elapsed,
    }


def _enrich_challenges(challenges: list[dict]) -> list[dict]:
    solved_ids = _read_solved_ids()
    claimed = _read_claimed()
    for c in challenges:
        c["solved_by_me"] = c.get("id") in solved_ids
        c["claimed_by"] = claimed.get(c.get("id"))
    return challenges


def get_agent_log(agent_name: str, tail: int = 500) -> str:
    safe_name = agent_name.replace("#", "_")
    for p in (LOGS_DIR / f"{safe_name}.log", WORKSPACE_DIR / safe_name / "agent.log"):
        if p.exists():
            try:
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
                return "\n".join(lines[-tail:])
            except Exception:
                continue
    return ""


_activity_cache: list[dict] = []
_activity_cache_time: float = 0


def _get_activity_feed(limit: int = 50) -> list[dict]:
    """Extract recent activity from agent logs (cached 5s)."""
    global _activity_cache, _activity_cache_time
    now = time.time()
    if now - _activity_cache_time < 5 and _activity_cache:
        return _activity_cache[:limit]

    events = []
    try:
        for log_path in LOGS_DIR.glob("*.log"):
            agent = _safe_name_to_agent(log_path.stem)
            try:
                lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception:
                continue
            last_ts = ""
            for line in lines:
                ts_match = re.match(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})", line)
                if ts_match:
                    last_ts = ts_match.group(1)
                stripped = line.lstrip()
                if stripped.startswith("FLAG_CONFIRMED_CORRECT:"):
                    flag = stripped.split(":", 1)[-1].strip().split()[0] if ":" in stripped else ""
                    events.append({"ts": last_ts, "agent": agent, "type": "solve", "msg": f"Solved! {flag}"})
                elif stripped.startswith("FLAG_CONFIRMED_INCORRECT:"):
                    flag = stripped.split(":", 1)[-1].strip().split("(")[0].strip()
                    events.append({"ts": last_ts, "agent": agent, "type": "wrong", "msg": f"Wrong: {flag}"})
                elif "=== Challenge" in line and "ready ===" in line:
                    cid_m = re.search(r"Challenge (\d+) ready", line)
                    if cid_m:
                        events.append({"ts": last_ts, "agent": agent, "type": "start", "msg": f"Challenge #{cid_m.group(1)} ready"})
    except Exception:
        pass
    events.sort(key=lambda e: e.get("ts", ""), reverse=True)
    _activity_cache = events
    _activity_cache_time = now
    return events[:limit]


# ── REST API ────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/overview")
async def api_overview():
    return get_overview()


@app.get("/api/challenges")
async def api_challenges():
    return _enrich_challenges(get_challenges())


@app.get("/api/challenges/{challenge_id}")
async def api_challenge_detail(challenge_id: int):
    data = _relay_get(f"/challenges/{challenge_id}", timeout=10)
    if data and "error" not in data:
        return data
    return {"error": "Challenge not found or relay unavailable"}


@app.get("/api/agents")
async def api_agents():
    return get_agents_status()


@app.get("/api/agents/{agent_name}/log")
async def api_agent_log(agent_name: str, tail: int = 500):
    return {"log": get_agent_log(agent_name, tail)}


@app.get("/api/activity")
async def api_activity(limit: int = 50):
    return _get_activity_feed(limit)


@app.get("/api/submissions")
async def api_submissions():
    return _read_wrong_flags()


@app.get("/api/claimed")
async def api_claimed():
    return _read_claimed()


# ── WebSocket（リアルタイム更新） ───────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in self.active:
                self.active.remove(ws)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        overview = get_overview()
        challenges = _enrich_challenges(get_challenges())
        activity = _get_activity_feed(30)
        await ws.send_json({
            "type": "init",
            "overview": overview,
            "challenges": challenges,
            "activity": activity,
        })
        while True:
            await asyncio.sleep(3)
            overview = get_overview()
            challenges = _enrich_challenges(get_challenges())
            activity = _get_activity_feed(30)
            await ws.send_json({
                "type": "update",
                "overview": overview,
                "challenges": challenges,
                "activity": activity,
            })
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)


@app.websocket("/ws/log/{agent_name}")
async def websocket_agent_log(ws: WebSocket, agent_name: str):
    await ws.accept()
    safe_name = agent_name.replace("#", "_")
    log_path = LOGS_DIR / f"{safe_name}.log"
    last_size = 0
    try:
        if log_path.exists():
            content = log_path.read_text(encoding="utf-8", errors="replace")
            await ws.send_json({"type": "log", "content": content})
            last_size = log_path.stat().st_size
        while True:
            await asyncio.sleep(1)
            if log_path.exists():
                cur_size = log_path.stat().st_size
                if cur_size > last_size:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(last_size)
                        new_content = f.read()
                    await ws.send_json({"type": "log_append", "content": new_content})
                    last_size = cur_size
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
