"""Typed errors, one per thing a caller can do something about.

The API's own `error` sentence is kept as the message: it says which link,
which limit, which plan. Status codes follow https://linkdigest.dev/openapi.json:

    400  InvalidRequestError    the request was malformed (not a link, bad translate_to)
    401  AuthenticationError    missing or revoked API key
    402  PaymentRequiredError   out of credits / link costs more than is left — nothing was spent
    422  UnreadableLinkError    removed, private or walled post; retrying will not help
    429  RateLimitError         too many requests, or a per-key cap; honour retry_after
    5xx  ServerError            the service or its engine failed; safe to retry later
"""

from __future__ import annotations

from typing import Any, Dict, Optional

KEYS_URL = "https://linkdigest.dev/app/keys"


class LinkDigestError(Exception):
    """Base class. `status` is the HTTP status, or None when nothing came back."""

    def __init__(
        self,
        message: str,
        status: Optional[int] = None,
        *,
        error_code: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status = status
        self.error_code = error_code
        self.body: Dict[str, Any] = body or {}


class NetworkError(LinkDigestError):
    """linkdigest.dev could not be reached (DNS, TLS, timeout, proxy)."""


class InvalidRequestError(LinkDigestError):
    """400: the request itself was wrong."""


class AuthenticationError(LinkDigestError):
    """401: no API key, or one that was revoked. Issue one at https://linkdigest.dev/app/keys."""


class PaymentRequiredError(LinkDigestError):
    """402: out of credits, or this link costs more than is left. Nothing was spent.

    `buy_url` opens checkout for a credit pack for this key's account, with no
    sign-in; `subscribe_url` opens the monthly plan. Either may be None — a
    video over the plan's length cap only offers the monthly plan, for example.
    `error_code` is one of quota_exceeded, insufficient_credits, media_too_long.
    """

    def __init__(self, message: str, status: Optional[int] = 402, **kw: Any):
        super().__init__(message, status, **kw)
        self.buy_url: Optional[str] = self.body.get("buy_url")
        self.subscribe_url: Optional[str] = self.body.get("subscribe_url")


class UnreadableLinkError(LinkDigestError):
    """422: the link was processed and there is nothing readable (removed, private, walled)."""


class RateLimitError(LinkDigestError):
    """429: slow down. `retry_after` is in seconds when the server said."""

    def __init__(self, message: str, status: Optional[int] = 429, *, retry_after: Optional[float] = None, **kw: Any):
        super().__init__(message, status, **kw)
        self.retry_after = retry_after


class ServerError(LinkDigestError):
    """5xx: the service or its engine failed. Not your input; try again later."""


class JobPendingError(LinkDigestError):
    """The digest is still running after `max_wait` seconds.

    Nothing is lost: collect it later with `LinkDigest.collect(job_id)`.
    Re-sending the url would start the work again.
    """

    def __init__(self, job_id: str, stage: Optional[str] = None, waited: float = 0.0):
        where = f" ({stage})" if stage else ""
        super().__init__(
            f"still processing job {job_id}{where} after {waited:.0f}s — "
            f"collect it later with collect({job_id!r}) instead of re-sending the url",
            202,
        )
        self.job_id = job_id
        self.stage = stage


def error_for(status: int, body: Dict[str, Any], text: str, retry_after: Optional[float] = None) -> LinkDigestError:
    """Map an HTTP error response to the matching exception."""
    message = str(body.get("error") or text or f"HTTP {status}").strip()[:1000]
    code = body.get("error_code")
    if status == 401:
        return AuthenticationError(f"{message} — issue a key at {KEYS_URL}", status, error_code=code, body=body)
    if status == 402:
        pay = body.get("buy_url") or body.get("subscribe_url")
        full = f"{message} Pay here (no sign-in): {pay}" if pay else message
        return PaymentRequiredError(full, status, error_code=code, body=body)
    if status == 429:
        return RateLimitError(message, status, retry_after=retry_after, error_code=code, body=body)
    if status == 422:
        return UnreadableLinkError(message, status, error_code=code, body=body)
    if 400 <= status < 500:
        return InvalidRequestError(message, status, error_code=code, body=body)
    return ServerError(message, status, error_code=code, body=body)
