import json
from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from linkdigest_client import LinkDigestClient, LinkDigestError


class MarketRadarTool(Tool):
    """痛点雷达 · Pain-Point Radar (2026-11-07): one topic → what people search for,
    what posts and their top comments complain about and ask (counted per post by
    code, quotes checked word for word), and the searches no post answers.
    Two calls: start with `topic`, fetch with `radar_id` when it is done."""

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        api_key = str(self.runtime.credentials.get("api_key") or "").strip()
        topic = str(tool_parameters.get("topic") or "").strip()
        radar_id = str(tool_parameters.get("radar_id") or "").strip()
        market = str(tool_parameters.get("market") or "cn").strip().lower()
        if market not in ("cn", "global"):
            market = "cn"
        size = str(tool_parameters.get("size") or "quick").strip().lower()
        if size not in ("quick", "standard", "deep"):
            size = "quick"
        language = str(tool_parameters.get("language") or "zh-CN").strip()
        if language not in ("zh-CN", "en", "ja"):
            language = "zh-CN"

        if not api_key:
            yield self.create_text_message("LinkDigest API key is not configured")
            return
        if not topic and not radar_id:
            yield self.create_text_message("Give a topic to start a radar, or a radar_id to fetch one")
            return

        client = LinkDigestClient(api_key)
        try:
            summary = client.radar_result(radar_id, markdown=True) if radar_id else client.radar(topic, market, size, language)
            if not radar_id and summary.get("status") == "done":
                summary = client.radar_result(str(summary.get("radar_id")), markdown=True)
        except LinkDigestError as exc:
            yield self.create_text_message(f"LinkDigest: {exc}")
            return
        except requests.RequestException:
            yield self.create_text_message("Could not reach linkdigest.dev")
            return

        status = summary.get("status")
        rid = summary.get("radar_id")
        if status == "done":
            yield self.create_text_message(summary.get("markdown") or json.dumps(summary.get("radar") or {}, ensure_ascii=False, indent=2))
            yield self.create_json_message(summary)
        elif status == "failed":
            yield self.create_text_message(f"LinkDigest: the radar did not finish ({summary.get('error') or 'unknown reason'}); the aggregation was not charged")
        else:
            yield self.create_text_message(
                f"Radar {rid} is running ({status}, {summary.get('posts_read') or 0} posts read so far; about "
                f"{summary.get('estimate')} credits). A run usually takes 10-20 minutes. Call this tool again with "
                f"radar_id={rid} to get the report."
            )
            yield self.create_json_message(summary)
