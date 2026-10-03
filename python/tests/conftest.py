"""A fake HTTP layer: every test here runs offline except tests/test_live.py."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Union

import pytest

from linkdigest._http import Request, Response

Item = Union[Response, Exception, Callable[[Request], Response]]


def jresp(status: int, obj: Any, headers: Optional[Dict[str, str]] = None) -> Response:
    h = {"content-type": "application/json"}
    h.update({k.lower(): v for k, v in (headers or {}).items()})
    return Response(status=status, headers=h, body=json.dumps(obj, ensure_ascii=False).encode("utf-8"))


def tresp(status: int, text: str, content_type: str, headers: Optional[Dict[str, str]] = None) -> Response:
    h = {"content-type": content_type}
    h.update({k.lower(): v for k, v in (headers or {}).items()})
    return Response(status=status, headers=h, body=text.encode("utf-8"))


class FakeTransport:
    """Answers requests from a queue, and records every request it was sent."""

    def __init__(self, *items: Item):
        self.queue: List[Item] = list(items)
        self.requests: List[Request] = []

    def __call__(self, req: Request) -> Response:
        self.requests.append(req)
        if not self.queue:
            raise AssertionError(f"unexpected request: {req.method} {req.url}")
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            return item(req)
        return item

    def body(self, i: int = -1) -> Dict[str, Any]:
        raw = self.requests[i].body
        return json.loads(raw.decode("utf-8")) if raw else {}


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: List[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


DIGEST = {
    "platform": "douyin",
    "author": "某作者",
    "title": "三步做出爆款口播",
    "caption": "三步做出爆款口播 #口播",
    "transcript": [{"t": 0.0, "text": "你是不是也遇到过"}, {"t": 2.4, "text": "开头三秒没人看"}],
    "transcript_source": "asr",
    "on_screen": [{"t": 1.0, "text": "开头三秒"}],
    "ocr_text": ["开头三秒"],
    "images": [],
    "key_points": ["开头要有钩子"],
    "degraded": [],
    "raw_markdown": "# 三步做出爆款口播\n\n## Transcript\n[00:00] 你是不是也遇到过\n",
    "cached": False,
    "credits": 2,
    "source_url": "https://www.douyin.com/video/1",
}


@pytest.fixture(autouse=True)
def _no_ambient_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """A developer's own key or base URL must never leak into the offline tests."""
    for name in ("LINKDIGEST_API_KEY", "LINKDIGEST_BASE_URL", "LINKDIGEST_MCP_URL"):
        monkeypatch.delenv(name, raising=False)
