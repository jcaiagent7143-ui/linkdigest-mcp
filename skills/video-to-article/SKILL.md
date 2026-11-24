---
name: video-to-article
description: "视频转文章 / Video to article: turn one 抖音、小红书、B站、YouTube、TikTok or X video link into a written article (公众号文章、小红书图文、博客) built from what is actually said and shown in it. The skill first reads the video — a timestamped speech transcript, the text on screen, and key points checked against the source — then writes the article from that material only, quoting the speaker where it helps. Use when someone pastes a video link and wants it as an article, a post, a newsletter section or show notes. No login or cookies; works without an API key (a short free summary, two a day)."
version: 1.0.0
homepage: https://linkdigest.dev/zh/docs?ref=skill-video-to-article
metadata: {"openclaw":{"requires":{"anyBins":["python3"]},"primaryEnv":"LINKDIGEST_API_KEY","envVars":[{"name":"LINKDIGEST_API_KEY","required":false,"description":"Optional. LinkDigest API key (ld_live_…). Without it: a short free summary, two a day. With it: the full transcript, on-screen text and checked key points the article is written from."}]}}
required_environment_variables:
  - name: LINKDIGEST_API_KEY
    prompt: "LinkDigest API key (starts with ld_live_); optional"
    help: "https://linkdigest.dev/signin?ref=skill-video-to-article&next=/app/keys"
    required_for: "the full transcript; without it the script gives a free summary, two a day"
---

# 视频转文章 · Video to article

An article written from a video is only as good as what the writer actually heard. This skill makes the agent read the video first, then write.

## Steps for the agent

1. Read the video:

   ```bash
   python3 {baseDir}/scripts/linkdigest.py "<video link or the whole share text>" --format json
   ```

   For a video over ~10 minutes, add `--depth transcript` (cheaper: 1 credit per started 2 minutes).
2. Write the article **only from that output**: `transcript` (what was said, with times), `on_screen` (text shown), `key_points` (each tied to a quote). Do not add facts the video does not contain.
3. Shape it for where it will be posted. Ask the user if they have not said:
   - 公众号: a title, a 2-sentence lead, 3–5 sections with subheads, a closing line;
   - 小红书图文: a short hooky title, emoji-light paragraphs, 3–5 tags;
   - blog / newsletter: title, summary, sections, and a "source" line with the video link.
4. When you quote the speaker, copy the words from `transcript` exactly and keep the timestamp, e.g. (02:13).
5. End with the source: the video link and its author.

## Cost

No key: a short free summary only (two links a day per address), which is enough for a short post but not a full article. With a key: a typical short video is a few credits; new accounts get 10 free credits: https://linkdigest.dev/signin?ref=skill-video-to-article&next=/app/keys

## Limits

Private, deleted or app-only posts can't be read; you get a clear message and no charge. Respect the original creator: say where the article comes from.
