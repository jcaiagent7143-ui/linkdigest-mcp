# Changelog

Dates are when the change reached this repository. The hosted service at
linkdigest.dev changes independently; its prices are in the README.

## 2026-10-24 — 1.0.9: `linkdigest capture <file>`

- Python SDK 0.2.3 (0.2.2 took the poll's 202 "still running" for a refusal; found by sending a real clip): `linkdigest capture ./video.mp4 --url "<link>"` reads a video you already
  have — the route for a Douyin post its player will not serve (save it in the app: 分享 →
  保存本地). The sound (16 kHz mono MP3) and up to 36 frames are extracted on your machine with
  ffmpeg and sent to `POST /api/v1/capture`; the video itself is never uploaded. `--dry-run`
  shows what would be sent without a key or a charge; `-o post.md`, `--json`. The command
  existed only in the private repository until now, so the docs' install line could not be
  followed by anyone else.

## 2026-10-08 — 1.0.6: on PyPI

- `pip install linkdigest-mcp` — the SDK, the `linkdigest` CLI and the `linkdigest-mcp` stdio server are published to PyPI by the release workflow through a trusted publisher (no API token). Same attested build as the GitHub release.

## 2026-10-07 — skills: keyless first look, task-named skills

- Every skill script works without `LINKDIGEST_API_KEY`: it uses the site's own free look (one summary a day per visitor) and says how to get the full output.
- Four skills named for the job rather than the brand: `xiaohongshu-note-to-text`, `douyin-video-to-text`, `tiktok-transcript`, `long-video-transcript`.

## 2026-10-06 — 1.0.5

- Python SDK 0.2.0: `depth="transcript"` (CLI `--depth transcript`) reads a long video in full
  as a transcript at 1 credit per 2 minutes. The bundled `digest_url` tool copy matches the
  hosted server again (it gained `depth`).
- Releases are now built by GitHub Actions and carry a signed build provenance attestation:
  `gh attestation verify <file> --repo jcaiagent7143-ui/linkdigest-mcp`.
- `plugins/linkdigest/`: a Claude plugin (hosted MCP server + three skills).

## 2026-10-06 — agent skills

- Seven agent skills in `skills/`, each one job with a standard-library script:
  Xiaohongshu note OCR, Douyin/Xiaohongshu video transcript, WeChat article reader,
  YouTube summary, an English Xiaohongshu/Douyin reader, viral breakdown, script rewrite.
  Installable with `npx skills add`, Hermes (`hermes skills install`) and ClawHub.
- The script accepts `--depth transcript` (long videos, 1 credit per 2 minutes) and names the
  skill it runs from in its User-Agent.

## 2026-10-05 — 1.0.4

- Registry entry (`server.json` 1.0.4) links this repository.
- `digest_url` now has a `title` and MCP annotations (`readOnlyHint: true`, `openWorldHint: true`),
  and `url` is no longer required by the schema: collecting a running job sends `job_id` alone.
  The bundled copy in `python/src/linkdigest/tool.py` matches the hosted tool again.
- README: what is open source here and what is the hosted service.

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
