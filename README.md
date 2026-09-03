# LinkDigest MCP server

Turn a social media link into text a language model can read — **transcript,
on-screen text, image descriptions, caption and metadata**.

Hosted, remote (streamable HTTP). Nothing to install or run.

**Website:** [linkdigest.dev](https://linkdigest.dev) · **Registry:** `dev.linkdigest/linkdigest`

## The problem

Fetching a social link yourself returns nothing useful. Share URLs are tokenised
(`xsec_token`, `app_code_link`), the content lives in video and images rather
than HTML, and the server sends an app-download shell or a login wall instead of
the post.

```
$ curl -s 'https://xhslink.com/o/1WiQ1QI6Uc0' | grep -o '<title>.*</title>'
<title>小红书</title>
```

That is the whole page. No caption, no images, no text.

## Install

**Claude Code**

```
claude mcp add --transport http linkdigest \
  https://linkdigest.dev/mcp \
  --header "Authorization: Bearer ld_live_..."
```

**Cursor** — `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "linkdigest": {
      "url": "https://linkdigest.dev/mcp",
      "headers": { "Authorization": "Bearer ld_live_..." }
    }
  }
}
```

A key is issued at [linkdigest.dev/app/keys](https://linkdigest.dev/app/keys).
Three digests are free, no card.

## The tool

`digest_url(url, format, job_id)` — only `url` is required.

| Argument | Notes |
|---|---|
| `url` | The post URL, including any share tokens. |
| `format` | `markdown` (default, best for reading) or `json` (structured). |
| `job_id` | Collect a digest already running. Pass this instead of `url` — re-sending the url would start the work again. |

You do not call it yourself. The tool description tells the agent to reach for it
whenever it meets a social link it cannot read, so it happens mid-task without
being asked.

A long video may not finish inside one call. When that happens the result names a
job id; call the tool again with that `job_id` and no `url` to collect it.

## What comes back

`platform`, `author`, `title`, `posted_at`, `caption`, `transcript` (`{t, text}`),
`ocr_text`, `images` (`{description, ocr}`), `key_points`, `raw_markdown`,
`source_url`, `transcript_source`, `degraded`.

Two are worth knowing about:

- **`transcript_source`** — `native_captions`, `asr`, or `none`. Captions the
  platform already published are exact; speech recognition is not. Treating them
  identically eventually quotes a mis-heard number back at someone as fact.
- **`degraded`** — what did not fully work, in plain words. Empty on a clean run.
  It exists because a digest once returned a well-formed, completely empty result
  during a provider outage and was cached for thirty days.

## Platforms

Checked against real posts, not documentation.

| Platform | Status |
|---|---|
| Xiaohongshu 小红书 | Works — image notes and video notes, no login needed |
| Douyin 抖音 | Works — video posts and image notes (图文) |
| TikTok | Works — short links resolve. Rate-limits under load |
| YouTube | Works — native captions where published, otherwise a watched transcript |
| X | Works — posts with video or images |
| Web pages / articles | Works — readable article text, title, author, date |
| **Bilibili** | **Not supported.** Returns HTTP 412 to our server's address. Needs a proxy |
| **Instagram** | **Not verified.** Wired, not confirmed end to end |
| **Facebook** | **Not supported.** Serves no post content to logged-out requests |

The rows that do not work are listed on purpose. Finding out after you have wired
something in is worse than knowing now.

## How long it takes

Measured, not estimated:

- Already-digested link: about **1 second** — anything anyone has run before is
  cached, and cached links are free
- Xiaohongshu note with images: **1–2 minutes**
- YouTube video with captions: about **2.5 minutes**

## Notes

- Chinese speech is transcribed with SenseVoice, which is materially more
  accurate on Mandarin than Whisper-class models.
- Media is never stored or served. It is processed in a temporary directory
  deleted before the request returns; only the text digest is kept.
- A blocked or removed post returns an error, not a description of the error page.

## Also available

A REST API (`POST https://linkdigest.dev/api/v1/digest`), a web app, and Apify
Store actors for bulk runs. See [linkdigest.dev](https://linkdigest.dev).
