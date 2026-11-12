"""LlamaIndex reader: social media links (抖音, 小红书, B站, TikTok, YouTube, X) as Documents.

    pip install "linkdigest-mcp[llamaindex]"

    from linkdigest.integrations.llamaindex import LinkDigestReader

    docs = LinkDigestReader(depth="script").load_data(["https://v.douyin.com/xxxx/"])
    print(docs[0].metadata["title"], docs[0].text[:200])

One Document per link: the digest's markdown as text, and flat metadata
(platform, title, author, source_url, posted_at, credits, coverage_*) that any
vector store accepts. A link that cannot be read (removed, private, still
running after max_wait) is logged and skipped by default; out of credits, a bad
key or a rate limit stops the load, since every link after it would fail too.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Iterator, List, Literal, Optional, Union

try:
    from llama_index.core.readers.base import BaseReader
    from llama_index.core.schema import Document
except ImportError as e:  # pragma: no cover - only without the extra
    raise ImportError('LinkDigestReader needs llama-index-core: pip install "linkdigest-mcp[llamaindex]"') from e

from ..client import DEFAULT_MAX_WAIT, Digest, LinkDigest
from ..errors import InvalidRequestError, JobPendingError, ServerError, UnreadableLinkError
from ._shared import agent_message

log = logging.getLogger("linkdigest")

#: Skipped under errors="warn": a problem with this one link.
_PER_LINK = (UnreadableLinkError, InvalidRequestError, JobPendingError, ServerError)
#: Billing and bookkeeping, not content: kept out of embeddings and the LLM prompt.
_NOT_CONTENT = ["credits", "cached", "job_id"]


class LinkDigestReader(BaseReader):
    """Read social media links through https://linkdigest.dev.

    api_key       Defaults to LINKDIGEST_API_KEY. Issue one at https://linkdigest.dev/signin?ref=llamaindex&next=/app/keys.
    depth         "full" (default), "transcript" (long videos, about half the price) or
                  "script" (the speech only, cheapest). load_data(depth=...) overrides it.
    translate_to  Also translate each digest, e.g. "en". +1 credit per link.
    max_credits   Your ceiling per link; a read over it is refused and costs nothing.
    errors        "warn" (default): log and skip a link that cannot be read. "raise": stop.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        client: Optional[LinkDigest] = None,
        depth: str = "full",
        translate_to: Optional[str] = None,
        max_credits: Optional[int] = None,
        max_wait: float = DEFAULT_MAX_WAIT,
        errors: Literal["warn", "raise"] = "warn",
    ):
        if errors not in ("warn", "raise"):
            raise ValueError('errors must be "warn" or "raise"')
        self.client = client or LinkDigest(api_key)
        self.depth = depth
        self.translate_to = translate_to
        self.max_credits = max_credits
        self.max_wait = max_wait
        self.errors = errors

    def lazy_load_data(
        self,
        urls: Union[str, Iterable[str]],
        depth: Optional[str] = None,
        translate_to: Optional[str] = None,
    ) -> Iterator[Document]:
        for url in [urls] if isinstance(urls, str) else urls:
            try:
                d = self.client.digest(
                    url,
                    depth=depth or self.depth,
                    translate_to=translate_to or self.translate_to,
                    max_credits=self.max_credits,
                    max_wait=self.max_wait,
                )
            except _PER_LINK as e:
                if self.errors == "raise":
                    raise
                log.warning("LinkDigest skipped %s: %s", url, agent_message(e))
                continue
            yield to_document(url, d)

    def load_data(
        self,
        urls: Union[str, Iterable[str]],
        depth: Optional[str] = None,
        translate_to: Optional[str] = None,
    ) -> List[Document]:
        return list(self.lazy_load_data(urls, depth=depth, translate_to=translate_to))


def to_document(url: str, d: Digest) -> Document:
    data = d.data or {}
    source = str(data.get("source_url") or url)
    meta: Dict[str, Any] = {
        "platform": data.get("platform"),
        "title": data.get("title"),
        "author": data.get("author"),
        "source_url": source,
        "posted_at": data.get("posted_at"),
        "transcript_source": data.get("transcript_source"),
        "credits": d.credits,
        "cached": d.cached,
        "job_id": d.job_id,
    }
    coverage = data.get("coverage") or {}
    for key in ("seconds_transcribed", "duration_seconds", "images_read", "images_total"):
        meta[f"coverage_{key}"] = coverage.get(key)
    if coverage.get("not_captured"):
        meta["coverage_not_captured"] = "; ".join(map(str, coverage["not_captured"]))
    if data.get("degraded"):
        meta["degraded"] = "; ".join(map(str, data["degraded"]))
    # Vector stores such as Chroma refuse None values and nested objects.
    meta = {k: v for k, v in meta.items() if v is not None and v != ""}
    return Document(
        id_=f"linkdigest:{source}",
        text=d.markdown,
        metadata=meta,
        excluded_embed_metadata_keys=list(_NOT_CONTENT),
        excluded_llm_metadata_keys=list(_NOT_CONTENT),
    )


__all__ = ["LinkDigestReader", "to_document"]
