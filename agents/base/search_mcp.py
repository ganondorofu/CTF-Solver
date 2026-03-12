#!/usr/bin/env python3
"""
Web search MCP server (stdlib only, no pip install required)

GitHub Copilot CLI から stdio 経由で起動される MCP サーバー。
DuckDuckGo を使ったウェブ検索を web_search ツールとして提供する。
"""

import json
import re
import sys
import urllib.parse
import urllib.request

# ── 検索ロジック ────────────────────────────────────────────────────────────

def _clean_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    s = s.replace("&quot;", '"').replace("&#x27;", "'").replace("&nbsp;", " ")
    return " ".join(s.split())


def _ddg_instant(query: str, n: int) -> list[str]:
    """DuckDuckGo Instant Answer API（構造化データ）"""
    url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode({
        "q": query, "format": "json", "no_html": "1", "skip_disambig": "1",
    })
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read())

    results = []
    if data.get("AbstractText"):
        results.append(
            f"**{data.get('Heading', 'Summary')}**\n"
            f"{data['AbstractText'][:600]}\n"
            f"URL: {data.get('AbstractURL', '')}"
        )
    for topic in data.get("RelatedTopics", [])[:n]:
        if isinstance(topic, dict) and topic.get("Text"):
            results.append(f"- {topic['Text'][:300]}\n  {topic.get('FirstURL', '')}")
    return results


def _ddg_html(query: str, n: int) -> list[str]:
    """DuckDuckGo HTML 検索（フォールバック）"""
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        html = r.read().decode("utf-8", errors="replace")

    titles   = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)

    results = []
    for i in range(min(n, len(titles))):
        title = _clean_html(titles[i])
        snip  = _clean_html(snippets[i]) if i < len(snippets) else ""
        if title:
            results.append(f"{i+1}. **{title}**\n   {snip[:400]}")
    return results


def web_search(query: str, max_results: int = 5) -> str:
    """DuckDuckGo でウェブ検索し、結果テキストを返す"""
    try:
        results = _ddg_instant(query, max_results)
        if results:
            return "\n\n".join(results)
    except Exception:
        pass

    try:
        results = _ddg_html(query, max_results)
        if results:
            return "\n\n".join(results)
    except Exception as e:
        return f"Search failed: {e}"

    return "No results found. Try rephrasing the query in English."


# ── MCP プロトコル（JSON-RPC 2.0 over stdio）──────────────────────────────

TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Search the web using DuckDuckGo. Use for:\n"
            "- Historical attack tool / malware names from clues in problems\n"
            "- CVE details, exploit information, security research\n"
            "- CTF writeups and solution hints\n"
            "- Cryptographic algorithms, protocols, vulnerabilities\n"
            "Tip: English queries often give better results."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (English preferred)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    }
]


def _send(msg_id, result):
    if msg_id is not None:
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}) + "\n")
        sys.stdout.flush()


def main():
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = msg.get("method", "")
        mid    = msg.get("id")

        if method == "initialize":
            _send(mid, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ddg-search", "version": "1.0"},
            })

        elif method in ("notifications/initialized", "initialized"):
            pass  # 通知には返信不要

        elif method == "tools/list":
            _send(mid, {"tools": TOOLS})

        elif method == "tools/call":
            params    = msg.get("params", {})
            tool_name = params.get("name", "")
            args      = params.get("arguments", {})

            if tool_name == "web_search":
                query   = args.get("query", "")
                max_r   = int(args.get("max_results", 5))
                text    = web_search(query, max_r)
                _send(mid, {"content": [{"type": "text", "text": text}]})
            else:
                _send(mid, {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}]})


if __name__ == "__main__":
    main()
