"""linkdigest-mcp — a stdio MCP server for clients that cannot speak HTTP MCP.

It speaks MCP over stdin/stdout (newline-delimited JSON-RPC 2.0) and forwards
the work to the hosted server at https://linkdigest.dev/mcp (Streamable HTTP),
adding your key from LINKDIGEST_API_KEY. Nothing is read or transcribed on
your machine, so there is nothing to install beyond this file: no ffmpeg, no
ASR key, no browser, no cookies.

    export LINKDIGEST_API_KEY=ld_live_...
    uvx --from "git+https://github.com/jcaiagent7143-ui/linkdigest-mcp#subdirectory=python" linkdigest-mcp

(Not on PyPI yet, so the package is installed from the git repository.)

What it does per method:

- initialize       answered here (no network), so the client starts even offline
- tools/list       the hosted server's live list; the bundled copy (tool.py) if
                   that call fails. Sent without your key.
- tools/call       forwarded to the hosted server with your key; its result is
                   relayed unchanged, including the "call again with job_id"
                   message long videos produce
- ping             answered here
- notifications    accepted, nothing sent back
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Tuple, Union

from ._http import Request, Response, Transport, urllib_transport
from ._version import __version__
from .client import API_KEY_ENV, BASE_URL_ENV, DEFAULT_BASE_URL
from .errors import KEYS_URL, NetworkError
from .tool import DIGEST_URL_TOOL, INSTRUCTIONS, TOOL_NAME

MCP_URL_ENV = "LINKDIGEST_MCP_URL"
#: Newest first. initialize answers with the client's version when it is here.
SUPPORTED_PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
#: What the hosted server implements (web/src/app/mcp/route.ts).
REMOTE_PROTOCOL_VERSION = "2024-11-05"
#: The hosted server answers a call within its ~20 s budget (a long video
#: returns a job id instead); this is only a ceiling for a stuck connection.
CALL_TIMEOUT = 150.0
LIST_TIMEOUT = 15.0

Message = Dict[str, Any]
Reply = Union[Message, List[Message], None]


def default_mcp_url() -> str:
    explicit = os.environ.get(MCP_URL_ENV, "").strip()
    if explicit:
        return explicit
    base = (os.environ.get(BASE_URL_ENV, "").strip() or DEFAULT_BASE_URL).rstrip("/")
    return f"{base}/mcp"


def _ok(id_: Any, result: Any) -> Message:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _err(id_: Any, code: int, message: str) -> Message:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def _tool_error(text: str) -> Dict[str, Any]:
    """A failed tool call the model can read and relay, rather than a protocol error."""
    return {"content": [{"type": "text", "text": text}], "isError": True}


class StdioProxy:
    """The method handling, separate from the stdio loop so it can be tested directly."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        mcp_url: Optional[str] = None,
        transport: Optional[Transport] = None,
        log: Optional[Callable[[str], None]] = None,
    ):
        self.api_key = (api_key or "").strip()
        self.mcp_url = mcp_url or default_mcp_url()
        self._transport = transport or urllib_transport
        self._log = log or (lambda line: print(line, file=sys.stderr, flush=True))

    # -- dispatch ---------------------------------------------------------

    def handle(self, message: Any) -> Reply:
        if isinstance(message, list):
            if not message:
                return _err(None, -32600, "invalid request: empty batch")
            replies = [r for r in (self._handle_one(m) for m in message) if r is not None]
            return replies or None
        return self._handle_one(message)

    def _handle_one(self, msg: Any) -> Optional[Message]:
        if not isinstance(msg, dict):
            return _err(None, -32600, "invalid request")
        if "method" not in msg:
            return None  # a response to something we never send; ignore
        method = msg.get("method")
        is_notification = "id" not in msg
        id_ = msg.get("id")
        if not isinstance(method, str):
            return None if is_notification else _err(id_, -32600, "invalid request: method must be a string")
        if is_notification:
            return None  # notifications/initialized, notifications/cancelled, ...
        raw_params = msg.get("params")
        params: Dict[str, Any] = raw_params if isinstance(raw_params, dict) else {}

        if method == "initialize":
            return _ok(id_, self._initialize(params))
        if method == "ping":
            return _ok(id_, {})
        if method == "tools/list":
            return _ok(id_, self._tools_list(id_, params))
        if method == "tools/call":
            return self._tools_call(id_, params)
        return _err(id_, -32601, f"method not found: {method}")

    # -- methods ----------------------------------------------------------

    @staticmethod
    def _initialize(params: Dict[str, Any]) -> Dict[str, Any]:
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else SUPPORTED_PROTOCOL_VERSIONS[0]
        return {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "linkdigest", "title": "LinkDigest", "version": __version__},
            "instructions": INSTRUCTIONS,
        }

    def _tools_list(self, id_: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            status, reply = self._remote("tools/list", params or None, id_, with_key=False, timeout=LIST_TIMEOUT)
            result = (reply or {}).get("result")
            if status == 200 and isinstance(result, dict) and isinstance(result.get("tools"), list) and result["tools"]:
                return result
            self._log(f"linkdigest-mcp: tools/list from {self.mcp_url} answered HTTP {status}; using the bundled tool")
        except NetworkError as e:
            self._log(f"linkdigest-mcp: {e}; using the bundled tool definition")
        return {"tools": [DIGEST_URL_TOOL]}

    def _tools_call(self, id_: Any, params: Dict[str, Any]) -> Message:
        name = params.get("name")
        if name != TOOL_NAME:
            return _err(id_, -32602, f"unknown tool: {name}")
        if not self.api_key:
            return _ok(
                id_,
                _tool_error(
                    f"{API_KEY_ENV} is not set, so LinkDigest cannot read the link. "
                    f"Issue a key at {KEYS_URL} (10 free credits on sign-up) and add it to "
                    f"this MCP server's env as {API_KEY_ENV}."
                ),
            )
        try:
            status, reply = self._remote("tools/call", params, id_, with_key=True, timeout=CALL_TIMEOUT)
        except NetworkError as e:
            return _ok(id_, _tool_error(f"Could not reach LinkDigest: {e}"))

        error = (reply or {}).get("error")
        if status == 401 or (isinstance(error, dict) and error.get("code") == -32001):
            return _ok(
                id_,
                _tool_error(
                    f"The LinkDigest API key in {API_KEY_ENV} was refused (missing or revoked). "
                    f"Issue a new one at {KEYS_URL}."
                ),
            )
        if reply and ("result" in reply or "error" in reply):
            out = {"jsonrpc": "2.0", "id": id_}
            if "result" in reply:
                out["result"] = reply["result"]
            else:
                out["error"] = reply["error"]
            return out
        return _ok(id_, _tool_error(f"LinkDigest answered HTTP {status} without a usable result."))

    # -- transport --------------------------------------------------------

    def _remote(
        self, method: str, params: Optional[Dict[str, Any]], id_: Any, *, with_key: bool, timeout: float
    ) -> Tuple[int, Optional[Message]]:
        payload: Message = {"jsonrpc": "2.0", "id": id_ if id_ is not None else 0, "method": method}
        if params:
            payload["params"] = params
        headers = {
            "Content-Type": "application/json",
            # Streamable HTTP clients must accept both; the hosted server answers JSON.
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": REMOTE_PROTOCOL_VERSION,
        }
        if with_key and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        r = self._transport(Request("POST", self.mcp_url, headers, body, timeout))
        return r.status, _parse_rpc(r, payload["id"])


def _parse_rpc(r: Response, id_: Any) -> Optional[Message]:
    """The JSON-RPC reply in a Streamable HTTP response: plain JSON, or an SSE stream."""
    if not r.body:
        return None
    if "text/event-stream" in r.header("content-type"):
        found: Optional[Message] = None
        data: List[str] = []
        for line in r.text.splitlines() + [""]:
            if line.startswith("data:"):
                data.append(line[5:].lstrip())
            elif not line.strip() and data:
                try:
                    event = json.loads("\n".join(data))
                except ValueError:
                    event = None
                data = []
                if isinstance(event, dict) and ("result" in event or "error" in event):
                    found = event
                    if event.get("id") == id_:
                        return event
        return found
    try:
        parsed = r.json()
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def serve(proxy: StdioProxy, stdin: BinaryIO, stdout: BinaryIO) -> None:
    """Read newline-delimited JSON-RPC from stdin until EOF; write replies to stdout.

    Calls that go over the network run on their own thread, so a slow digest
    does not hold up a ping. Replies may therefore arrive out of order, which
    JSON-RPC allows (they carry the request id).
    """
    lock = threading.Lock()
    workers: List[threading.Thread] = []

    def write(reply: Reply) -> None:
        if reply is None:
            return
        data = json.dumps(reply, ensure_ascii=False, separators=(",", ":")) + "\n"
        with lock:
            stdout.write(data.encode("utf-8"))
            stdout.flush()

    def run(msg: Any) -> None:
        try:
            write(proxy.handle(msg))
        except Exception as e:  # never let one bad message kill the server
            id_ = msg.get("id") if isinstance(msg, dict) else None
            if isinstance(msg, dict) and "id" in msg:
                write(_err(id_, -32603, f"internal error: {e}"))

    for raw in stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            msg = json.loads(line.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            write(_err(None, -32700, "parse error"))
            continue
        slow = isinstance(msg, list) or (isinstance(msg, dict) and msg.get("method") in ("tools/call", "tools/list"))
        if slow:
            t = threading.Thread(target=run, args=(msg,), daemon=True)
            t.start()
            workers.append(t)
            workers = [w for w in workers if w.is_alive()]
        else:
            run(msg)

    # stdin closed: finish what was asked (a piped request still gets its answer).
    for t in workers:
        t.join()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="linkdigest-mcp",
        description=(
            "Stdio MCP server for LinkDigest: exposes digest_url and forwards calls to the hosted "
            "server (default https://linkdigest.dev/mcp) with the key in LINKDIGEST_API_KEY. "
            "Meant to be launched by an MCP client, e.g. "
            "`uvx --from git+https://github.com/jcaiagent7143-ui/linkdigest-mcp#subdirectory=python linkdigest-mcp`."
        ),
    )
    parser.add_argument("--version", action="version", version=f"linkdigest-mcp {__version__}")
    parser.add_argument(
        "--mcp-url",
        default=None,
        help=f"hosted MCP endpoint (default: ${MCP_URL_ENV}, or ${BASE_URL_ENV}/mcp, or {DEFAULT_BASE_URL}/mcp)",
    )
    args = parser.parse_args(argv)

    proxy = StdioProxy(api_key=os.environ.get(API_KEY_ENV), mcp_url=args.mcp_url or default_mcp_url())
    state = "set" if proxy.api_key else f"NOT set — tools/call will ask for one ({KEYS_URL})"
    print(
        f"linkdigest-mcp {__version__}: stdio -> {proxy.mcp_url}; {API_KEY_ENV} {state}",
        file=sys.stderr,
        flush=True,
    )
    try:
        serve(proxy, sys.stdin.buffer, sys.stdout.buffer)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
