# Changelog

Dates are when the change reached this repository. The hosted service at
linkdigest.dev changes independently; its prices are in the README.

## 2026-10-04

- **Python package (`python/`, 0.1.0, MIT):** a zero-dependency SDK (`LinkDigest().digest(url)`),
  a `linkdigest` command line, and `linkdigest-mcp`, a stdio MCP server that forwards to the
  hosted endpoint for clients that only run local servers. Installed from this repository with
  `git+https://…#subdirectory=python`; it is not on PyPI.
- **Chinese README** (`README.zh-CN.md`) with prices in yuan and configs for Cherry Studio,
  通义灵码, Trae, Cursor, Claude Code and the ModelScope MCP plaza.
- **Examples** (`examples/`): Dify, OpenAPI import for Coze-style platforms, Feishu Bitable,
  and links to CSV.
- Docs: transcripts from speech recognition are per ~170 s segment, `on_screen` carries
  approximate times, `transcript_source` can be `gemini_video`, and `degraded` also carries
  route notes on complete digests.

## 2026-10-03

- Current pricing: 10 free credits once per account, 1 credit per started video minute.
- `breakdown` (viral breakdown, 爆款拆解), `translate_to` and `partial_ok` in the tool table.
- `server.json` 1.0.3 in the official MCP registry; Dify plugin source 0.1.3.

## 2026-09-06

- LICENSE file (MIT).

## 2026-09-05

- Dify plugin source (`dify/`).
- Cursor plugin (`.cursor-plugin/`, `mcp.json`, `skills/`) and DeepSeek Harness plugin metadata.

## 2026-09-04

- First release: the hosted MCP server's README, install commands and the `linkdigest` skill.
