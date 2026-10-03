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
from linkdigest.tool import DIGEST_URL_TOOL


@pytest.mark.live
def test_live_tools_list_matches_the_bundled_tool():
    proxy = StdioProxy(api_key=None, mcp_url="https://linkdigest.dev/mcp", log=lambda line: None)
    status, reply = proxy._remote("tools/list", None, 1, with_key=False, timeout=30)

    assert status == 200, reply
    tools = reply["result"]["tools"]
    assert [t["name"] for t in tools] == ["digest_url"]
    assert tools[0] == DIGEST_URL_TOOL, "the hosted tool changed: update src/linkdigest/tool.py"
