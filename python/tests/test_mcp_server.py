from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from conftest import FakeTransport, jresp, tresp
from linkdigest.errors import NetworkError
from linkdigest.mcp_server import SUPPORTED_PROTOCOL_VERSIONS, StdioProxy, serve
from linkdigest.tool import DIGEST_URL_TOOL

REMOTE = "https://linkdigest.dev/mcp"
TOOL_TEXT = {"content": [{"type": "text", "text": "# 标题\n\n逐字稿…"}]}


def proxy(fake: FakeTransport, key: str | None = "ld_live_mcp") -> StdioProxy:
    return StdioProxy(api_key=key, mcp_url=REMOTE, transport=fake, log=lambda line: None)


def call(id_, url="https://v.douyin.com/abc/", **args):
    return {
        "jsonrpc": "2.0",
        "id": id_,
        "method": "tools/call",
        "params": {"name": "digest_url", "arguments": {"url": url, **args}},
    }


# -- local methods: no network ---------------------------------------------


@pytest.mark.parametrize("requested", ["2024-11-05", "2025-03-26", "2025-06-18"])
def test_initialize_echoes_a_supported_version_without_network(requested):
    fake = FakeTransport()
    r = proxy(fake).handle({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": requested}})
    assert r["result"]["protocolVersion"] == requested
    assert r["result"]["capabilities"] == {"tools": {"listChanged": False}}
    assert r["result"]["serverInfo"]["name"] == "linkdigest"
    assert "digest_url" in r["result"]["instructions"]
    assert fake.requests == []


def test_initialize_offers_the_newest_version_for_an_unknown_one():
    r = proxy(FakeTransport()).handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "1999-01-01"}})
    assert r["result"]["protocolVersion"] == SUPPORTED_PROTOCOL_VERSIONS[0]


def test_notifications_and_stray_responses_get_no_reply():
    p = proxy(FakeTransport())
    assert p.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert p.handle({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 3}}) is None
    assert p.handle({"jsonrpc": "2.0", "id": 9, "result": {}}) is None


def test_ping_and_unknown_methods():
    p = proxy(FakeTransport())
    assert p.handle({"jsonrpc": "2.0", "id": "a", "method": "ping"}) == {"jsonrpc": "2.0", "id": "a", "result": {}}
    r = p.handle({"jsonrpc": "2.0", "id": 2, "method": "resources/list"})
    assert r["error"]["code"] == -32601
    assert p.handle("nonsense")["error"]["code"] == -32600


# -- tools/list --------------------------------------------------------------


def test_tools_list_relays_the_live_list_without_sending_the_key():
    live = {"tools": [{**DIGEST_URL_TOOL, "description": "newer wording"}]}
    fake = FakeTransport(jresp(200, {"jsonrpc": "2.0", "id": 5, "result": live}))
    r = proxy(fake).handle({"jsonrpc": "2.0", "id": 5, "method": "tools/list"})
    assert r == {"jsonrpc": "2.0", "id": 5, "result": live}
    req = fake.requests[0]
    assert req.url == REMOTE and req.method == "POST"
    assert "Authorization" not in req.headers
    assert "text/event-stream" in req.headers["Accept"]
    assert fake.body()["method"] == "tools/list"


@pytest.mark.parametrize("failure", [NetworkError("offline"), jresp(500, {"error": "boom"})])
def test_tools_list_falls_back_to_the_bundled_tool(failure):
    r = proxy(FakeTransport(failure)).handle({"jsonrpc": "2.0", "id": 6, "method": "tools/list"})
    assert r["result"] == {"tools": [DIGEST_URL_TOOL]}


def test_bundled_tool_mirrors_the_hosted_contract():
    schema = DIGEST_URL_TOOL["inputSchema"]
    assert DIGEST_URL_TOOL["name"] == "digest_url"
    assert set(schema["properties"]) == {"url", "job_id", "format", "partial_ok", "translate_to", "breakdown"}
    # job_id alone collects a running job, so url is not required by the schema.
    assert schema["required"] == []
    assert DIGEST_URL_TOOL["annotations"]["readOnlyHint"] is True
    assert DIGEST_URL_TOOL["title"] == DIGEST_URL_TOOL["annotations"]["title"]
    assert schema["properties"]["format"]["enum"] == ["markdown", "json"]
    assert schema["properties"]["translate_to"]["pattern"] == "^[a-z]{2}(-[A-Z]{2})?$"


# -- tools/call --------------------------------------------------------------


def test_tools_call_forwards_with_the_key_and_relays_the_result():
    fake = FakeTransport(jresp(200, {"jsonrpc": "2.0", "id": 7, "result": TOOL_TEXT}))
    r = proxy(fake).handle(call(7, breakdown=True))
    assert r == {"jsonrpc": "2.0", "id": 7, "result": TOOL_TEXT}
    req = fake.requests[0]
    assert req.headers["Authorization"] == "Bearer ld_live_mcp"
    assert fake.body()["params"] == {"name": "digest_url", "arguments": {"url": "https://v.douyin.com/abc/", "breakdown": True}}


def test_job_id_message_from_a_long_video_is_relayed_unchanged():
    pending = {
        "content": [
            {
                "type": "text",
                "text": 'Still reading that link — long videos take a minute. It is running as job j1. '
                'Call digest_url again with job_id="j1" (omit url) in about 15 seconds to collect it.',
            }
        ]
    }
    fake = FakeTransport(jresp(200, {"jsonrpc": "2.0", "id": 8, "result": pending}))
    r = proxy(fake).handle(call(8))
    assert r["result"] == pending and "isError" not in r["result"]


def test_tools_call_without_a_key_explains_and_sends_nothing():
    fake = FakeTransport()
    r = proxy(fake, key=None).handle(call(9))
    assert r["result"]["isError"] is True
    text = r["result"]["content"][0]["text"]
    assert "LINKDIGEST_API_KEY" in text and "linkdigest.dev/app/keys" in text
    assert fake.requests == []


def test_a_refused_key_becomes_a_readable_tool_error():
    fake = FakeTransport(jresp(401, {"jsonrpc": "2.0", "id": 10, "error": {"code": -32001, "message": "invalid or missing API key"}}))
    r = proxy(fake).handle(call(10))
    assert r["id"] == 10 and r["result"]["isError"] is True
    assert "refused" in r["result"]["content"][0]["text"]


def test_remote_protocol_errors_are_relayed():
    fake = FakeTransport(jresp(200, {"jsonrpc": "2.0", "id": 11, "error": {"code": -32602, "message": "url is required"}}))
    r = proxy(fake).handle(call(11, url=""))
    assert r == {"jsonrpc": "2.0", "id": 11, "error": {"code": -32602, "message": "url is required"}}


def test_unreachable_remote_is_a_tool_error_not_a_crash():
    r = proxy(FakeTransport(NetworkError("could not reach https://linkdigest.dev/mcp: timed out"))).handle(call(12))
    assert r["result"]["isError"] is True and "timed out" in r["result"]["content"][0]["text"]


def test_unknown_tool_is_rejected_locally():
    fake = FakeTransport()
    r = proxy(fake).handle({"jsonrpc": "2.0", "id": 13, "method": "tools/call", "params": {"name": "rm_rf"}})
    assert r["error"]["code"] == -32602 and fake.requests == []


def test_sse_responses_are_understood():
    sse = (
        "event: message\n"
        'data: {"jsonrpc":"2.0","method":"notifications/progress","params":{}}\n\n'
        "event: message\n"
        f"data: {json.dumps({'jsonrpc': '2.0', 'id': 14, 'result': TOOL_TEXT}, ensure_ascii=False)}\n\n"
    )
    r = proxy(FakeTransport(tresp(200, sse, "text/event-stream"))).handle(call(14))
    assert r["result"] == TOOL_TEXT


def test_batches_reply_per_request():
    fake = FakeTransport()
    r = proxy(fake).handle(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "ping"},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "ping"},
        ]
    )
    assert [x["id"] for x in r] == [1, 2]


# -- the stdio loop ----------------------------------------------------------


def test_serve_speaks_newline_delimited_json_rpc():
    fake = FakeTransport(
        jresp(200, {"jsonrpc": "2.0", "id": 2, "result": {"tools": [DIGEST_URL_TOOL]}}),
        jresp(200, {"jsonrpc": "2.0", "id": 3, "result": TOOL_TEXT}),
    )
    lines = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    stdin = io.BytesIO(("\n".join(json.dumps(m) for m in lines) + "\nnot json\n\n").encode())
    stdout = io.BytesIO()
    serve(proxy(fake), stdin, stdout)
    stdin2 = io.BytesIO((json.dumps(call(3)) + "\n").encode())
    serve(proxy(fake), stdin2, stdout)

    replies = [json.loads(line) for line in stdout.getvalue().decode("utf-8").splitlines()]
    by_id = {r.get("id"): r for r in replies}
    assert by_id[1]["result"]["protocolVersion"] == "2025-06-18"
    assert by_id[2]["result"]["tools"][0]["name"] == "digest_url"
    assert by_id[3]["result"]["content"][0]["text"].startswith("# 标题")
    assert by_id[None]["error"]["code"] == -32700  # the "not json" line
    assert len(replies) == 4  # the notification got nothing back
    # Chinese stays readable on the wire (ensure_ascii=False), one message per line.
    assert "标题" in stdout.getvalue().decode("utf-8")


# -- the installed entry point, as a real subprocess ---------------------------------


class _RemoteMcp(BaseHTTPRequestHandler):
    """A stand-in for https://linkdigest.dev/mcp: tools/list open, tools/call needs the key."""

    def log_message(self, *a):
        pass

    def do_POST(self):
        msg = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if msg["method"] == "tools/list":
            status, out = 200, {"jsonrpc": "2.0", "id": msg["id"], "result": {"tools": [DIGEST_URL_TOOL]}}
        elif self.headers.get("Authorization") != "Bearer ld_live_sub":
            status, out = 401, {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32001, "message": "invalid or missing API key"}}
        else:
            url = msg["params"]["arguments"]["url"]
            status, out = 200, {"jsonrpc": "2.0", "id": msg["id"], "result": {"content": [{"type": "text", "text": f"读到了 {url}"}]}}
        data = json.dumps(out, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def test_linkdigest_mcp_process_end_to_end():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _RemoteMcp)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        env = {k: v for k, v in os.environ.items() if not k.startswith("LINKDIGEST_")}
        env["LINKDIGEST_API_KEY"] = "ld_live_sub"
        env["LINKDIGEST_MCP_URL"] = f"http://127.0.0.1:{server.server_address[1]}/mcp"
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            call(3, url="https://xhslink.com/o/abc"),
        ]
        done = subprocess.run(
            [sys.executable, "-m", "linkdigest.mcp_server"],
            input="".join(json.dumps(r, ensure_ascii=False) + "\n" for r in requests).encode("utf-8"),
            capture_output=True,
            env=env,
            timeout=60,
        )
    finally:
        server.shutdown()
        server.server_close()

    assert done.returncode == 0, done.stderr.decode()
    replies = {r["id"]: r for r in map(json.loads, done.stdout.decode("utf-8").splitlines())}
    assert set(replies) == {1, 2, 3}
    assert replies[2]["result"]["tools"][0]["name"] == "digest_url"
    assert replies[3]["result"]["content"][0]["text"] == "读到了 https://xhslink.com/o/abc"
    log = done.stderr.decode()
    assert "LINKDIGEST_API_KEY set" in log and "ld_live_sub" not in log
