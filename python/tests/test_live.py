"""The one test that touches the real service.

It calls tools/list on https://linkdigest.dev/mcp with no API key — the only
method the hosted server answers without one — so it costs nothing and needs
no secret. It checks two things: the real transport and parsing work against
the real server, and the bundled copy of the tool (tool.py) still matches the
live one word for word.

Offline? Run `pytest -m "not live"`.
"""

from __future__ import annotations

import pytest

from linkdigest.mcp_server import StdioProxy
from linkdigest.tool import BUNDLED_TOOLS


@pytest.mark.live
def test_live_tools_list_matches_the_bundled_tools():
    proxy = StdioProxy(api_key=None, mcp_url="https://linkdigest.dev/mcp", log=lambda line: None)
    status, reply = proxy._remote("tools/list", None, 1, with_key=False, timeout=30)

    assert status == 200, reply
    tools = reply["result"]["tools"]
    assert tools == BUNDLED_TOOLS, "the hosted tools changed: update src/linkdigest/tool.py from the live tools/list"


@pytest.mark.live
def test_live_short_link_is_resolved_by_its_redirect():
    # linkdigest.links: one HEAD (or GET) to b23.tv, its Location read, nothing else fetched.
    from linkdigest.links import resolve

    r = resolve("https://b23.tv/BV1stVH66E6G")
    assert r.platform == "bilibili" and r.post_id == "BV1stVH66E6G" and r.hops >= 1
    assert r.canonical_url == "https://www.bilibili.com/video/BV1stVH66E6G/"
