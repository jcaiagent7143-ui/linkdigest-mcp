---
name: bilibili-video-summary
description: "B站视频总结 / Bilibili video summary. 用户发来 B 站视频（BV 号、bilibili.com/video 链接、b23.tv 短链或分享文字），想知道「这个视频讲了什么」「值不值得看」「结论是什么」时使用。先给一段话的总结和几条要点，每条要点附它依据的原话（口播的带时间，画面上的注明画面），可以核对，不是凭标题猜。不登录 B 站、不要 Cookie、不下载视频；读不了不扣费。1 分钟视频 2 积分，之后每分钟 1 积分。需要 LinkDigest API Key（注册送 10 积分，不用绑卡）。"
version: 1.0.1
homepage: https://linkdigest.dev/zh/bilibili-ai-zongjie?ref=skill-bilibili-video-summary
metadata: {"openclaw":{"requires":{"anyBins":["python3"]},"primaryEnv":"LINKDIGEST_API_KEY","envVars":[{"name":"LINKDIGEST_API_KEY","required":true,"description":"LinkDigest API Key（ld_live_ 开头），在 https://linkdigest.dev/app/keys 创建"}]}}
required_environment_variables:
  - name: LINKDIGEST_API_KEY
    prompt: "LinkDigest API key (starts with ld_live_)"
    help: "https://linkdigest.dev/signin?ref=skill-bilibili-video-summary&next=/app/keys"
    required_for: "summarising Bilibili videos; sign-up gives 10 free credits, no card"
---

# B站视频总结 (Bilibili video summary, with quotes you can check)

An agent that is handed a Bilibili link usually can't open it (the site answers servers with HTTP 412), so it guesses from the title. This skill reads the video itself and answers with a summary whose every point points back to what was said.

## Steps for the agent

1. Run the read on the link the user gave:
   ```bash
   export LINKDIGEST_API_KEY=ld_live_...   # https://linkdigest.dev/signin?ref=skill-bilibili-video-summary&next=/app/keys
   python3 {baseDir}/scripts/linkdigest.py --format json "https://b23.tv/xxxxxxx"
   ```
   A long video may answer `202` first; the script keeps polling until it is done.
2. Answer in this order:
   - one paragraph on what the video says;
   - the key points (`key_points`, plain sentences), each followed by its supporting quote from `key_point_support` (match `point_index`; give the time `t` when it is set, and say "on screen" when `kind` is `image` or `on_screen`);
   - anything the video itself names as its conclusion or recommendation.
3. Keep the full transcript out of the reply unless the user asks for it. Offer it ("要全文逐字稿吗？").
4. Say the cost (last stderr line) and that speech recognition can misspell names and numbers.

## What the read contains

- Title, uploader, description and today's view, like and coin counts.
- Transcript timed by segment: the uploader's subtitles when present, otherwise speech recognition.
- Text seen on screen (slides, captions, product names) from sampled frames.
- Key points written from what was read, with `key_point_support`: for each point, the quote it rests on (from the transcript, the frames or the on-screen text) and `verified: true` when that quote was found word for word. Present an unverified quote as approximate, or leave it out.

## Guardrails

- Never fill in what the read doesn't say. If the transcript is thin (music, no speech), the digest says so; pass that on.
- For lectures over ~8 minutes with chapters or 分P, `bilibili-course-notes` gives a timed outline instead.
- Only need the words, cheaply? `bilibili-subtitle-text` reads speech only, 1 credit per 2 minutes.

## Price and limits

2 credits for the first minute, then 1 per started minute (10 min → 11). Already-read links are 0. Top-ups: 50 credits ¥9.9 (支付宝) / $1.50; 250 credits ¥36 / $5; one-time, no expiry.

Not read: deleted / hidden / members-only / region-locked videos (`422`, Bilibili's reason quoted), live rooms, paid 番剧, comments. A refusal by Bilibili is `503`, retry later. Longer than the plan allows is `402` with a cheaper transcript-first option. None of these is charged.

## Privacy

Only the link goes to linkdigest.dev; no Bilibili login or cookie, and the media is deleted after the read. https://linkdigest.dev/privacy · MCP: `https://linkdigest.dev/mcp` · support@linkdigest.dev
