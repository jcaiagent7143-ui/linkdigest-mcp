---
name: douyin-video-summary
description: "抖音视频总结 / Douyin video summary. 用户发来抖音视频（douyin.com/video 链接、v.douyin.com 短链或整段分享文字），想知道「这条视频讲了什么」「值不值得看完」「结论是什么」时使用。读的是视频本身：口播（语音识别，带时间）和画面上的字，先给一段话总结和几条要点，每条要点附口播里对应的原话和时间，可以核对，不是凭标题猜。没有 Key 也能先免费看一条摘要；完整逐字稿需要 LinkDigest API Key（注册送 10 积分）。不登录抖音、不要 Cookie、不下载视频；读不了不扣费。"
version: 1.0.1
homepage: https://linkdigest.dev/zh/douyin-shipin-zongjie?ref=skill-douyin-video-summary
metadata: {"openclaw":{"requires":{"anyBins":["python3"]},"primaryEnv":"LINKDIGEST_API_KEY","envVars":[{"name":"LINKDIGEST_API_KEY","required":false,"description":"可选。LinkDigest API Key（ld_live_ 开头），在 https://linkdigest.dev/signin?ref=skill-douyin-video-summary&next=/app/keys 创建，注册送 10 积分；没有 Key 时每个地址每天可免费看 2 条摘要"}],"homepage":"https://linkdigest.dev/zh/douyin-shipin-zongjie?ref=skill-douyin-video-summary"}}
required_environment_variables:
  - name: LINKDIGEST_API_KEY
    prompt: "LinkDigest API key (starts with ld_live_); optional"
    help: "https://linkdigest.dev/signin?ref=skill-douyin-video-summary&next=/app/keys"
    required_for: "the full transcript and on-screen text; without it the script gives a free summary, up to 2 a day per address"
---
# 抖音视频总结 (a Douyin video summary you can check against the speech)

A Douyin share link gives a server an app shell: the content is in the audio and on the frames, and Douyin publishes no captions. An agent handed the link therefore tends to summarise the title. This skill reads the video and answers from what was said.

## Steps for the agent

1. Read the link the user gave (a `douyin.com/video/...` link, a `v.douyin.com` short link, or the whole share text):
   ```bash
   export LINKDIGEST_API_KEY=ld_live_...   # https://linkdigest.dev/signin?ref=skill-douyin-video-summary&next=/app/keys  (optional, see below)
   python3 {baseDir}/scripts/linkdigest.py --format json "https://v.douyin.com/VeXgdE_QwTE"
   ```
   Copy a short link exactly as given: the code after `v.douyin.com/` is case-sensitive. Share text with quotes or line breaks goes in on standard input: `printf '%s' "$SHARE_TEXT" | python3 {baseDir}/scripts/linkdigest.py --format json -`.
2. Answer in this order:
   - one paragraph on what the video says;
   - the points in `key_points`, each followed by the line that says it. When the read carries `key_point_support`, use its `quote` and time `t` for the matching `point_index` (`verified: true` means the quote was found word for word). When it does not, find the line in `transcript` yourself and give its time as `mm:ss` (`transcript` is a list of `{t, text}`, `t` in seconds). When a point rests on something shown rather than said, quote the line from `ocr_text` and say it was on screen;
   - whatever the speaker gives as the conclusion or the recommendation.
3. A point you cannot find in `transcript` or `ocr_text` is dropped or marked "not found in the speech". Do not keep it on the title's word.
4. Offer the full transcript ("要全文逐字稿吗？") and do not paste it unasked. Say what the read cost (last line of stderr).

## With and without a key

| | What comes back | Cost |
| --- | --- | --- |
| No `LINKDIGEST_API_KEY` | A summary: title, author, key points, counts. Up to 2 a day per address. | free |
| With a key | Everything below | credits, see Price |

Sign-up gives 10 credits once, no card.

## What a full read holds

- `title`, `author`, `posted_at`, `caption` and the tags.
- `transcript`: the speech by segment with start times. It is speech recognition (`transcript_source: asr`), so names, numbers and jargon can be misspelt. Tell the user to check those before quoting.
- `ocr_text`: lines read off the frames (burned-in subtitles, slides, product names).
- `key_points`: the points, written from the two above.
- In Markdown (drop `--format json`): the same, plus likes, comments, saves and shares as of the read.

## Other jobs

- Only the spoken words, as cheaply as possible: `douyin-subtitle-text`.
- Many videos at once, or a creator's series: `douyin-batch-to-text`.
- A profile link (`douyin.com/user/...`) is not a video: `douyin-creator-card`.

## Price and limits

1 credit per video plus 1 per started minute: 1 minute is 2, 3 minutes 4, 5 minutes 6, 10 minutes 11. A link someone already read is 0. Top-ups are one-time and never expire: 50 credits ¥9.9 (支付宝) / $1.50, 250 credits ¥36 / $5.

A full read goes up to 10 minutes on a free or top-up account. For longer videos add `--depth transcript` (the whole speech, a few frames, 1 credit plus 1 per started 2 minutes, up to 60 minutes).

## When it cannot read

- `422`: deleted, private, a live room, or a video Douyin only shows to signed-in users. The reason is quoted. Not charged.
- `503`: Douyin declined this read. Try again later. Not charged.
- `402`: longer than the account reads, or not enough credits. The reply says which and carries the top-up link. Not charged.

## Privacy

Only the link goes to linkdigest.dev. No Douyin account or cookie is used and the video is not downloaded to your machine; the media is deleted after the read. https://linkdigest.dev/privacy · Remote MCP: `https://linkdigest.dev/mcp` · support@linkdigest.dev
