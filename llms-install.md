# Installing LinkDigest (for AI agents setting it up)

LinkDigest is a **hosted remote MCP server** (streamable HTTP). There is nothing to build or run.
It reads Xiaohongshu (RedNote), Douyin, Bilibili, Weibo, WeChat, TikTok and YouTube links into text:
timed transcript, text inside images and video frames, top comments, key points with checked quotes.

## 1. Pick how the user signs in

- **OAuth (no key to copy):** server URL `https://linkdigest.dev/mcp/oauth`. The client registers itself
  (dynamic client registration, PKCE S256) and opens a consent page; the user signs in with Google or an
  e-mail code and presses Approve. A new account gets 10 free credits, no card.
- **API key:** server URL `https://linkdigest.dev/mcp` with the header `Authorization: Bearer ld_live_…`.
  The user gets a key at https://linkdigest.dev/app/keys (or by e-mail:
  `POST https://linkdigest.dev/api/v1/keys/request` with `{"email": "..."}`).

## 2. Add it to the client

Cline (`cline_mcp_settings.json`), Cursor (`~/.cursor/mcp.json`), Windsurf and most clients with remote support:

```json
{
  "mcpServers": {
    "linkdigest": {
      "type": "streamableHttp",
      "url": "https://linkdigest.dev/mcp",
      "headers": { "Authorization": "Bearer ld_live_..." }
    }
  }
}
```

A client without remote support (stdio only):

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

Claude Code: `claude mcp add --transport http linkdigest https://linkdigest.dev/mcp/oauth`, then `/mcp` → Authenticate.
Grok Bot: say in chat "Add a custom MCP server called LinkDigest at https://linkdigest.dev/mcp/oauth", then Authorize.

## 3. Check it works

Call `digest_url` with `https://v.douyin.com/VeXgdE_QwTE`. It is already read, so it costs 0 credits and
returns the caption, a timed transcript and the on-screen text of a 2:22 video. `check_balance` shows credits.

Tools: `digest_url` (one link), `search_links` (find posts on a topic), `compare_links` (many links in one
page), `check_balance`, `list_batches`. Docs: https://linkdigest.dev/docs · llms.txt: https://linkdigest.dev/llms.txt
