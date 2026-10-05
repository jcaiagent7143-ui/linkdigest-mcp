"""The digest_url tool, exactly as https://linkdigest.dev/mcp lists it.

A word-for-word copy of the TOOLS entry the hosted server returns from
tools/list. The stdio server asks the hosted server for its live tool list
first and falls back to this copy only when that call fails, so a client still
sees the tool while offline. tests/test_live.py compares this copy with the
live one, so a change on the server shows up as a failing test here.
"""

from __future__ import annotations

from typing import Any, Dict

TOOL_NAME = "digest_url"

INSTRUCTIONS = "Call digest_url whenever you meet a social media link whose content you cannot read."

DIGEST_URL_TOOL: Dict[str, Any] = {
    "name": TOOL_NAME,
    "title": "Read a social media post as text",
    "annotations": {
        "title": "Read a social media post as text",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
    "description": (
        "Turn a social media URL into LLM-ready context. Works on Xiaohongshu, "
        "Douyin, TikTok, YouTube, X and ordinary web pages. Returns the post's "
        "transcript, on-screen text, image descriptions, caption and metadata — "
        "the things you cannot get by fetching the URL yourself, because these "
        "posts are video or images behind tokenised share links. Use this "
        "whenever you are given a social media link. Bilibili, Instagram and "
        "Facebook are not supported. A long video may not finish in one call: if "
        "the result names a job id, call this tool again with that job_id (and no "
        "url) to collect it. Set breakdown to true to also get a teardown of how "
        "the post is built (hook, timed beats, reusable template) — useful when "
        "the user wants to learn from or remake a post."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The post URL, including any share tokens. Required unless job_id is given.",
            },
            "job_id": {
                "type": "string",
                "description": (
                    "Collect a digest already running. Pass the job id from a previous "
                    "call instead of url. Use this rather than re-sending the url, "
                    "which would start the work again."
                ),
            },
            "format": {
                "type": "string",
                "enum": ["markdown", "json"],
                "description": "markdown (default, best for reading) or json (structured).",
            },
            "partial_ok": {
                "type": "boolean",
                "description": (
                    "Read the opening minutes the budget affords instead of refusing a video "
                    "over max_credits or the plan's length cap. Default false: a long video "
                    "is refused and costs nothing (YouTube excepted: its length is known only "
                    "after Gemini watches it, so it is read in full and billed at most "
                    "max_credits). When true, the digest carries `partial` (read_seconds, "
                    "duration_seconds, full_credits)."
                ),
            },
            "translate_to": {
                "type": "string",
                "pattern": "^[a-z]{2}(-[A-Z]{2})?$",
                "description": (
                    "Also translate the digest into this language: an ISO 639-1 code, "
                    "optionally with a region (en, ja, zh-CN). The original-language "
                    "text is always returned; the translation is added alongside it "
                    "under `translation` (title, caption, key points, transcript text, "
                    "on-screen text, image descriptions), and as a Translation section "
                    "at the end of the markdown. Machine translation. Costs the digest's "
                    "price plus 1 credit; a repeat of the same url and language is "
                    "served from cache for free."
                ),
            },
            "breakdown": {
                "type": "boolean",
                "description": (
                    "Also take the post apart (爆款拆解): the hook in its first seconds, "
                    "the structure as timed beats, the title formula, cover text, call "
                    "to action, audience, and a reusable template to make your own "
                    "version. Quotes are copied from the post and checked against it; "
                    "engagement counts and hashtags come from the platform. Written in "
                    "the post's language, or in translate_to if given. Shown as a "
                    "section in markdown and as `breakdown` in json. Costs the digest's "
                    "price plus 1 credit; a repeat is served from cache for free."
                ),
            },
        },
        "required": [],
    },
}
