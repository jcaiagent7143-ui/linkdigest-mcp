"""A thin client for the hosted LinkDigest REST API.

This plugin runs nothing locally. Every request goes to https://linkdigest.dev
with the user's own API key; the engine, the media fetch, the transcription and
the image reading all happen there. That is why the package is small and why
the only network domain in the manifest is linkdigest.dev.

Two shapes the API can answer with, both handled here:

- 200 with the digest. Cached links come back in about a second.
- 202 with a job id. Long media exceeds a single request (the site's edge caps
  origin responses at ~30 s, and a 17-image Xiaohongshu note takes ~120 s), so
  the API hands back a job to poll. This client polls until the digest is
  ready or a deadline passes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

BASE_URL = "https://linkdigest.dev"
# The poll endpoint tells us how long to wait; this is the fallback and floor.
POLL_SECONDS = 10
# Measured: 119 s for a 17-image Xiaohongshu note, ~150-170 s for a long Douyin
# video. Leave headroom, but do not sit on a hung job forever.
DEADLINE_SECONDS = 210


class LinkDigestError(Exception):
    """A response the caller should show to the user as-is."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


@dataclass
class Digest:
    """Either structured JSON or a Markdown document, never both."""

    json: dict[str, Any] | None
    markdown: str | None
    cached: bool
    credits: int | None


class LinkDigestClient:
    def __init__(self, api_key: str, base_url: str = BASE_URL, session: requests.Session | None = None):
        self._key = api_key.strip()
        self._base = base_url.rstrip("/")
        self._s = session or requests.Session()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._key}", "Accept": "application/json, text/markdown"}

    def check_key(self) -> None:
        """Validate the key without spending a credit.

        The poll endpoint authenticates before it looks up the job, so a bad key
        is a 401 and a good key is anything else. No digest is started.
        """
        r = self._s.get(f"{self._base}/api/v1/digest/credential-check", headers=self._headers(), timeout=20)
        if r.status_code == 401:
            raise LinkDigestError("invalid API key — issue one at https://linkdigest.dev/app/keys", 401)

    def digest(self, url: str, fmt: str = "markdown") -> Digest:
        r = self._s.post(
            f"{self._base}/api/v1/digest",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"url": url, "format": fmt},
            timeout=40,
        )
        if r.status_code == 202:
            body = r.json()
            return self._poll(str(body["jobId"]), int(body.get("retryAfter") or POLL_SECONDS), fmt)
        return self._finish(r, fmt)

    def _poll(self, job_id: str, retry_after: int, fmt: str) -> Digest:
        deadline = time.monotonic() + DEADLINE_SECONDS
        wait = max(retry_after, POLL_SECONDS)
        while True:
            time.sleep(wait)
            r = self._s.get(
                f"{self._base}/api/v1/digest/{job_id}",
                params={"format": fmt},
                headers=self._headers(),
                timeout=40,
            )
            if r.status_code != 202:
                return self._finish(r, fmt)
            if time.monotonic() > deadline:
                raise LinkDigestError(
                    f"still processing after {DEADLINE_SECONDS}s; the job id is {job_id} — "
                    f"call again with that id, or the link is longer than this plan allows",
                    202,
                )
            wait = max(int(r.headers.get("Retry-After") or wait), POLL_SECONDS)

    @staticmethod
    def _finish(r: requests.Response, fmt: str) -> Digest:
        if r.status_code == 401:
            raise LinkDigestError("invalid API key — issue one at https://linkdigest.dev/app/keys", 401)
        if r.status_code == 402:
            raise LinkDigestError("free digests used up — upgrade at https://linkdigest.dev/pricing", 402)
        if r.status_code == 429:
            raise LinkDigestError("rate limited; try again shortly", 429)
        if r.status_code >= 400:
            try:
                msg = r.json().get("error") or r.text
            except ValueError:
                msg = r.text
            # 502 is the API saying "the engine could not read this link": a
            # dead post, a blocked platform, a private account. Not a transport
            # failure, and the message names which.
            raise LinkDigestError(str(msg)[:500], r.status_code)

        ctype = r.headers.get("Content-Type", "")
        if fmt == "markdown" and "json" not in ctype:
            return Digest(json=None, markdown=r.text, cached=r.headers.get("X-Cached", "").lower() == "true", credits=None)
        body = r.json()
        return Digest(json=body, markdown=None, cached=bool(body.get("cached")), credits=body.get("credits"))
