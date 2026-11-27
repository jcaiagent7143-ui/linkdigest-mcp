import json
from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from linkdigest_client import LinkDigestClient, LinkDigestError

SOURCES = {
    "social": ["xiaohongshu", "douyin"],
    "all": ["xiaohongshu", "douyin", "hackernews"],
    "hackernews": ["hackernews"],
}


class TopicPulseTool(Tool):
    """Topic Pulse (2026-11-27): one topic and a window of days -> the posts about it from inside
    that window on Xiaohongshu and Douyin (plus Hacker News stories), the newest ones read in
    full, every item ranked by code, and a brief whose points quote their posts word for word
    (each quote checked against the text that was read). Two calls when a run outlasts a tool
    call: start with `topic`, fetch with `pulse_id`."""

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        api_key = str(self.runtime.credentials.get("api_key") or "").strip()
        topic = str(tool_parameters.get("topic") or "").strip()
        pulse_id = str(tool_parameters.get("pulse_id") or "").strip()
        try:
            days = int(float(tool_parameters.get("days") or 30))
        except (TypeError, ValueError):
            days = 30
        days = min(90, max(1, days))
        size = str(tool_parameters.get("size") or "quick").strip().lower()
        if size not in ("quick", "standard", "deep"):
            size = "quick"
        language = str(tool_parameters.get("language") or "zh-CN").strip()
        if language not in ("zh-CN", "en", "ja"):
            language = "zh-CN"
        # "auto" sends no list: the API picks by the topic (Chinese -> the two apps; otherwise Hacker News too).
        sources = SOURCES.get(str(tool_parameters.get("sources") or "auto").strip().lower())

        if not api_key:
            yield self.create_text_message("LinkDigest API key is not configured")
            return
        if not topic and not pulse_id:
            yield self.create_text_message("Give a topic to start a pulse, or a pulse_id to fetch one")
            return

        client = LinkDigestClient(api_key)
        try:
            summary = client.pulse_result(pulse_id, markdown=True) if pulse_id else client.pulse(topic, days, sources, size, language)
            if not pulse_id and summary.get("status") == "done":
                summary = client.pulse_result(str(summary.get("pulse_id")), markdown=True)
        except LinkDigestError as exc:
            yield self.create_text_message(f"LinkDigest: {exc}")
            return
        except requests.RequestException:
            yield self.create_text_message("Could not reach linkdigest.dev")
            return

        status = summary.get("status")
        pid = summary.get("pulse_id")
        if status == "done":
            yield self.create_text_message(summary.get("markdown") or json.dumps(summary.get("pulse") or {}, ensure_ascii=False, indent=2))
            yield self.create_json_message(summary)
        elif status == "failed":
            yield self.create_text_message(
                f"LinkDigest: the pulse did not finish ({summary.get('error') or 'unknown reason'}). "
                "The brief was not charged; searches and reads that had already happened are."
            )
        else:
            yield self.create_text_message(
                f"Pulse {pid} is running ({status}, {summary.get('posts_read') or 0} posts read so far; about "
                f"{summary.get('estimate')} credits). A run that reads Xiaohongshu or Douyin usually takes 2-5 minutes. "
                f"Call this tool again with pulse_id={pid} to get the brief."
            )
            yield self.create_json_message(summary)
