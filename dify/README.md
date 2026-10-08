# LinkDigest for Dify

Turn a Xiaohongshu, Douyin, TikTok, YouTube or X link into text a workflow can use: transcript with timecodes, on-screen text, a description and OCR of every image, the caption and metadata. Markdown or JSON.

Source: https://github.com/jcaiagent7143-ui/linkdigest-mcp · Service: https://linkdigest.dev

[Chinese (zh_Hans)](./README.zh_Hans.md)

## Why

A workflow node that fetches a Xiaohongshu URL gets an app-download shell, not the post. The content is images and video; there is nothing in the HTML to read. Douyin and TikTok are video with no transcript on the page. LinkDigest does the reading on its servers — resolve the share link, pull the media, transcribe speech, OCR on-screen text, describe every image — and returns text.

## Setup

1. Create an API key at https://linkdigest.dev/app/keys — sign in with Google, then one button. 10 free credits when you sign up (once, not monthly), no card.
2. Install this plugin and paste the key into the provider credential. The plugin validates it against the API without spending a digest.

## Tool

**`digest_url(url, format)`**

| Parameter | | |
|---|---|---|
| `url` | required | The share link as shared, including tokens. Short links resolve. |
| `format` | optional | `markdown` (default) or `json` |

Long media exceeds a single request; the plugin polls the job to completion (up to ~3.5 minutes). A cached link returns in about a second and costs nothing.

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
| **Bilibili** | **not supported** — returns HTTP 412 to the service's address |
| **Instagram** | **wired, not verified end to end** |

Facebook is out of scope; it serves no post content to logged-out requests.

## Measured

A 17-image Xiaohongshu note: 17 image descriptions, 381 fragments of on-screen text, ~119 seconds. A TikTok with native captions: 67 transcript segments in ~9 seconds.

## Pricing

10 free credits to start (once, not monthly), no card. Then $5 once for 250 credits (no subscription, never expire), or $9/month for 500 credits — a typical post is 1 credit, video 1 per started minute. Cached links are always free and never counted. Details: https://linkdigest.dev/pricing

## Network

The plugin talks only to `linkdigest.dev` over HTTPS. Nothing runs locally.

## Example workflow

`examples/social-research-agent.yml` — a Dify workflow DSL: paste a list of links, each is read with the plugin, summarised, and the set is compared. Import it under Studio → Create app → Import DSL file, pick a model in the two LLM nodes, run. Walkthrough: https://linkdigest.dev/docs/dify
