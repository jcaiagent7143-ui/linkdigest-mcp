"""The tools, exactly as https://linkdigest.dev/mcp lists them.

A word-for-word copy of the TOOLS list the hosted server returns from
tools/list. The stdio server asks the hosted server for its live tool list
first and falls back to this copy only when that call fails, so a client still
sees the tools while offline. tests/test_live.py compares this copy with the
live one, so a change on the server shows up as a failing test here.

2026-11-09: the copy held digest_url alone while the server had grown to five
tools; refreshed from the live list (digest_url, compare_links, check_balance,
list_batches, search_links).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

TOOL_NAME = "digest_url"

INSTRUCTIONS = "Call digest_url whenever you meet a social media link whose content you cannot read."

BUNDLED_TOOLS: List[Dict[str, Any]] = [{'name': 'digest_url',
  'title': 'Read a social media post as text',
  'annotations': {'title': 'Read a social media post as text',
                  'readOnlyHint': True,
                  'destructiveHint': False,
                  'idempotentHint': False,
                  'openWorldHint': True},
  'description': 'Read what a social media link actually says. Works on Xiaohongshu, Douyin, '
                 'Weibo, TikTok, YouTube, X, Instagram, Bilibili, podcast episodes (小宇宙, Apple '
                 "Podcasts) and ordinary web pages. Returns the post's transcript with times, "
                 'on-screen text, the text in every image, caption and counts, key points each '
                 'backed by a quote checked against the post (`key_point_support` in json), and a '
                 'receipt of what was read (`coverage` in json). Facebook and Spotify are not '
                 'supported. Works without an API key for a first look (a summary, two a day per '
                 'address); the full output needs a key — see check_balance. If the result names a '
                 'job id, call again with job_id only. Example: url="https://v.douyin.com/abc/", '
                 'ask="推荐了什么产品、多少钱？".',
  'inputSchema': {'type': 'object',
                  'properties': {'url': {'type': 'string',
                                         'description': 'The post link, or the share text that '
                                                        'contains it. Required unless job_id is '
                                                        'given.'},
                                 'job_id': {'type': 'string',
                                            'description': 'Collect a digest still running, '
                                                           'instead of url (re-sending the url '
                                                           'would start it again).'},
                                 'format': {'type': 'string',
                                            'enum': ['markdown', 'json'],
                                            'description': 'markdown (default) or json '
                                                           '(structured: `coverage`, '
                                                           '`key_point_support`, `answer`, and '
                                                           '`links` — the links the post points '
                                                           'to, with kind; None is opened).'},
                                 'partial_ok': {'type': 'boolean',
                                                'description': 'Read the opening minutes the '
                                                               'budget affords instead of refusing '
                                                               'a long video; the digest then '
                                                               'carries `partial`. Default false: '
                                                               'a long video is refused for free.'},
                                 'translate_to': {'type': 'string',
                                                  'pattern': '^[a-z]{2}(-[A-Z]{2})?$',
                                                  'description': 'Also translate into this '
                                                                 'language (en, ja, zh-CN); the '
                                                                 'original text is kept. +1 '
                                                                 'credit.'},
                                 'depth': {'type': 'string',
                                           'enum': ['full', 'transcript', 'script'],
                                           'description': 'full (default), or transcript for a '
                                                          'long video: the whole transcript with a '
                                                          'frame a minute, 1 credit per started 2 '
                                                          'minutes and a longer length cap. '
                                                          'script: the speech only (文案), 1 credit '
                                                          'per started 2 minutes, no base. YouTube '
                                                          'is always read in full.'},
                                 'breakdown': {'type': 'boolean',
                                               'description': 'Also take the post apart (爆款拆解): '
                                                              'hook, timed beats, title formula, '
                                                              'call to action, reusable template; '
                                                              'quotes checked against the post. +1 '
                                                              'credit.'},
                                 'ask': {'type': 'string',
                                         'maxLength': 300,
                                         'description': 'A question to answer from the post, e.g. '
                                                        '"what products and prices does it '
                                                        'recommend?". Returns answer, found and '
                                                        'the quotes it rests on, checked against '
                                                        'the post; found is false when the post '
                                                        'does not say — nothing is invented. +1 '
                                                        'credit.'},
                                 'insight': {'type': 'boolean',
                                             'description': 'Consumer insight (消费者洞察): audience, '
                                                            'claims, objections, purchase-intent '
                                                            'cues, products/prices, questions — '
                                                            'each a quote checked against the post '
                                                            'and its top comments. +1 credit.'}},
                  'required': []}},
 {'name': 'compare_links',
  'title': 'Compare a set of posts in one page',
  'annotations': {'title': 'Compare a set of posts in one page',
                  'readOnlyHint': True,
                  'destructiveHint': False,
                  'idempotentHint': False,
                  'openWorldHint': True},
  'description': 'Read a set of Xiaohongshu, Douyin, Weibo, TikTok, YouTube or X links as one '
                 'batch and write one comparison over them (批量综合): the themes, hooks, formats and '
                 'claims they share, the objections readers raise and the gaps none of them cover, '
                 'every example naming which link it came from and checked against it word for '
                 'word. The first call starts the batch and returns a batch id; call again with '
                 'batch_id to collect. Needs an API key. Each link is read at its usual price '
                 '(cached links are free); the comparison is 1 credit per 10 links. Example: '
                 'urls=["https://xhslink.com/o/a", "https://xhslink.com/o/b"]. After the browser '
                 "extension's “Digest the notes on this page” button, call list_batches and pass "
                 'the newest batch_id here.',
  'inputSchema': {'type': 'object',
                  'properties': {'urls': {'type': 'array',
                                          'items': {'type': 'string'},
                                          'minItems': 1,
                                          'maxItems': 20,
                                          'description': 'The post links, 1 to 20. Required unless '
                                                         'batch_id is given.'},
                                 'batch_id': {'type': 'string',
                                              'description': 'Collect a batch still running, '
                                                             'instead of urls (re-sending the urls '
                                                             'would start it again).'},
                                 'insight': {'type': 'boolean',
                                             'description': "Also draw every post's consumer "
                                                            'insight (消费者洞察) and compare on it. +1 '
                                                            'credit a link.'},
                                 'breakdown': {'type': 'boolean',
                                               'description': 'Also take every post apart (爆款拆解) '
                                                              'so the comparison sees each hook '
                                                              'and format. +1 credit a link.'},
                                 'translate_to': {'type': 'string',
                                                  'pattern': '^[a-z]{2}(-[A-Z]{2})?$',
                                                  'description': 'Write the comparison (and each '
                                                                 'digest) in this language, e.g. '
                                                                 'en. +1 credit a link.'}},
                  'required': []}},
 {'name': 'check_balance',
  'title': 'Credits left and what a read costs',
  'annotations': {'title': 'Credits left and what a read costs',
                  'readOnlyHint': True,
                  'destructiveHint': False,
                  'idempotentHint': True,
                  'openWorldHint': False},
  'description': 'How many credits this API key has left, what each kind of read costs, and where '
                 'to buy more (links need no sign-in; the credit pack takes Alipay). Without a key '
                 'it returns the prices and how to get a key. Call it before a batch of reads, or '
                 'when digest_url says credits ran out.',
  'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False}},
 {'name': 'list_batches',
  'title': "This account's last batches",
  'annotations': {'title': "This account's last batches",
                  'readOnlyHint': True,
                  'destructiveHint': False,
                  'idempotentHint': True,
                  'openWorldHint': False},
  'description': 'The last batches on this API key, newest first — including the ones the browser '
                 "extension's “Digest the notes on this page” button started from the user's own "
                 'Xiaohongshu or Douyin tab. Each line: batch_id, label, created, status '
                 'done/total, credits, synthesis (ready, pending, failed or none). Pass a batch_id '
                 'to compare_links to read the comparison. Starts nothing, costs nothing. Needs an '
                 'API key.',
  'inputSchema': {'type': 'object',
                  'properties': {'limit': {'type': 'integer',
                                           'minimum': 1,
                                           'maximum': 10,
                                           'description': 'How many, 1 to 10 (default 10).'},
                                 'label': {'type': 'string',
                                           'maxLength': 80,
                                           'description': 'Only batches with this name — the query '
                                                          "of a search_links handoff to the user's "
                                                          'own browser.'}},
                  'additionalProperties': False}},
 {'name': 'search_links',
  'title': 'Find posts on a topic',
  'annotations': {'title': 'Find posts on a topic',
                  'readOnlyHint': True,
                  'destructiveHint': False,
                  'idempotentHint': False,
                  'openWorldHint': True},
  'description': 'Find posts on a topic on xiaohongshu, douyin, youtube, x, web (web search scoped '
                 'to the platform, filtered to links digest_url can read). A search that finds '
                 'posts costs 4 credits on douyin and xiaohongshu, 1 elsewhere; nothing found is '
                 'free. Searching is metered by credits, not by an hourly count. Returns a '
                 'numbered list; pass digest: true to read them as one batch and compare them '
                 '(then compare_links with the batch_id). xiaohongshu returns the notes the web '
                 "has indexed, read from their public pages (no login, no session); for the user's "
                 "own feed or a search the web has not seen, they press the extension's “Digest "
                 'the notes on this page” button on the page they see, then list_batches. douyin '
                 "returns the video pages the web has indexed, each read through Douyin's own "
                 'embed player like a pasted link; Chinese words find the most. Needs an API key. '
                 'Example: query="护肤 早C晚A", platform="xiaohongshu", limit=5.',
  'inputSchema': {'type': 'object',
                  'properties': {'query': {'type': 'string',
                                           'maxLength': 200,
                                           'description': 'The topic, in any language.'},
                                 'platform': {'type': 'string',
                                              'enum': ['xiaohongshu',
                                                       'douyin',
                                                       'youtube',
                                                       'x',
                                                       'web'],
                                              'description': 'Where to look: xiaohongshu, douyin, '
                                                             'youtube, x, web.'},
                                 'limit': {'type': 'integer',
                                           'minimum': 1,
                                           'maximum': 10,
                                           'description': 'How many links, 1 to 10 (default 5).'},
                                 'digest': {'type': 'boolean',
                                            'description': 'Also read the results as one batch '
                                                           'with a comparison (批量综合); returns the '
                                                           'batch_id for compare_links.'},
                                 'insight': {'type': 'boolean',
                                             'description': "With digest: draw every post's "
                                                            'consumer insight (消费者洞察), +1 credit a '
                                                            'link.'},
                                 'breakdown': {'type': 'boolean',
                                               'description': 'With digest: take every post apart '
                                                              '(爆款拆解), +1 credit a link.'}},
                  'required': ['query', 'platform'],
                  'additionalProperties': False}}]

#: The tool every client is told about first; kept for code that imports it.
DIGEST_URL_TOOL: Dict[str, Any] = BUNDLED_TOOLS[0]

TOOL_NAMES: Tuple[str, ...] = tuple(t["name"] for t in BUNDLED_TOOLS)
