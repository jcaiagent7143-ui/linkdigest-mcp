import json
from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from linkdigest_client import LinkDigestClient, LinkDigestError


class DigestUrlTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        api_key = str(self.runtime.credentials.get("api_key") or "").strip()
        url = str(tool_parameters.get("url") or "").strip()
        fmt = str(tool_parameters.get("format") or "markdown").strip().lower()
        if fmt not in ("markdown", "json"):
            fmt = "markdown"

        if not api_key:
            yield self.create_text_message("LinkDigest API key is not configured")
            return
        if not url:
            yield self.create_text_message("url is required")
            return

        try:
            digest = LinkDigestClient(api_key).digest(url, fmt)
        except LinkDigestError as exc:
            # The API's own message says what went wrong - a dead post, a
            # blocked platform, an exhausted plan. Pass it through unchanged
            # rather than hiding it behind a generic failure.
            yield self.create_text_message(f"LinkDigest: {exc}")
            return
        except requests.RequestException:
            yield self.create_text_message("Could not reach linkdigest.dev")
            return

        if digest.markdown is not None:
            yield self.create_text_message(digest.markdown)
        else:
            yield self.create_json_message(digest.json or {})
            yield self.create_text_message(json.dumps(digest.json, ensure_ascii=False, indent=2))
