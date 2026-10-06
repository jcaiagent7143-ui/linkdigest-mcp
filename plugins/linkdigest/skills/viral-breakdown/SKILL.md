---
name: viral-breakdown
description: Take a short video or image post apart to see how it is built, and optionally write a new script on the same structure. Use when the user shares a Douyin, Xiaohongshu, TikTok or YouTube link and asks why it worked, for a teardown or breakdown (爆款拆解), the hook, the structure, a script template, or to rewrite or imitate it for their own topic (仿写). Calls the LinkDigest digest_url tool with breakdown enabled.
---

# Viral breakdown and script rewrite

## Step 1: read the post with a breakdown

Call `digest_url` with the link and `breakdown: true`. Use `format: "json"` when you need the fields below. The breakdown costs 1 credit on top of the read; a post already read by anyone costs only that 1 credit.

For a video longer than about ten minutes, add `depth: "transcript"` so the whole video is read (see the `long-video-transcript` skill).

## Step 2: use these fields

| Field | What it holds |
| --- | --- |
| `transcript` | The spoken script with times in seconds |
| `on_screen` | Text burned into the video, with approximate times |
| `breakdown.hook` | The opening: the exact words spoken, the on-screen text, what is shown, and why it holds attention |
| `breakdown.beats` | The structure in order: time, the job of each part, a summary, and a quote from the source |
| `breakdown.title_formula`, `breakdown.cover_text` | How the title and cover are built |
| `breakdown.cta` | What the post asks viewers to do |
| `breakdown.template` | The structure as reusable steps |
| `breakdown.missing` | What the analysis could not see. Do not assume it. |
| `stats` | Likes, saves, comments and shares on the day it was read |

Every quote in the breakdown was checked against the source text in code. Quotes that could not be found were removed, not invented.

## Step 3: report, or write the user's version

If the user asked for a teardown, present the hook, the beats with their times, the title formula and the template. Keep the source quotes as quotes.

If the user wants their own script on this structure:

1. Ask for their topic, product or persona and the target length if they have not said.
2. Keep the order and purpose of the beats and their share of the running time. Replace every line with the user's content. Do not copy the source wording.
3. Use the same kind of hook the source used, with the user's material.
4. Use only facts the user gave. Where a number or example is needed and missing, leave a marked blank.
5. Give two or three title options built on the source's title formula, the cover text, then the script beat by beat with on-screen text suggestions.
6. End with a short table mapping each source beat to the new script's part.

## Be clear about sources

Say what came from the post (transcript, on-screen text, counts), what is analysis by a model (the breakdown), and what you wrote. Mention anything listed in `breakdown.missing`. Remind the user that reusing a structure is fine, while copying the wording is not.
