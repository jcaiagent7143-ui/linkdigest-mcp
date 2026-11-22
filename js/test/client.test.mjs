// Unit tests against a fake fetch: no network, no key needed. Run: npm run build && npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { LinkDigest, AuthenticationError, PaymentRequiredError, RateLimitError, UnreadableLinkError, JobPendingError, InvalidRequestError, digestBody } from "../dist/index.js";

const json = (status, body, headers = {}) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", ...headers } });
function fake(handlers) {
  const calls = [];
  const f = async (url, init) => {
    calls.push({ url, init, body: init.body ? JSON.parse(init.body) : undefined });
    const h = handlers.shift();
    if (!h) throw new Error("no more fake responses");
    return typeof h === "function" ? h(url, init) : h;
  };
  return { f, calls };
}

test("a missing key throws AuthenticationError before any request", () => {
  const old = process.env.LINKDIGEST_API_KEY; delete process.env.LINKDIGEST_API_KEY;
  assert.throws(() => new LinkDigest({ fetch: async () => json(200, {}) }), AuthenticationError);
  if (old) process.env.LINKDIGEST_API_KEY = old;
});

test("digest sends only the fields that are set, with the bearer key", async () => {
  const { f, calls } = fake([json(200, { title: "t", transcript: [{ t: 0, text: "hi" }] })]);
  const ld = new LinkDigest({ apiKey: "ld_live_test", fetch: f });
  const d = await ld.digest(" https://v.douyin.com/abc/ ", { depth: "script", ask: "  what   price? " });
  assert.equal(d.title, "t");
  assert.equal(calls[0].url, "https://linkdigest.dev/api/v1/digest");
  assert.deepEqual(calls[0].body, { url: "https://v.douyin.com/abc/", format: "json", ask: "what price?", depth: "script" });
  assert.equal(calls[0].init.headers.Authorization, "Bearer ld_live_test");
  assert.ok(!String(ld).includes("ld_live_test"), "toString never shows the key");
});

test("a 202 is collected with long-poll GETs on the job id, never by re-sending the url", async () => {
  const { f, calls } = fake([json(202, { jobId: "job1", stage: "fetch" }), json(202, { jobId: "job1", stage: "asr" }, { "retry-after": "0" }), json(200, { title: "done" })]);
  const stages = [];
  const ld = new LinkDigest({ apiKey: "k", fetch: f });
  const d = await ld.digest("https://x.com/a/status/1", { onPending: (id, s) => stages.push(`${id}:${s}`) });
  assert.equal(d.title, "done");
  assert.equal(calls.length, 3);
  assert.match(calls[1].url, /\/api\/v1\/digest\/job1\?format=json&wait=20$/);
  assert.equal(calls[1].init.method, "GET");
  assert.deepEqual(stages, ["job1:fetch", "job1:asr"]);
});

test("maxWait 0 throws JobPendingError carrying the job id", async () => {
  const { f } = fake([json(202, { jobId: "job2", stage: "download" })]);
  const ld = new LinkDigest({ apiKey: "k", fetch: f });
  await assert.rejects(ld.digest("https://b23.tv/x", { maxWait: 0 }), (e) => e instanceof JobPendingError && e.jobId === "job2" && e.stage === "download");
});

test("HTTP errors map to typed errors with the API's code and pay links", async () => {
  const { f } = fake([
    json(402, { error: "This link costs 3 credits; 1 is available.", error_code: "insufficient_credits", buy_url: "https://linkdigest.dev/pay/x" }),
    json(429, { error: "slow down" }, { "retry-after": "12" }),
    json(422, { error: "post gone", error_code: "unreadable" }),
  ]);
  const ld = new LinkDigest({ apiKey: "k", fetch: f });
  await assert.rejects(ld.digest("u1"), (e) => e instanceof PaymentRequiredError && e.errorCode === "insufficient_credits" && e.buyUrl === "https://linkdigest.dev/pay/x" && e.message.includes("Pay here"));
  await assert.rejects(ld.digest("u2"), (e) => e instanceof RateLimitError && e.retryAfter === 12);
  await assert.rejects(ld.digest("u3"), (e) => e instanceof UnreadableLinkError && e.status === 422);
});

test("search, batch, getBatch and usage hit the documented paths", async () => {
  const { f, calls } = fake([
    json(200, { results: [{ url: "https://www.douyin.com/video/1" }], credits: 4 }),
    json(202, { batch_id: "B1", status: "running" }),
    json(200, { batch_id: "B1", status: "done", digests: { "https://www.douyin.com/video/1": { raw_markdown: "x" } }, items: [{ url: "https://www.douyin.com/video/1", status: "cached", credits: 0 }] }),
    json(200, { plan: "free", remaining: 7 }),
  ]);
  const ld = new LinkDigest({ apiKey: "k", fetch: f, baseUrl: "https://example.test/" });
  const s = await ld.search("牛肉面 探店", { platform: "douyin", limit: 3 });
  assert.equal(s.results.length, 1);
  assert.deepEqual(calls[0].body, { query: "牛肉面 探店", platform: "douyin", limit: 3 });
  const b = await ld.batch(s.results.map((r) => r.url), { depth: "script" });
  assert.equal(b.batch_id, "B1");
  assert.deepEqual(calls[1].body, { urls: ["https://www.douyin.com/video/1"], depth: "script" });
  const g = await ld.getBatch("B1", { includeDigests: true });
  assert.equal(calls[2].url, "https://example.test/api/v1/digest/batch/B1?include=digests");
  assert.equal(Object.keys(g.digests).length, 1);
  assert.equal((await ld.usage()).remaining, 7);
});

test("bad input is refused locally", () => {
  assert.throws(() => digestBody("", { format: "json" }), InvalidRequestError);
  assert.throws(() => digestBody("u", { format: "json", depth: "deep" }), InvalidRequestError);
  assert.throws(() => digestBody("u", { format: "json", maxCredits: 0 }), InvalidRequestError);
  assert.throws(() => digestBody("u", { format: "json", translateTo: "english" }), InvalidRequestError);
});
