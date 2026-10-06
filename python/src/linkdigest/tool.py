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

DIGEST_URL_TOOL: Dict[str, Any] = {'name': 'digest_url',
 'title': 'Read a social media post as text',
 'annotations': {'title': 'Read a social media post as text',
                 'readOnlyHint': True,
                 'destructiveHint': False,
                 'idempotentHint': False,
                 'openWorldHint': True},
 'description': 'Turn a social media URL into LLM-ready context. Works on Xiaohongshu, Douyin, '
                "TikTok, YouTube, X and ordinary web pages. Returns the post's transcript, "
                'on-screen text, image descriptions, caption and metadata — the things you cannot '
                'get by fetching the URL yourself, because these posts are video or images behind '
                'tokenised share links. Use this whenever you are given a social media link. '
                'Bilibili, Instagram and Facebook are not supported. A long video may not finish '
                'in one call: if the result names a job id, call this tool again with that job_id '
                '(and no url) to collect it. Set breakdown to true to also get a teardown of how '
                'the post is built (hook, timed beats, reusable template) — useful when the user '
                'wants to learn from or remake a post. For a long video (a talk, a course, a '
                'podcast), set depth to transcript: the whole transcript with a frame a minute, at '
                'about half the per-minute price. A digest says how much of the post it captured '
                'and what it did not read (a Coverage section in markdown; `coverage` in json), '
                'and backs each key point with a short quote the server checked against the post '
                '(`key_point_support` in json, verified true or false).',
 'inputSchema': {'type': 'object',
                 'properties': {'url': {'type': 'string',
                                        'description': 'The post URL, including any share tokens. '
                                                       'Required unless job_id is given.'},
                                'job_id': {'type': 'string',
                                           'description': 'Collect a digest already running. Pass '
                                                          'the job id from a previous call instead '
                                                          'of url. Use this rather than re-sending '
                                                          'the url, which would start the work '
                                                          'again.'},
                                'format': {'type': 'string',
                                           'enum': ['markdown', 'json'],
                                           'description': 'markdown (default, best for reading) or '
                                                          'json (structured). json adds `coverage` '
                                                          '(seconds_transcribed, duration_seconds, '
                                                          'largest_frame_gap_seconds, images_read, '
                                                          'images_total, not_captured) and '
                                                          '`key_point_support` ({ point_index, '
                                                          'kind, t, image_index, quote, verified } '
                                                          'per key point). Either format lists the '
                                                          'links the post points to (a Links '
                                                          'section; `links` in json: { url, '
                                                          'found_in, label, kind }, from its '
                                                          "caption, QR codes, WeChat's 阅读原文 and "
                                                          'on-screen text). None is opened; kind '
                                                          'marks payment codes and group invites.'},
                                'partial_ok': {'type': 'boolean',
                                               'description': 'Read the opening minutes the budget '
                                                              'affords instead of refusing a video '
                                                              "over max_credits or the plan's "
                                                              'length cap. Default false: a long '
                                                              'video is refused and costs nothing '
                                                              '(YouTube excepted: its length is '
                                                              'known only after Gemini watches it, '
                                                              'so it is read in full and billed at '
                                                              'most max_credits). When true, the '
                                                              'digest carries `partial` '
                                                              '(read_seconds, duration_seconds, '
                                                              'full_credits). An image post the '
                                                              'budget does not cover whole reads '
                                                              'its first images instead (6 a '
                                                              'credit); its partial has 0 seconds, '
                                                              'and image_count / images_read say '
                                                              'how many.'},
                                'translate_to': {'type': 'string',
                                                 'pattern': '^[a-z]{2}(-[A-Z]{2})?$',
                                                 'description': 'Also translate the digest into '
                                                                'this language: an ISO 639-1 code, '
                                                                'optionally with a region (en, ja, '
                                                                'zh-CN). The original-language '
                                                                'text is always returned; the '
                                                                'translation is added alongside it '
                                                                'under `translation` (title, '
                                                                'caption, key points, transcript '
                                                                'text, on-screen text, image '
                                                                'descriptions), and as a '
                                                                'Translation section at the end of '
                                                                'the markdown. Machine '
                                                                "translation. Costs the digest's "
                                                                'price plus 1 credit; a repeat of '
                                                                'the same url and language is '
                                                                'served from cache for free.'},
                                'depth': {'type': 'string',
                                          'enum': ['full', 'transcript'],
                                          'description': 'How much of a video to read. full '
                                                         '(default): the transcript plus frames '
                                                         'sampled densely, 1 credit per started '
                                                         'minute. transcript: transcript-first, '
                                                         'for long videos — the whole transcript '
                                                         'plus one frame a minute (or one per '
                                                         'chapter), one credit per started 2 '
                                                         'minutes, and a longer length cap (free '
                                                         '60 min, paid 120 min, against 10 and 30 '
                                                         'for full). Coverage says the frames were '
                                                         'sparse and `depth` in json says which '
                                                         'read it was. When a full read would be '
                                                         'partial, `partial.transcript_credits` is '
                                                         'what this read of the whole video costs. '
                                                         'A YouTube video read by Gemini watching '
                                                         'it (YouTube blocks this server) has no '
                                                         'transcript-only form: it is read in full '
                                                         'and priced as a full read.'},
                                'breakdown': {'type': 'boolean',
                                              'description': 'Also take the post apart (爆款拆解): the '
                                                             'hook in its first seconds, the '
                                                             'structure as timed beats, the title '
                                                             'formula, cover text, call to action, '
                                                             'audience, and a reusable template to '
                                                             'make your own version. Quotes are '
                                                             'copied from the post and checked '
                                                             'against it; engagement counts and '
                                                             'hashtags come from the platform. '
                                                             "Written in the post's language, or "
                                                             'in translate_to if given. Shown as a '
                                                             'section in markdown and as '
                                                             '`breakdown` in json. Costs the '
                                                             "digest's price plus 1 credit; a "
                                                             'repeat is served from cache for '
                                                             'free.'}},
                 'required': []}}
