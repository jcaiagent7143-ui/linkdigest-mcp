# linkdigest-mcp (Python)

<!-- mcp-name: dev.linkdigest/linkdigest -->

把抖音、小红书、TikTok、YouTube、X 链接变成 AI 能读的文本：逐字稿、带大致时间的画面文字、
每张图的描述和 OCR、要点，可选爆款拆解（breakdown）和翻译。

Turn a Douyin, Xiaohongshu, TikTok, YouTube or X link into text an LLM can read.

This package is a thin client for the hosted service at [linkdigest.dev](https://linkdigest.dev):
nothing is downloaded or transcribed on your machine, and it has **no dependencies**
(Python 3.10+, standard library only). It installs three things:

| | |
|---|---|
| `from linkdigest import LinkDigest` | Python SDK — waits for long videos for you (`GET /api/v1/digest/{jobId}?wait=20`) and raises typed errors (402 carries a pay link) |
| `linkdigest <url>` | command line — Markdown to stdout, `--json`, `--breakdown`, `--translate en` |
| `linkdigest-mcp` | stdio MCP server — the `digest_url` tool, forwarded to `https://linkdigest.dev/mcp` with your key |

All three read the API key from `LINKDIGEST_API_KEY`. Issue one at
[linkdigest.dev/app/keys](https://linkdigest.dev/app/keys) — 10 free credits on sign-up, no card.

```python
from linkdigest import LinkDigest

ld = LinkDigest()  # LINKDIGEST_API_KEY
d = ld.digest("https://v.douyin.com/xxxx/", breakdown=True)
print(d.title, d.credits)
print(d.markdown)
```

```bash
linkdigest "https://xhslink.com/o/xxxx" --breakdown
```

```json
{
  "mcpServers": {
    "linkdigest": {
      "command": "uvx",
      "args": ["linkdigest-mcp"],
      "env": { "LINKDIGEST_API_KEY": "ld_live_..." }
    }
  }
}
```

Full documentation (中文): [README.zh-CN.md](https://github.com/jcaiagent7143-ui/linkdigest-mcp/blob/main/README.zh-CN.md)
· English: [README.md](https://github.com/jcaiagent7143-ui/linkdigest-mcp/blob/main/README.md)

MIT licensed.
