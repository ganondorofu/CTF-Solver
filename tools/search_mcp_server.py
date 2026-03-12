#!/usr/bin/env python3
"""
CTF Web Search MCP Server

Claude Codeエージェント（claude_zai / kimi）向けにweb_searchツールを提供する。
DuckDuckGoを使用するためAPIキー不要。

起動方法:
    cd CTF-Solver
    source venv/bin/activate
    python tools/search_mcp_server.py          # デフォルト: localhost:4444
    python tools/search_mcp_server.py 4444     # ポート指定

~/.claude/settings.json に以下を追加してエージェントに自動接続:
    {
      "mcpServers": {
        "web-search": {
          "url": "http://localhost:4444/sse"
        }
      }
    }
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    logger.error("mcp パッケージが不足: %s", e)
    sys.exit(1)

try:
    from duckduckgo_search import DDGS
except ImportError:
    logger.error("duckduckgo-search / ddgs パッケージが不足です")
    logger.error("pip install ddgs を実行してください")
    sys.exit(1)

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4444

mcp = FastMCP("CTF Web Search", port=PORT)


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo.

    Use this tool to look up:
    - CVE details, exploit information
    - Historical malware / attack tool names
    - Cryptographic algorithms or protocols
    - CTF-related knowledge and writeups
    - Any information needed to solve the challenge

    Args:
        query: Search query string (English queries often give better results)
        max_results: Number of results to return (default 5, max 10)

    Returns:
        Search results with title, URL, and snippet for each result
    """
    max_results = min(max_results, 10)
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results, region="wt-wt"))
        if not results:
            return "No results found. Try a different query."

        output = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            url = r.get("href", "No URL")
            body = r.get("body", "No description")[:500]
            output.append(f"{i}. **{title}**\n   URL: {url}\n   {body}")
        return "\n\n".join(output)

    except Exception as e:
        logger.error("web_search error: %s", e)
        return f"Search failed: {e}"


@mcp.tool()
def fetch_page(url: str, max_chars: int = 3000) -> str:
    """
    Fetch and return the text content of a web page.

    Use this to read the full content of a URL found via web_search.

    Args:
        url: URL to fetch
        max_chars: Maximum characters to return (default 3000)

    Returns:
        Page content as plain text
    """
    try:
        import urllib.request
        import html
        import re

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; CTF-Agent/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        # HTMLタグを除去してテキスト抽出
        raw = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
        raw = re.sub(r"<style[^>]*>.*?</style>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
        raw = re.sub(r"<[^>]+>", " ", raw)
        raw = html.unescape(raw)
        raw = re.sub(r"\s+", " ", raw).strip()
        return raw[:max_chars]

    except Exception as e:
        return f"Failed to fetch {url}: {e}"


if __name__ == "__main__":
    logger.info("CTF Web Search MCP Server 起動中 (port=%d)...", PORT)
    logger.info("エージェントは web_search / fetch_page ツールが使用可能になります")
    mcp.run(transport="sse")
