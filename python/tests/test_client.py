from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import List, Tuple

import pytest

from conftest import DIGEST, FakeClock, FakeTransport, jresp, tresp
from linkdigest import (
    AuthenticationError,
    Digest,
    InvalidRequestError,
    JobPendingError,
    LinkDigest,
    NetworkError,
    PaymentRequiredError,
    RateLimitError,
    ServerError,
    UnreadableLinkError,
)
from linkdigest._http import Request, urllib_transport

KEY = "ld_live_test_key"


def client(fake: FakeTransport, clock: FakeClock | None = None, **kw) -> LinkDigest:
    c = LinkDigest(KEY, transport=fake, **kw)
    clock = clock or FakeClock()
    c._clock = clock
    c._sleep = clock.sleep
    return c


# -- the request ---------------------------------------------------------


def test_digest_posts_url_with_bearer_key_and_returns_fields():
    fake = FakeTransport(jresp(200, DIGEST))
    d = client(fake).digest("https://v.douyin.com/abc/")

    req = fake.requests[0]
    assert req.method == "POST"
    assert req.url == "https://linkdigest.dev/api/v1/digest"
    assert req.headers["Authorization"] == f"Bearer {KEY}"
    assert req.headers["Content-Type"] == "application/json"
    # Optional fields are absent unless asked for.
    assert fake.body() == {"url": "https://v.douyin.com/abc/", "format": "json"}

    assert isinstance(d, Digest)
    assert d.title == "三步做出爆款口播"
    assert d.platform == "douyin"
    assert d.credits == 2 and d.cached is False
    assert d.markdown.startswith("# 三步做出爆款口播")
    assert d.transcript_text == "你是不是也遇到过\n开头三秒没人看"
    assert d["transcript_source"] == "asr"
    assert "on_screen" in d
    assert d.breakdown is None and d.translation is None


def test_digest_sends_breakdown_translate_partial_and_max_credits():
    fake = FakeTransport(jresp(200, {**DIGEST, "breakdown": {"hook": {"spoken": "你是不是也遇到过"}}}))
    d = client(fake).digest(
        "  分享文案 https://v.douyin.com/abc/ 复制此链接  ", "json", True, "en", True, max_credits=5
    )
    assert fake.body() == {
        "url": "分享文案 https://v.douyin.com/abc/ 复制此链接",
        "format": "json",
        "translate_to": "en",
        "breakdown": True,
        "partial_ok": True,
        "max_credits": 5,
    }
    assert d.breakdown == {"hook": {"spoken": "你是不是也遇到过"}}


def test_key_from_environment_and_base_url_override(monkeypatch):
    monkeypatch.setenv("LINKDIGEST_API_KEY", "  ld_live_from_env  ")
    monkeypatch.setenv("LINKDIGEST_BASE_URL", "http://localhost:3000/")
    fake = FakeTransport(jresp(200, DIGEST))
    LinkDigest(transport=fake).digest("https://x.com/a/status/1")
    assert fake.requests[0].url == "http://localhost:3000/api/v1/digest"
    assert fake.requests[0].headers["Authorization"] == "Bearer ld_live_from_env"


def test_missing_key_is_an_authentication_error_that_says_where_to_get_one():
    with pytest.raises(AuthenticationError, match="linkdigest.dev/app/keys"):
        LinkDigest()


def test_repr_never_shows_the_key():
    assert KEY not in repr(LinkDigest(KEY))


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"url": ""}, "url is required"),
        ({"url": "https://a.b", "format": "html"}, "format"),
        ({"url": "https://a.b", "translate_to": "english"}, "translate_to"),
        ({"url": "https://a.b", "breakdown": "yes"}, "breakdown"),
        ({"url": "https://a.b", "max_credits": 0}, "max_credits"),
        ({"url": "https://a.b", "max_credits": True}, "max_credits"),
    ],
)
def test_bad_arguments_fail_before_any_request(kwargs, match):
    fake = FakeTransport()
    with pytest.raises(InvalidRequestError, match=match):
        client(fake).digest(**kwargs)
    assert fake.requests == []


# -- long jobs -----------------------------------------------------------


def test_202_is_collected_with_wait_20_until_ready():
    clock = FakeClock()

    def held(status, obj, headers=None):
        # The server holds ?wait=20 requests: time passes during the call.
        def answer(req: Request):
            clock.now += 20
            return jresp(status, obj, headers)

        return answer

    fake = FakeTransport(
        jresp(202, {"pending": True, "jobId": "job/1", "retryAfter": 15}),
        held(202, {"pending": True, "jobId": "job/1", "stage": "transcribing", "retryAfter": 10}, {"Retry-After": "10"}),
        held(200, {**DIGEST, "cached": False, "jobId": "job/1", "credits": 4}),
    )
    seen: List[Tuple[str, str]] = []
    d = client(fake, clock).digest("https://v.douyin.com/long/", on_pending=lambda j, s: seen.append((j, s)))

    assert [r.method for r in fake.requests] == ["POST", "GET", "GET"]
    assert fake.requests[1].url == "https://linkdigest.dev/api/v1/digest/job%2F1?format=json&wait=20"
    assert fake.requests[1].timeout >= 50  # longer than the server's 20 s hold
    assert d.job_id == "job/1" and d.credits == 4
    assert seen == [("job/1", None), ("job/1", "transcribing")]
    assert clock.slept == []  # the server did the waiting


def test_early_202_answers_are_paced_by_retry_after():
    clock = FakeClock()
    fake = FakeTransport(
        jresp(202, {"pending": True, "jobId": "j"}),
        jresp(202, {"pending": True, "jobId": "j"}, {"Retry-After": "7"}),
        jresp(200, DIGEST),
    )
    client(fake, clock).digest("https://xhslink.com/o/x")
    assert clock.slept == [7.0]


def test_max_wait_zero_returns_the_job_id_without_polling():
    fake = FakeTransport(jresp(202, {"pending": True, "jobId": "j9", "retryAfter": 15}))
    with pytest.raises(JobPendingError) as e:
        client(fake).digest("https://v.douyin.com/long/", max_wait=0)
    assert e.value.job_id == "j9"
    assert "collect('j9')" in str(e.value)
    assert len(fake.requests) == 1


def test_running_out_of_max_wait_raises_job_pending_with_stage():
    clock = FakeClock()
    pending = jresp(202, {"pending": True, "jobId": "j", "stage": "frames"}, {"Retry-After": "10"})
    fake = FakeTransport(*([pending] * 10))
    with pytest.raises(JobPendingError) as e:
        client(fake, clock).collect("j", max_wait=25)
    assert e.value.job_id == "j" and e.value.stage == "frames"
    assert sum(clock.slept) <= 25


def test_collect_survives_a_dropped_connection_and_a_502():
    clock = FakeClock()
    fake = FakeTransport(NetworkError("reset"), jresp(502, {"error": "engine unreachable"}), jresp(200, DIGEST))
    d = client(fake, clock).collect("j")
    assert d.title == DIGEST["title"]
    assert clock.slept == [5.0, 10.0]


def test_collect_gives_up_after_repeated_server_errors():
    fake = FakeTransport(*([jresp(503, {"error": "engine secret not configured"})] * 4))
    with pytest.raises(ServerError, match="engine secret"):
        client(fake).collect("j")


def test_collect_markdown_format():
    fake = FakeTransport(tresp(200, "# t\n\nbody", "text/markdown; charset=utf-8"))
    d = client(fake).collect("j", "markdown")
    assert "format=markdown" in fake.requests[0].url
    assert d.markdown == "# t\n\nbody" and d.data is None and d.job_id == "j"


def test_post_without_job_id_in_202_is_a_server_error():
    with pytest.raises(ServerError):
        client(FakeTransport(jresp(202, {"pending": True}))).digest("https://a.b")


# -- answers -------------------------------------------------------------


def test_markdown_format_returns_text_and_cache_header():
    fake = FakeTransport(tresp(200, "# 标题\n", "text/markdown; charset=utf-8", {"X-Cached": "true"}))
    d = client(fake).digest("https://xhslink.com/o/x", "markdown")
    assert d.markdown == "# 标题\n" and d.data is None and d.cached is True and d.credits is None
    with pytest.raises(KeyError, match="markdown"):
        d["title"]


def test_402_carries_the_pay_links():
    body = {
        "error": "Not enough credits for this link: it needs 4, 1 left.",
        "error_code": "insufficient_credits",
        "upgradeRequired": True,
        "buy_url": "https://linkdigest.dev/buy?t=abc",
        "subscribe_url": "https://linkdigest.dev/subscribe?t=abc",
    }
    with pytest.raises(PaymentRequiredError) as e:
        client(FakeTransport(jresp(402, body))).digest("https://v.douyin.com/abc/")
    err = e.value
    assert err.status == 402 and err.error_code == "insufficient_credits"
    assert err.buy_url == body["buy_url"] and err.subscribe_url == body["subscribe_url"]
    assert body["buy_url"] in str(err) and "Not enough credits" in str(err)


def test_402_for_a_long_video_offers_only_the_monthly_plan():
    body = {"error": "That video is 25 minutes.", "error_code": "media_too_long", "subscribe_url": "https://s"}
    with pytest.raises(PaymentRequiredError) as e:
        client(FakeTransport(jresp(402, body))).digest("https://v.douyin.com/abc/")
    assert e.value.buy_url is None and e.value.subscribe_url == "https://s"
    assert "https://s" in str(e.value)


@pytest.mark.parametrize(
    "status, body, headers, exc",
    [
        (401, {"error": "invalid or missing API key."}, {}, AuthenticationError),
        (400, {"error": "invalid url"}, {}, InvalidRequestError),
        (422, {"error": "could not read this link: the post was removed"}, {}, UnreadableLinkError),
        (500, {"error": "unexpected error"}, {}, ServerError),
    ],
)
def test_error_statuses_map_to_typed_errors(status, body, headers, exc):
    with pytest.raises(exc) as e:
        client(FakeTransport(jresp(status, body, headers))).digest("https://a.b")
    assert e.value.status == status
    assert body["error"] in str(e.value)


def test_429_exposes_retry_after():
    fake = FakeTransport(jresp(429, {"error": "Too many digests at once"}, {"Retry-After": "30"}))
    with pytest.raises(RateLimitError) as e:
        client(fake).digest("https://a.b")
    assert e.value.retry_after == 30.0


def test_non_json_error_body_still_reads():
    with pytest.raises(ServerError, match="Bad Gateway"):
        client(FakeTransport(tresp(502, "Bad Gateway", "text/html"))).digest("https://a.b")


def test_check_key_spends_nothing_and_reports_401():
    fake = FakeTransport(jresp(200, {"ok": True, "key": {"label": "laptop", "hint": "…abcd"}}))
    assert client(fake).check_key()["ok"] is True
    assert fake.requests[0].method == "GET"
    assert fake.requests[0].url.endswith("/api/v1/digest/credential-check")
    with pytest.raises(AuthenticationError):
        client(FakeTransport(jresp(401, {"ok": False, "error": "invalid"}))).check_key()


# -- the real HTTP layer, against a local server (still offline) ----------------


class _Handler(BaseHTTPRequestHandler):
    seen: List[Tuple[str, str, dict, bytes]] = []

    def log_message(self, *a):  # keep pytest output clean
        pass

    def _reply(self, status: int, obj: dict, headers: dict | None = None) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n)
        _Handler.seen.append(("POST", self.path, dict(self.headers), body))
        if json.loads(body).get("url") == "https://pay.me":
            self._reply(402, {"error": "out of credits", "error_code": "quota_exceeded", "buy_url": "https://b"})
        else:
            self._reply(202, {"pending": True, "jobId": "local1", "retryAfter": 15})

    def do_GET(self):
        _Handler.seen.append(("GET", self.path, dict(self.headers), b""))
        self._reply(200, {**DIGEST, "jobId": "local1"})


@pytest.fixture()
def local_api():
    _Handler.seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def test_urllib_transport_end_to_end(local_api):
    ld = LinkDigest(KEY, base_url=local_api)
    d = ld.digest("https://v.douyin.com/abc/", breakdown=True)
    assert d.title == DIGEST["title"] and d.job_id == "local1"
    (m1, p1, h1, b1), (m2, p2, h2, _) = _Handler.seen
    assert (m1, p1) == ("POST", "/api/v1/digest")
    assert json.loads(b1) == {"url": "https://v.douyin.com/abc/", "format": "json", "breakdown": True}
    assert h1["Authorization"] == f"Bearer {KEY}"
    assert h1["User-Agent"].startswith("linkdigest-python/")
    assert (m2, p2) == ("GET", "/api/v1/digest/local1?format=json&wait=20")


def test_urllib_transport_returns_error_bodies(local_api):
    with pytest.raises(PaymentRequiredError) as e:
        LinkDigest(KEY, base_url=local_api).digest("https://pay.me")
    assert e.value.buy_url == "https://b" and e.value.error_code == "quota_exceeded"


def test_urllib_transport_unreachable_host_is_a_network_error():
    with pytest.raises(NetworkError):
        urllib_transport(Request("GET", "http://127.0.0.1:9/", {}, None, 2.0))
