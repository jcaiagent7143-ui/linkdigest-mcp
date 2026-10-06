---
name: long-video-transcript
description: Read a long video in full as a transcript. Use when the user shares a Douyin, Xiaohongshu or TikTok video longer than about ten minutes (a course, talk, interview, live replay) and wants the full transcript, notes or a summary of the whole thing, or when a normal read came back partial or was refused as too long. Calls the LinkDigest digest_url tool with depth set to transcript.
---

# Long videos, read in full

A normal read samples the picture densely and costs 1 credit per minute, with a length limit of 10 minutes on free and pack accounts and 30 minutes on the monthly plan. Transcript-first mode reads the whole speech and only a few frames, costs 1 credit per started 2 minutes, and accepts up to 60 minutes on free and pack accounts and 2 hours on the monthly plan.

## How to call

Call `digest_url` with the link and `depth: "transcript"`.

- A 44-minute video costs 23 credits this way, against 45 for a full read.
- The result often takes more than one call. If it names a job id, call `digest_url` again with only `job_id` until the result arrives. Do not send the link again.
- Add `partial_ok: true` if the user would rather get the opening part than nothing when credits run short. The result then says how far it read.

YouTube is the exception: it is always read in full by a model that watches the video, at the per-minute price, and `depth` has no effect there.

## What you get, and what you do not

- The full spoken transcript with timecodes, and key points with checked quotes.
- A few frames only: one per chapter when the video has chapters, otherwise about one a minute, 30 at most. On-screen text between those frames is not read. The coverage receipt in the result says this, and you should tell the user when slides or on-screen text matter to them.

## Working with the result

1. For notes or a summary, work through the transcript in order and keep the timecodes so the user can jump to a part.
2. Use the post's chapters as headings when they are present.
3. If the user needs what was on screen (slides, code, figures), offer a full read of that section's video instead, and say it costs more.
4. Report how many credits the read used.

## When a read was partial or refused

If an earlier result carries `partial` or a "too long" refusal, it also names the transcript-first price for the whole video. Offer that to the user before reading again.
