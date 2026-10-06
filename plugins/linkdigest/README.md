# LinkDigest

Read a social media link as text. Xiaohongshu (RedNote), Douyin, TikTok, YouTube, X and WeChat public-account articles keep their content in video and images behind share links, so fetching the URL returns a login wall or an app page. LinkDigest reads the post and returns what is in it: the spoken transcript with timecodes, the on-screen text, a description and the text of every image, the caption, hashtags, engagement counts and key points with quotes checked against the source.

## What this plugin contains

- A connection to the hosted LinkDigest MCP server at `https://linkdigest.dev/mcp`, which provides one read-only tool, `digest_url`.
- Three skills that tell Claude when and how to use it:
  - `read-social-link`: read one post or article and report what it says.
  - `viral-breakdown`: take a post apart (hook, timed beats, title formula, reusable template) and help write a new script on the same structure.
  - `long-video-transcript`: read a long video in full as a transcript at a lower price.

The plugin has no hooks, no commands and no local programs. It runs nothing on your machine.

## What it sends, and where

When Claude calls `digest_url`, the link you gave (and the options for that call, such as a translation language) is sent to `linkdigest.dev` with your API key. Nothing else from your conversation or your files is sent. LinkDigest fetches the public post, reads it with speech recognition and vision models, and returns text. Media is held in a temporary folder for the read and deleted. Text results are cached per link, so the same public link is free to read again and may be served to others who ask for the same link. Do not submit private links. Privacy policy: https://linkdigest.dev/privacy

## Setup

LinkDigest is a paid service with a free start: 10 free credits on sign-up, no card. Create an API key at https://linkdigest.dev/app/keys and enter it when the plugin asks for "LinkDigest API key". The key is stored in your system's secure storage.

## Cost

One credit is about $0.02 on the $5 pack of 250 credits (Alipay is accepted). An image post with up to 6 images costs 1 credit, and each further 6 images cost 1 more. A video costs 1 credit plus 1 per started minute, or 1 per started 2 minutes in transcript-first mode. Translation and breakdown cost 1 credit each. A link that anyone has read before is cached and free, and a link that cannot be read is not charged. Current prices: https://linkdigest.dev/pricing

## Limits

It reads one public link per call. It does not search, read comments, list a creator's posts, download media, post or log in. Bilibili and Instagram are not supported. Private, deleted and login-only posts cannot be read. YouTube videos are always read in full, at the per-minute price.

## Support

support@linkdigest.dev · Docs: https://linkdigest.dev/docs · Source: https://github.com/jcaiagent7143-ui/linkdigest-mcp
