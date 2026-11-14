# Link-reading benchmark

What four ways of reading a link get from Bilibili, Douyin, Xiaohongshu and YouTube posts: LinkDigest, Jina Reader (`r.jina.ai`, keyless), one plain page fetch, and `yt-dlp --dump-json`.

LinkDigest is our product. That is why the sampling rule, the runner, the scorer and every per-link score are here: you can check them, and re-run them.

## Run 2026-11-14 (24 links)

Results page (Chinese): https://linkdigest.dev/zh/lianjie-duqu-ceping

| reader | opened the post | speech transcript | text in picture | comments |
|---|---|---|---|---|
| LinkDigest | 23/24 with content | 16/24 | 22/24 | 6/24 |
| Jina Reader | 14/24 | 0 | 0 | 0 |
| plain fetch | 7/24 | 0 | 0 | 0 |
| yt-dlp (metadata only) | 12/24 | 3 caption tracks listed | — | — |

"Speech", "text in picture" and "comments" count only where the post has them (many Bilibili popular videos are music only; Xiaohongshu photo notes have no speech). LinkDigest missed one link: a 3-hour YouTube video it could not download, which came back with title and cover only and was not charged. LinkDigest used 108 credits for the 24 links (cap 12 each); the other three readers are free.

## How

1. `sample.py` picks the links **before any reader runs**: the first 6 videos of 10 minutes or less on Bilibili's public popular list, and the first 6 results of three fixed topic searches (Douyin 「家常菜 做法」, Xiaohongshu 「咖啡 探店」, YouTube 「如何学习编程」). Every link sampled is kept.
2. `run.py` reads each link with the four readers and writes their raw outputs to `raw/` (`LINKDIGEST_API_KEY` for the LinkDigest column; `--only jina,fetch,ytdlp` runs the free ones).
3. `score.py` scores from the files only. A reader opened the post when the post's own title (recorded at sampling time) is in its output. For speech, picture text and comments, up to five lines LinkDigest read are searched for in the other readers' text; half or more found counts as read.

`2026-11-14/links.json` is the sample and `2026-11-14/results.json` the per-link scores. The raw outputs are not republished here: they contain the creators' own words and pages. Running the scripts regenerates them.
