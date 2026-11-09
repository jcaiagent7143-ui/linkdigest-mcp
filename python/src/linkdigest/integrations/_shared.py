"""What the LangChain tool and the LlamaIndex reader both say and keep."""

from __future__ import annotations

from typing import Any, Dict

from ..errors import (
    LinkDigestError,
    PaymentRequiredError,
    RateLimitError,
    UnreadableLinkError,
)

PRICING_URL = "https://linkdigest.dev/pricing"

#: The fields an agent reads. raw_markdown is left out of the JSON form (it is
#: the markdown form), and ocr_text repeats on_screen without the times.
COMPACT_KEYS = (
    "platform",
    "source_url",
    "title",
    "author",
    "posted_at",
    "caption",
    "transcript",
    "transcript_source",
    "on_screen",
    "images",
    "key_points",
    "answer",
    "breakdown",
    "translation",
    "links",
    "stats",
    "coverage",
    "degraded",
    "partial",
    "depth",
    "credits",
    "cached",
)


def compact(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: data[k] for k in COMPACT_KEYS if data.get(k) not in (None, "", [], {})}


def agent_message(e: LinkDigestError) -> str:
    """The error as a sentence an agent can act on, or pass to its user."""
    if isinstance(e, PaymentRequiredError):
        if e.buy_url or e.subscribe_url:
            # error_for already put the pay link in the message.
            return f"{e.message} Nothing was charged. Tell the user: the link opens payment, no sign-in."
        return f"{e.message} Nothing was charged. Credits: {PRICING_URL}"
    if isinstance(e, UnreadableLinkError):
        return f"This post cannot be read: {e.message} Nothing was charged; retrying will not help."
    if isinstance(e, RateLimitError) and e.retry_after:
        return f"{e.message} Try again in {e.retry_after:.0f} seconds."
    return e.message
