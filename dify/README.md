# LinkDigest for Dify

Turn a Xiaohongshu, Douyin, TikTok, YouTube or X link into text a workflow can use: transcript with timecodes, on-screen text, a description and OCR of every image, the caption and metadata. Markdown or JSON.

Source: https://github.com/jcaiagent7143-ui/linkdigest-mcp · Service: https://linkdigest.dev

[Chinese (zh_Hans)](./README.zh_Hans.md)

## Why

A workflow node that fetches a Xiaohongshu URL gets an app-download shell, not the post. The content is images and video; there is nothing in the HTML to read. Douyin and TikTok are video with no transcript on the page. LinkDigest does the reading on its servers — resolve the share link, pull the media, transcribe speech, OCR on-screen text, describe every image — and returns text.

## Setup

1. Create an API key at https://linkdigest.dev/app/keys — sign in with Google or an email link, then one button. 10 free credits when you sign up (once, not monthly), no card.
2. Install this plugin and paste the key into the provider credential. The plugin validates it against the API without spending a digest.

## Tool

**`digest_url(url, format)`**

| Parameter | | |
|---|---|---|
| `url` | required | The share link as shared, including tokens. Short links resolve. |
| `format` | optional | `markdown` (default) or `json` |

Long media exceeds a single request; the plugin polls the job to completion (up to ~3.5 minutes). A cached link returns in about a second and costs nothing.

**`market_radar(topic, market, size, language)`** - Pain-Point Radar (new in 0.1.7)

One product category, brand or competitor in, one report out: what people search for (Baidu, Taobao and Bing suggestions; Bing and YouTube for `global`), what the top Xiaohongshu + Douyin posts (or YouTube + TikTok reviews) complain about, want and hesitate over, each point counted per post by code with a word-for-word quote, and the searches no post answers. A run takes 10-20 minutes: the first call starts it and returns a `radar_id`; call again with `radar_id` to fetch the report (free). About 41-47 credits for 12 posts, at most 5 a post; posts already read cost nothing.

| Parameter | | |
|---|---|---|
| `topic` | to start | A category, product or brand (1-40 characters) |
| `radar_id` | to fetch | The id the first call returned |
| `market` | optional | `cn` (Xiaohongshu + Douyin, default) or `global` (YouTube + TikTok) |
| `size` | optional | `quick` 12 posts (default), `standard` 24, `deep` 48 |
| `language` | optional | `zh-CN` (default), `en` or `ja` |

## What comes back

- `transcript` with timecodes, and `transcript_source` — `native_captions` (exact, from the platform) or `asr` (speech recognition)
- `ocr_text` — every fragment of on-screen text
- `images` — a description of each image
- `caption`, `key_points`, metadata (author, publish date, counts)
- `degraded` — non-empty when part of the post could not be read. An empty transcript with a non-empty `degraded` is a thinner digest than the post, not a silent post.

## Platforms

| | |
|---|---|
| Xiaohongshu (RedNote) | image and video notes, no login needed |
| Douyin | video posts, and image-and-text notes |
| TikTok | short links resolve; rate-limits under load |
| YouTube | native captions where published, otherwise a watched transcript |
| X | posts with video or images |
| Web pages | article text and metadata |
| Bilibili | videos and b23.tv short links, through Bilibili's own embed player (since 2026-10-24) |
| Instagram | reels and video posts; photo posts read from Instagram's own embed page (a carousel gives its first slide) |
| Weibo | posts with their text, counts, the text in images, a video's speech and top comments |
| WeChat articles | mp.weixin.qq.com/s/… Official Account articles |
| Podcasts | Xiaoyuzhou and Apple Podcasts episodes, transcribed |

Facebook is out of scope; it serves no post content to logged-out requests.

## Measured

A 17-image Xiaohongshu note: 17 image descriptions, 381 fragments of on-screen text. A TikTok with native captions: 67 transcript segments. How long a read takes today, per platform, is computed from the last 30 days of real requests at https://linkdigest.dev/platforms (never typed in here).

## Pricing

10 free credits to start (once, not monthly), no card. Then, once and never expiring: 50 credits for ¥9.9 by Alipay or $1.50 by card, or 250 credits for ¥36 / $5; or $9/month for 500 credits. An image post is 1 credit for up to 6 images, +1 per further 6 (a 12-image note is 2); a video is 1 credit plus 1 per started minute (a 3-minute Douyin is 4). Cached links are always free and never counted. Details: https://linkdigest.dev/pricing

## Network

The plugin talks only to `linkdigest.dev` over HTTPS. Nothing runs locally.
