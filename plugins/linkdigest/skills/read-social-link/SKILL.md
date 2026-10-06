---
name: read-social-link
description: Read a social media post or article link that returns nothing useful when fetched. Use when the user shares a Xiaohongshu / RedNote (小红书), Douyin (抖音), TikTok, YouTube, X or WeChat article (公众号, mp.weixin.qq.com) link and wants to know what it says, a summary, the transcript, the text inside the images, or a translation. Calls the LinkDigest digest_url tool.
---

# Read a social link

Fetching these links yourself returns a login wall, an "open in app" page or a few lines of caption. The content is in video and images. The `digest_url` tool from the LinkDigest server reads the post and returns text.

## When to use

- The user pastes a Xiaohongshu, Douyin, TikTok, YouTube, X or WeChat article link, with or without a question.
- The user pastes the whole share text copied from an app. Pass it as it is; the link is picked out on the server.
- The user asks what a post says, for a summary, the transcript, subtitles, the text on the images, the numbers (likes, saves), or a translation.

Do not use it to search a platform, read comments, list a creator's posts or download media. It reads one public link per call. Bilibili and Instagram are not supported.

## How to call

Call `digest_url` with:

| Argument | Use |
| --- | --- |
| `url` | The link or share text. Keep the link's parameters; Xiaohongshu refuses links without `xsec_token`. |
| `translate_to` | A language code such as `en`, `zh-CN` or `ja` when the user wants the content in another language. Costs 1 extra credit. The original text is kept beside the translation. |
| `partial_ok` | `true` to read the opening part of a long video instead of failing when the budget does not cover all of it. |
| `format` | `markdown` (default) to read, `json` for structured fields. |

A long video may not finish in one call. If the result names a job id, call `digest_url` again with only `job_id` to collect it. Do not submit the link a second time.

## What comes back

- Title, author, post date, caption, hashtags, and the engagement counts the platform reported that day.
- For video: the spoken transcript with timecodes and the on-screen text with approximate times; on Douyin also the post's chapters and category.
- For image posts and WeChat articles: every image in order, with a description and the text written on it.
- Key points, each with a short quote that was checked word for word against the post.
- A coverage receipt: how many seconds or images were read, and a plain list of what was not.
- Links and QR codes the post points to. They are listed, never opened.

## Telling the user

1. Answer from the post's own words first: caption, transcript, image text, counts. Say which parts were written by a model (image descriptions, key points, translation).
2. Quote exactly when the user asks for "the text" or "the transcript". Do not rewrite it.
3. If the coverage receipt lists something that was not read, say so.
4. For prices, names and numbers read from images, suggest checking the original; small or handwritten text can be misread.
5. Mention how many credits the call used when the result reports it.

## When it fails

- "No share token" on Xiaohongshu: ask the user to copy the link from the app's Share → Copy link.
- Not enough credits: the result includes a payment link; pass it to the user. Nothing was charged.
- Private, deleted or login-only posts cannot be read, and are not charged.
