# linkdigest — JavaScript / TypeScript client

TypeScript client for [LinkDigest](https://linkdigest.dev), the intelligence infrastructure for AI agents: read Douyin, Xiaohongshu (RedNote), Bilibili, TikTok, YouTube, X, Weibo, WeChat articles and web links into structured, verifiable data. The data covers the speech transcript, on-screen text, the text in images, the caption, top comments and key points, with quotes checked against the post.

- Zero dependencies.
- Runs on Node 18+, Bun, Deno and edge runtimes (anything with `fetch`).
- Typed results.
- Long videos are collected for you: the API answers 202 with a job id, and the client long-polls it.

## Install

From the GitHub release (no npm account needed):

```bash
npm install https://github.com/jcaiagent7143-ui/linkdigest-mcp/releases/download/js-v0.1.0/linkdigest-0.1.0.tgz
```

Or build it from this repository: `cd js && npm install && npm run build` (dist/index.js + dist/index.d.ts). The npm registry name `linkdigest` will follow.

## Quick start

```ts
import { LinkDigest } from "linkdigest";

const ld = new LinkDigest(); // reads LINKDIGEST_API_KEY; get a key at https://linkdigest.dev/app/keys

// One link: a long video is collected automatically (up to maxWait seconds).
const d = await ld.digest("https://v.douyin.com/…/", { depth: "script" }); // speech only, the cheapest read
console.log(d.title, d.transcript?.map((s) => s.text).join(" "));

// Ask a question; the answer comes with quotes checked against the post.
const a = await ld.digest("https://www.xiaohongshu.com/discovery/item/…?xsec_token=…", { ask: "Which products and prices?" });

// Search a topic, then read the results as one batch.
const found = await ld.search("牛肉面 探店", { platform: "douyin", limit: 10 });
const batch = await ld.batch(found.results.map((r) => r.url), { depth: "script" });
const done = await ld.waitForBatch(batch.batch_id);
for (const [url, digest] of Object.entries(done.digests ?? {})) console.log(url, digest.raw_markdown?.slice(0, 80));

// Credits left, and this key's last failed reads.
console.log(await ld.usage());
```

## Errors

Every error is a `LinkDigestError` with `status`, `errorCode` and the API's `body`:

| Error | When |
|---|---|
| `AuthenticationError` | 401: no key, or a revoked one |
| `PaymentRequiredError` | 402: not enough credits, nothing spent. `buyUrl` opens checkout with no sign-in |
| `UnreadableLinkError` | 422: removed, private or walled. `errorCode` is `not_served` when the platform declined the post |
| `RateLimitError` | 429. `retryAfter` is in seconds |
| `ServerError` | 5xx |
| `NetworkError` | the API could not be reached |
| `JobPendingError` | still running after `maxWait`. Call `collect(jobId)` later; never re-send the url |

## Tested

- Unit tests run against a fake fetch: `npm test`.
- Checked live on 2026-11-22 against linkdigest.dev on a test account:
  - `digest` of a cached link took 1.8 s;
  - `search` (3 Douyin results, 4 credits) took 2.8 s;
  - `batch` + `waitForBatch` of 3 cached links took 0.9 s;
  - `usage` showed only the search was charged.

API reference: https://linkdigest.dev/docs · OpenAPI: https://linkdigest.dev/openapi.json · MIT licence.
