"""LangChain tool: a social media link (抖音, 小红书, B站, TikTok, YouTube, X) as text.

    pip install "linkdigest-mcp[langchain]"

    from linkdigest.integrations.langchain import LinkDigestTool

    tool = LinkDigestTool()  # reads LINKDIGEST_API_KEY
    print(tool.invoke({"url": "https://v.douyin.com/xxxx/", "depth": "script"}))

The tool returns the digest's markdown to the model (or compact JSON with
output="json"); called through a ToolCall, the full JSON is also on the
ToolMessage as `artifact`. A read still running after `max_wait` comes back
as a job id the model collects on a second call, so it is not paid for twice.
A refused read (402 out of credits, 422 removed or private post) comes back
as a sentence for the model to pass on, with the pay link when there is one.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Literal, Optional, Tuple

try:
    from langchain_core.callbacks import CallbackManagerForToolRun
    from langchain_core.tools import BaseTool, ToolException
except ImportError as e:  # pragma: no cover - only without the extra
    raise ImportError('LinkDigestTool needs langchain-core: pip install "linkdigest-mcp[langchain]"') from e
from pydantic import BaseModel, Field

from ..client import DEFAULT_MAX_WAIT, LinkDigest
from ..errors import JobPendingError, LinkDigestError
from ._shared import agent_message, compact

DESCRIPTION = (
    "Read a social media post or web page as text: its transcript (timed), on-screen text, "
    "image descriptions, caption, key points and metadata. Works on Douyin, Xiaohongshu "
    "(RedNote), Bilibili, Weibo, WeChat articles, TikTok, YouTube, X, Instagram, podcasts "
    "and ordinary web pages - posts you cannot read by fetching the URL yourself, because "
    "they are video or images behind share links. Use it whenever you are given such a "
    "link. depth=script returns only the spoken words (cheapest); depth=transcript reads a "
    "long video (a talk, a course, a podcast) in full at about half the price. The result "
    "says how much of the post it captured. A link anyone has read before is free."
)


class LinkDigestInput(BaseModel):
    url: Optional[str] = Field(
        default=None,
        description="The post link, or the whole share text that contains it. Required unless job_id is given.",
    )
    depth: Literal["full", "transcript", "script"] = Field(
        default="full",
        description=(
            "full (default): transcript plus densely sampled frames. transcript: for long videos, "
            "the whole transcript plus a frame a minute. script: the speech only."
        ),
    )
    translate_to: Optional[str] = Field(
        default=None,
        pattern=r"^[a-z]{2}(-[A-Z]{2})?$",
        description="Also translate the digest, e.g. en, ja, zh-CN. +1 credit.",
    )
    job_id: Optional[str] = Field(
        default=None,
        description="Collect a read an earlier call said was still running, by its job id, instead of re-sending the url.",
    )


class LinkDigestTool(BaseTool):
    """Read one social media link through https://linkdigest.dev.

    api_key      Defaults to LINKDIGEST_API_KEY. Issue one at https://linkdigest.dev/signin?ref=langchain&next=/app/keys.
    output       "markdown" (default) or "json": what the model is given.
    max_credits  Your ceiling per link; a read over it is refused and costs nothing.
    max_wait     Seconds to wait for a long read before handing back its job id.
    """

    name: str = "digest_url"
    description: str = DESCRIPTION
    args_schema: type[BaseModel] = LinkDigestInput
    response_format: Literal["content", "content_and_artifact"] = "content_and_artifact"

    client: Any = Field(default=None, exclude=True)
    output: Literal["markdown", "json"] = "markdown"
    max_credits: Optional[int] = None
    max_wait: float = DEFAULT_MAX_WAIT

    def __init__(self, api_key: Optional[str] = None, *, client: Optional[LinkDigest] = None, **kwargs: Any):
        # A refused read is something to tell the user, not a crash of the agent.
        kwargs.setdefault("handle_tool_error", True)
        kwargs.setdefault("handle_validation_error", True)
        super().__init__(client=client or LinkDigest(api_key), **kwargs)

    def _run(
        self,
        url: Optional[str] = None,
        depth: str = "full",
        translate_to: Optional[str] = None,
        job_id: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        try:
            if job_id:
                d = self.client.collect(job_id, max_wait=self.max_wait)
            elif url:
                d = self.client.digest(
                    url,
                    depth=depth,
                    translate_to=translate_to or None,
                    max_credits=self.max_credits,
                    max_wait=self.max_wait,
                )
            else:
                raise ToolException("Give url (the post link) or job_id (to collect a read still running).")
        except JobPendingError as e:
            stage = f", {e.stage}" if e.stage else ""
            return (
                f"Still reading (job {e.job_id}{stage}). Call {self.name} again with "
                f'job_id="{e.job_id}" in a minute to collect it; re-sending the url would start over.',
                {"job_id": e.job_id, "stage": e.stage, "pending": True},
            )
        except LinkDigestError as e:
            raise ToolException(agent_message(e)) from e
        data = d.data or {}
        content = d.markdown if self.output == "markdown" else json.dumps(compact(data), ensure_ascii=False)
        return content, data


__all__ = ["LinkDigestTool", "LinkDigestInput"]
