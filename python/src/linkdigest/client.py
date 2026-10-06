"""A small client for the hosted LinkDigest REST API.

Nothing runs locally. Every call goes to https://linkdigest.dev with your own
API key; fetching the media, transcription and image reading happen there.

The API answers a digest request in one of two ways:

- 200 with the digest. A link anyone has read before comes back in about a
  second and costs nothing.
- 202 with a job id, when the work takes longer than one request may last
  (long videos, image notes with many pictures). The client then collects the
  job with GET /api/v1/digest/{jobId}?wait=20, which holds each request open
  for up to 20 seconds until the job settles, and repeats until the digest is
  ready or `max_wait` runs out. Running out raises JobPendingError carrying
  the job id, so the work is collected later rather than paid for twice.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote, urlencode

from ._http import Request, Response, Transport, urllib_transport
from .errors import (
    KEYS_URL,
    AuthenticationError,
    InvalidRequestError,
    JobPendingError,
    LinkDigestError,
    NetworkError,
    ServerError,
    error_for,
)

DEFAULT_BASE_URL = "https://linkdigest.dev"
API_KEY_ENV = "LINKDIGEST_API_KEY"
BASE_URL_ENV = "LINKDIGEST_BASE_URL"

#: The server caps ?wait at 20 seconds (GET /api/v1/digest/{jobId}).
POLL_WAIT_SECONDS = 20
#: How long digest() keeps collecting a running job before raising JobPendingError.
DEFAULT_MAX_WAIT = 600.0
#: Same rule as the API: an ISO 639-1 code, optionally with a region.
TRANSLATE_TO = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")
FORMATS = ("json", "markdown")

PendingCallback = Callable[[str, Optional[str]], None]


@dataclass
class Digest:
    """One post as text.

    `markdown` is always filled: the whole digest as Markdown (with any
    breakdown and translation sections). `data` is the structured JSON when
    format="json" (the default) and None for format="markdown".
    `credits` is what this call cost — 0 when it came from cache.
    """

    markdown: str
    data: Optional[Dict[str, Any]] = None
    cached: bool = False
    credits: Optional[int] = None
    job_id: Optional[str] = None

    def get(self, key: str, default: Any = None) -> Any:
        return (self.data or {}).get(key, default)

    def __getitem__(self, key: str) -> Any:
        if self.data is None:
            raise KeyError(f"{key!r}: this digest was requested as markdown; use format='json' for fields")
        return self.data[key]

    def __contains__(self, key: object) -> bool:
        return self.data is not None and key in self.data

    # The fields people reach for most. Everything else: digest.get("...").
    @property
    def platform(self) -> Optional[str]:
        return self.get("platform")

    @property
    def title(self) -> Optional[str]:
        return self.get("title")

    @property
    def author(self) -> Optional[str]:
        return self.get("author")

    @property
    def caption(self) -> Optional[str]:
        return self.get("caption")

    @property
    def transcript(self) -> List[Dict[str, Any]]:
        """[{t: seconds, text}] — what is said in the video."""
        return self.get("transcript") or []

    @property
    def transcript_text(self) -> str:
        return "\n".join(str(seg.get("text", "")) for seg in self.transcript).strip()

    @property
    def on_screen(self) -> List[Dict[str, Any]]:
        """[{t: approximate seconds, text}] — text burned into the video."""
        return self.get("on_screen") or []

    @property
    def images(self) -> List[Dict[str, Any]]:
        """[{description, ocr}] — each image of an image note."""
        return self.get("images") or []

    @property
    def key_points(self) -> List[str]:
        return self.get("key_points") or []

    @property
    def breakdown(self) -> Optional[Dict[str, Any]]:
        """爆款拆解, present when requested with breakdown=True."""
        return self.get("breakdown")

    @property
    def translation(self) -> Optional[Dict[str, Any]]:
        return self.get("translation")

    @property
    def degraded(self) -> List[str]:
        """What did not read fully, in plain words. Empty on a clean run."""
        return self.get("degraded") or []


@dataclass
class _Sent:
    response: Response
    elapsed: float = field(default=0.0)


class LinkDigest:
    """Client for https://linkdigest.dev.

    >>> from linkdigest import LinkDigest
    >>> ld = LinkDigest()                      # reads LINKDIGEST_API_KEY
    >>> d = ld.digest("https://v.douyin.com/xxxx/", breakdown=True)
    >>> print(d.title, d.credits)
    >>> print(d.markdown)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_wait: float = DEFAULT_MAX_WAIT,
        transport: Optional[Transport] = None,
    ):
        key = (api_key if api_key is not None else os.environ.get(API_KEY_ENV, "")).strip()
        if not key:
            raise AuthenticationError(
                f"no API key: pass api_key=... or set {API_KEY_ENV}. Issue one at {KEYS_URL}"
            )
        self._key = key
        self.base_url = (base_url or os.environ.get(BASE_URL_ENV) or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_wait = max_wait
        self._transport: Transport = transport or urllib_transport
        # Seams for tests; not part of the public API.
        self._sleep: Callable[[float], None] = time.sleep
        self._clock: Callable[[], float] = time.monotonic

    def __repr__(self) -> str:  # never show the key
        return f"LinkDigest(base_url={self.base_url!r})"

    # -- public -----------------------------------------------------------

    def digest(
        self,
        url: str,
        format: str = "json",
        breakdown: bool = False,
        translate_to: Optional[str] = None,
        partial_ok: bool = False,
        *,
        depth: str = "full",
        max_credits: Optional[int] = None,
        max_wait: Optional[float] = None,
        on_pending: Optional[PendingCallback] = None,
    ) -> Digest:
        """Read one link. Blocks until the digest is ready (or `max_wait` passes).

        url           The post link, or the whole share text that contains it.
        format        "json" (default; structured fields plus `markdown`) or "markdown".
        breakdown     Also take the post apart (爆款拆解): hook, timed beats, title
                      formula, template. +1 credit.
        translate_to  Also translate, e.g. "en", "ja", "zh-CN". +1 credit.
        partial_ok    Read the opening minutes the budget affords instead of
                      refusing a video that is too long or too expensive.
        depth         "full" (default) or "transcript": a long video read in full as a
                      transcript with a few frames, 1 credit per 2 minutes. YouTube
                      is always read in full.
        max_credits   Your own ceiling for this link; over it is a 402 and costs nothing.
        max_wait      Seconds to keep collecting a long job (default 600). 0 = do not
                      wait: raise JobPendingError with the job id straight away.
        on_pending    Called as on_pending(job_id, stage) each time the job is still running.
        """
        body = self._body(url, format, breakdown, translate_to, partial_ok, max_credits, depth)
        sent = self._send(
            "POST",
            "/api/v1/digest",
            body=json.dumps(body).encode("utf-8"),
            content_type="application/json",
        )
        r = sent.response
        if r.status == 202:
            pending = _json_or_empty(r)
            job_id = str(pending.get("jobId") or "")
            if not job_id:
                raise ServerError("the API answered 202 without a job id", 202, body=pending)
            if on_pending:
                on_pending(job_id, pending.get("stage"))
            limit = self.max_wait if max_wait is None else max_wait
            if limit <= 0:
                raise JobPendingError(job_id, pending.get("stage"))
            return self.collect(job_id, format, max_wait=limit, on_pending=on_pending)
        return self._finish(r, format)

    def collect(
        self,
        job_id: str,
        format: str = "json",
        *,
        max_wait: Optional[float] = None,
        on_pending: Optional[PendingCallback] = None,
    ) -> Digest:
        """Collect a digest that is already running, by the job id a 202 gave you.

        Use this instead of re-sending the url, which would start the work again.
        """
        job_id = (job_id or "").strip()
        if not job_id:
            raise InvalidRequestError("job_id is required")
        if format not in FORMATS:
            raise InvalidRequestError(f"format must be one of {FORMATS}, got {format!r}")
        limit = self.max_wait if max_wait is None else max_wait
        path = f"/api/v1/digest/{quote(job_id, safe='')}?" + urlencode({"format": format, "wait": POLL_WAIT_SECONDS})
        start = self._clock()
        failures = 0
        while True:
            try:
                # The server may hold this request for POLL_WAIT_SECONDS.
                sent = self._send("GET", path, timeout=max(self.timeout, POLL_WAIT_SECONDS + 30))
            except NetworkError:
                # Collecting is idempotent, so a dropped connection is retried.
                failures += 1
                if failures > 3 or self._clock() - start >= limit:
                    raise
                self._sleep(5.0 * failures)
                continue
            r = sent.response
            if r.status in (502, 503, 504) and failures < 3 and self._clock() - start < limit:
                failures += 1
                self._sleep(5.0 * failures)
                continue
            failures = 0
            if r.status != 202:
                return self._finish(r, format, job_id=job_id)

            pending = _json_or_empty(r)
            stage = pending.get("stage")
            if on_pending:
                on_pending(job_id, stage)
            waited = self._clock() - start
            if waited >= limit:
                raise JobPendingError(job_id, stage, waited)
            # ?wait=20 normally holds the request until the job settles; only
            # pause when the server answered early, so we do not spin.
            if sent.elapsed < 5:
                self._sleep(min(_retry_after(r, pending, 10.0), max(0.0, limit - waited)))

    def check_key(self) -> Dict[str, Any]:
        """Validate the key without starting a digest or spending a credit."""
        r = self._send("GET", "/api/v1/digest/credential-check").response
        if r.status >= 400:
            raise _error(r)
        return _json_or_empty(r)

    # -- internals --------------------------------------------------------

    @staticmethod
    def _body(
        url: str,
        format: str,
        breakdown: bool,
        translate_to: Optional[str],
        partial_ok: bool,
        max_credits: Optional[int],
        depth: str = "full",
    ) -> Dict[str, Any]:
        if not isinstance(url, str) or not url.strip():
            raise InvalidRequestError("url is required")
        if format not in FORMATS:
            raise InvalidRequestError(f"format must be one of {FORMATS}, got {format!r}")
        for name, value in (("breakdown", breakdown), ("partial_ok", partial_ok)):
            if not isinstance(value, bool):
                raise InvalidRequestError(f"{name} must be True or False")
        body: Dict[str, Any] = {"url": url.strip(), "format": format}
        # Optional fields are sent only when set, exactly as the API documents them.
        if translate_to:
            if not TRANSLATE_TO.match(translate_to):
                raise InvalidRequestError("translate_to must be a language code like en, ja or zh-CN")
            body["translate_to"] = translate_to
        if breakdown:
            body["breakdown"] = True
        if partial_ok:
            body["partial_ok"] = True
        if depth not in ("full", "transcript"):
            raise InvalidRequestError('depth must be "full" or "transcript"')
        if depth == "transcript":
            body["depth"] = "transcript"
        if max_credits is not None:
            if isinstance(max_credits, bool) or not isinstance(max_credits, int) or max_credits < 1:
                raise InvalidRequestError("max_credits must be a whole number >= 1")
            body["max_credits"] = max_credits
        return body

    def _send(
        self,
        method: str,
        path: str,
        *,
        body: Optional[bytes] = None,
        content_type: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> _Sent:
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Accept": "application/json, text/markdown",
        }
        if content_type:
            headers["Content-Type"] = content_type
        t0 = self._clock()
        response = self._transport(
            Request(method, self.base_url + path, headers, body, timeout or self.timeout)
        )
        return _Sent(response, self._clock() - t0)

    @staticmethod
    def _finish(r: Response, format: str, job_id: Optional[str] = None) -> Digest:
        if r.status >= 400:
            raise _error(r)
        if r.status != 200:
            raise ServerError(f"unexpected HTTP {r.status} from the API", r.status)
        ctype = r.header("content-type")
        if format == "markdown" and "json" not in ctype:
            return Digest(
                markdown=r.text,
                data=None,
                cached=r.header("x-cached").lower() == "true",
                credits=None,
                job_id=job_id,
            )
        try:
            data = r.json()
        except ValueError as e:
            raise ServerError("the API answered 200 with a body that is not JSON", r.status) from e
        if not isinstance(data, dict):
            raise ServerError("the API answered 200 with unexpected JSON", r.status)
        return Digest(
            markdown=str(data.get("raw_markdown") or ""),
            data=data,
            cached=bool(data.get("cached")),
            credits=data.get("credits"),
            job_id=job_id or data.get("jobId"),
        )


def _json_or_empty(r: Response) -> Dict[str, Any]:
    try:
        data = r.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _retry_after(r: Response, body: Dict[str, Any], default: float) -> float:
    for raw in (r.header("retry-after"), body.get("retryAfter")):
        try:
            if raw not in (None, ""):
                return max(0.0, float(raw))
        except (TypeError, ValueError):
            continue
    return default


def _error(r: Response) -> LinkDigestError:
    body = _json_or_empty(r)
    retry = _retry_after(r, body, -1.0)
    return error_for(r.status, body, r.text if not body else "", retry_after=None if retry < 0 else retry)
