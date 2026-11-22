/**
 * linkdigest — a small TypeScript client for the hosted LinkDigest REST API.
 *
 * Nothing runs locally: every call goes to https://linkdigest.dev with your own API key, where the
 * media is fetched, transcribed and read. Zero dependencies; Node 18+ (global fetch), Deno, Bun,
 * edge runtimes and browsers that allow the request.
 *
 * A read answers in one of two ways:
 * - 200 with the digest. A link anyone has read before comes back in about a second and costs nothing.
 * - 202 with a job id, when the work takes longer than one request may last (long videos, image
 *   notes with many pictures). `digest()` then collects the job with
 *   GET /api/v1/digest/{jobId}?wait=20, which holds each request open for up to 20 seconds, and
 *   repeats until the digest is ready or `maxWait` runs out. Running out throws JobPendingError
 *   carrying the job id, so the work is collected later rather than paid for twice.
 */

export const VERSION = "0.1.0";
export const DEFAULT_BASE_URL = "https://linkdigest.dev";
export const KEYS_URL = "https://linkdigest.dev/signin?ref=sdk-js&next=/app/keys";
/** The server caps ?wait at 20 seconds (GET /api/v1/digest/{jobId}). */
export const POLL_WAIT_SECONDS = 20;
/** How long digest() keeps collecting a running job before throwing JobPendingError. */
export const DEFAULT_MAX_WAIT_SECONDS = 600;

export type Depth = "full" | "transcript" | "script";
export type Format = "json" | "markdown";
export type SearchPlatform = "douyin" | "xiaohongshu" | "youtube" | "x" | "tiktok" | "web" | string;

/** A timed piece of speech: `t` is seconds from the start. */
export interface TranscriptSegment {
  t: number;
  text: string;
  approx?: boolean;
}

/** A digest as the API returns it. Every field is optional because platforms differ. */
export interface Digest {
  url?: string;
  platform?: string;
  title?: string;
  author?: string;
  caption?: string;
  transcript?: TranscriptSegment[];
  on_screen?: Array<Record<string, unknown>>;
  images?: Array<Record<string, unknown>>;
  key_points?: string[];
  comments?: Array<Record<string, unknown>>;
  answer?: Record<string, unknown> | null;
  breakdown?: Record<string, unknown> | null;
  translation?: Record<string, unknown> | null;
  degraded?: string[];
  raw_markdown?: string;
  markdown?: string;
  [key: string]: unknown;
}

export interface DigestOptions {
  /** "json" (default) or "markdown". */
  format?: Format;
  /** "full" (default), "transcript" (long videos read in full with a few frames) or "script" (speech only). */
  depth?: Depth;
  /** A question to answer from the post; the answer comes with quotes checked against the post. +1 credit. */
  ask?: string;
  /** Also take the post apart (hook, timed beats, title formula). +1 credit. */
  breakdown?: boolean;
  /** Also translate, e.g. "en", "ja", "zh-CN". +1 credit. */
  translateTo?: string;
  /** Read the opening minutes the budget affords instead of refusing a long or costly video. */
  partialOk?: boolean;
  /** Your own ceiling for this link; over it is a 402 and costs nothing. */
  maxCredits?: number;
  /** Seconds to keep collecting a long job (default 600). 0 = throw JobPendingError at once. */
  maxWait?: number;
  /** Called each time the job is still running. */
  onPending?: (jobId: string, stage: string | null) => void;
  signal?: AbortSignal;
}

export interface SearchOptions {
  platform?: SearchPlatform;
  /** How many links to return (the API caps it). */
  limit?: number;
  /** Also read every result as one batch with a comparison; the response carries `batch_id`. */
  digest?: boolean;
  breakdown?: boolean;
  insight?: boolean;
  signal?: AbortSignal;
}

export interface SearchResult {
  url: string;
  title?: string;
  snippet?: string;
  posted_at?: string | null;
  [key: string]: unknown;
}

export interface SearchResponse {
  query?: string;
  platform?: string;
  results: SearchResult[];
  credits?: number;
  /** With `digest: true`: the batch started over the results. */
  batch_id?: string | null;
  [key: string]: unknown;
}

export interface BatchOptions {
  depth?: Depth;
  ask?: string;
  breakdown?: boolean;
  insight?: boolean;
  /** One comparison page across the links. */
  synthesis?: boolean;
  translateTo?: string;
  partialOk?: boolean;
  /** A public https URL to POST the finished batch to (signed). */
  webhookUrl?: string;
  signal?: AbortSignal;
}

export interface BatchItem {
  url: string;
  /** queued, running, done, cached (read before, 0 credits) or error. */
  status: string;
  credits?: number;
  error?: string | null;
  error_code?: string | null;
  cache_key?: string;
  [key: string]: unknown;
}

export interface Batch {
  batch_id: string;
  /** running or done. */
  status: string;
  total?: number;
  done?: number;
  failed?: number;
  credits_total?: number;
  items?: BatchItem[];
  /** With include=digests: every finished digest, keyed by its link (an object, not an array). */
  digests?: Record<string, Digest>;
  synthesis?: Record<string, unknown> | null;
  [key: string]: unknown;
}

export interface Usage {
  plan?: string;
  used?: number;
  limit?: number;
  remaining?: number;
  pack_credits?: number;
  key?: { monthly_cap?: number | null; used?: number; remaining?: number | null };
  failed?: Array<{ at?: string; url?: string; error_code?: string; message?: string }>;
  [key: string]: unknown;
}

export interface ClientOptions {
  /** Defaults to process.env.LINKDIGEST_API_KEY. */
  apiKey?: string;
  /** Defaults to process.env.LINKDIGEST_BASE_URL, then https://linkdigest.dev. */
  baseUrl?: string;
  /** Per-request timeout in seconds for calls that are not long-polls (default 60). */
  timeout?: number;
  /** Default for DigestOptions.maxWait (seconds). */
  maxWait?: number;
  /** Inject a fetch (tests, proxies). Defaults to globalThis.fetch. */
  fetch?: typeof fetch;
}

// ---------------------------------------------------------------- errors

export class LinkDigestError extends Error {
  readonly status: number | null;
  readonly errorCode: string | null;
  readonly body: Record<string, unknown>;
  constructor(message: string, status: number | null = null, errorCode: string | null = null, body: Record<string, unknown> = {}) {
    super(message);
    this.name = new.target.name;
    this.status = status;
    this.errorCode = errorCode;
    this.body = body;
  }
}
/** linkdigest.dev could not be reached (DNS, TLS, timeout, proxy). */
export class NetworkError extends LinkDigestError {}
/** 400: the request itself was wrong. */
export class InvalidRequestError extends LinkDigestError {}
/** 401: no API key, or one that was revoked. Issue one at KEYS_URL. */
export class AuthenticationError extends LinkDigestError {}
/**
 * 402: out of credits, or this link costs more than is left. Nothing was spent.
 * `buyUrl` opens checkout for a credit pack for this key's account with no sign-in; `subscribeUrl`
 * opens the monthly plan. `errorCode` is quota_exceeded, insufficient_credits or media_too_long.
 */
export class PaymentRequiredError extends LinkDigestError {
  get buyUrl(): string | null {
    return typeof this.body.buy_url === "string" ? this.body.buy_url : null;
  }
  get subscribeUrl(): string | null {
    return typeof this.body.subscribe_url === "string" ? this.body.subscribe_url : null;
  }
}
/** 422: the link was processed and there is nothing readable (removed, private, walled, not served). */
export class UnreadableLinkError extends LinkDigestError {}
/** 429: slow down. `retryAfter` is in seconds when the server said. */
export class RateLimitError extends LinkDigestError {
  readonly retryAfter: number | null;
  constructor(message: string, status: number | null, errorCode: string | null, body: Record<string, unknown>, retryAfter: number | null) {
    super(message, status, errorCode, body);
    this.retryAfter = retryAfter;
  }
}
/** 5xx: the service or its engine failed. Not your input; try again later. */
export class ServerError extends LinkDigestError {}
/**
 * The digest is still running after `maxWait` seconds. Nothing is lost: collect it later with
 * `client.collect(jobId)`. Re-sending the url would start the work again.
 */
export class JobPendingError extends LinkDigestError {
  readonly jobId: string;
  readonly stage: string | null;
  constructor(jobId: string, stage: string | null = null, waited = 0) {
    super(
      `still processing job ${jobId}${stage ? ` (${stage})` : ""} after ${Math.round(waited)}s — ` +
        `collect it later with collect("${jobId}") instead of re-sending the url`,
      202
    );
    this.jobId = jobId;
    this.stage = stage;
  }
}

/** Map an HTTP error response to the matching error. */
export function errorFor(status: number, body: Record<string, unknown>, text: string, retryAfter: number | null = null): LinkDigestError {
  const message = String(body.error || text || `HTTP ${status}`).trim().slice(0, 1000);
  const code = typeof body.error_code === "string" ? body.error_code : null;
  if (status === 401) return new AuthenticationError(`${message} — issue a key at ${KEYS_URL}`, status, code, body);
  if (status === 402) {
    const pay = (body.buy_url || body.subscribe_url) as string | undefined;
    return new PaymentRequiredError(pay ? `${message} Pay here (no sign-in): ${pay}` : message, status, code, body);
  }
  if (status === 429) return new RateLimitError(message, status, code, body, retryAfter);
  if (status === 422) return new UnreadableLinkError(message, status, code, body);
  if (status >= 500) return new ServerError(message, status, code, body);
  return new InvalidRequestError(message, status, code, body);
}

// ---------------------------------------------------------------- client

const TRANSLATE_TO = /^[a-z]{2}(-[A-Z]{2})?$/;
const env = (name: string): string | undefined =>
  (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env?.[name];
const sleep = (seconds: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    if (signal?.aborted) return reject(signal.reason ?? new Error("aborted"));
    const t = setTimeout(resolve, Math.max(0, seconds) * 1000);
    signal?.addEventListener("abort", () => (clearTimeout(t), reject(signal.reason ?? new Error("aborted"))), { once: true });
  });

interface Sent {
  res: Response;
  elapsed: number;
}

export class LinkDigest {
  readonly baseUrl: string;
  readonly timeout: number;
  readonly maxWait: number;
  readonly #key: string;
  readonly #fetch: typeof fetch;

  constructor(options: ClientOptions = {}) {
    const key = (options.apiKey ?? env("LINKDIGEST_API_KEY") ?? "").trim();
    if (!key) throw new AuthenticationError(`no API key: pass { apiKey } or set LINKDIGEST_API_KEY — issue one at ${KEYS_URL}`, 401);
    this.#key = key;
    this.baseUrl = (options.baseUrl ?? env("LINKDIGEST_BASE_URL") ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.timeout = options.timeout ?? 60;
    this.maxWait = options.maxWait ?? DEFAULT_MAX_WAIT_SECONDS;
    const f = options.fetch ?? (globalThis.fetch as typeof fetch | undefined);
    if (!f) throw new LinkDigestError("no fetch in this runtime: use Node 18+ or pass { fetch }");
    this.#fetch = f;
  }

  /** Never shows the key. */
  toString(): string {
    return `LinkDigest(${this.baseUrl})`;
  }

  /** Read one link. Resolves when the digest is ready, or throws JobPendingError after `maxWait`. */
  async digest(url: string, options: DigestOptions = {}): Promise<Digest> {
    const format = options.format ?? "json";
    const body = digestBody(url, { ...options, format });
    const { res } = await this.#send("POST", "/api/v1/digest", body, undefined, options.signal);
    if (res.status === 202) {
      const pending = await jsonOrEmpty(res);
      const jobId = String(pending.jobId ?? "");
      if (!jobId) throw new ServerError("the API answered 202 without a job id", 202, null, pending);
      const stage = (pending.stage as string | undefined) ?? null;
      options.onPending?.(jobId, stage);
      const limit = options.maxWait ?? this.maxWait;
      if (limit <= 0) throw new JobPendingError(jobId, stage);
      return this.collect(jobId, { format, maxWait: limit, onPending: options.onPending, signal: options.signal });
    }
    return finish(res, format);
  }

  /** Collect a digest that is already running, by the job id a 202 gave you. Never re-sends the url. */
  async collect(
    jobId: string,
    options: { format?: Format; maxWait?: number; onPending?: DigestOptions["onPending"]; signal?: AbortSignal } = {}
  ): Promise<Digest> {
    const id = (jobId || "").trim();
    if (!id) throw new InvalidRequestError("jobId is required", 400);
    const format = options.format ?? "json";
    if (format !== "json" && format !== "markdown") throw new InvalidRequestError('format must be "json" or "markdown"', 400);
    const limit = options.maxWait ?? this.maxWait;
    const path = `/api/v1/digest/${encodeURIComponent(id)}?format=${format}&wait=${POLL_WAIT_SECONDS}`;
    const start = Date.now();
    const waited = () => (Date.now() - start) / 1000;
    let failures = 0;
    for (;;) {
      let sent: Sent;
      try {
        // The server may hold this request for POLL_WAIT_SECONDS.
        sent = await this.#send("GET", path, undefined, Math.max(this.timeout, POLL_WAIT_SECONDS + 30), options.signal);
      } catch (err) {
        // Collecting is idempotent, so a dropped connection is retried.
        if (!(err instanceof NetworkError)) throw err;
        failures += 1;
        if (failures > 3 || waited() >= limit) throw err;
        await sleep(5 * failures, options.signal);
        continue;
      }
      const { res } = sent;
      if ([502, 503, 504].includes(res.status) && failures < 3 && waited() < limit) {
        failures += 1;
        await sleep(5 * failures, options.signal);
        continue;
      }
      failures = 0;
      if (res.status !== 202) return finish(res, format);
      const pending = await jsonOrEmpty(res);
      const stage = (pending.stage as string | undefined) ?? null;
      options.onPending?.(id, stage);
      if (waited() >= limit) throw new JobPendingError(id, stage, waited());
      // ?wait=20 normally holds the request until the job settles; only pause when the server
      // answered early, so the loop does not spin.
      if (sent.elapsed < 5) await sleep(Math.min(retryAfter(res, pending, 10), Math.max(0, limit - waited())), options.signal);
    }
  }

  /** Find posts on a topic. With `digest: true` the results are also read as one batch (see `batch_id`). */
  async search(query: string, options: SearchOptions = {}): Promise<SearchResponse> {
    if (typeof query !== "string" || !query.trim()) throw new InvalidRequestError("query is required", 400);
    const body: Record<string, unknown> = { query: query.trim() };
    if (options.platform) body.platform = options.platform;
    if (options.limit !== undefined) body.limit = options.limit;
    if (options.digest) body.digest = true;
    if (options.breakdown) body.breakdown = true;
    if (options.insight) body.insight = true;
    const { res } = await this.#send("POST", "/api/v1/search", body, undefined, options.signal);
    return (await okJson(res)) as SearchResponse;
  }

  /** Start reading many links as one batch. Collect it with getBatch() or waitForBatch(). */
  async batch(urls: string[], options: BatchOptions = {}): Promise<Batch> {
    if (!Array.isArray(urls) || urls.length === 0 || urls.some((u) => typeof u !== "string" || !u.trim()))
      throw new InvalidRequestError("urls must be a non-empty list of links", 400);
    const body: Record<string, unknown> = { urls: urls.map((u) => u.trim()) };
    if (options.depth && options.depth !== "full") body.depth = options.depth;
    if (options.ask?.trim()) body.ask = options.ask.trim().slice(0, 300);
    if (options.breakdown) body.breakdown = true;
    if (options.insight) body.insight = true;
    if (options.synthesis) body.synthesis = true;
    if (options.partialOk) body.partial_ok = true;
    if (options.translateTo) body.translate_to = checkLang(options.translateTo);
    if (options.webhookUrl) body.webhook_url = options.webhookUrl;
    const { res } = await this.#send("POST", "/api/v1/digest/batch", body, undefined, options.signal);
    return (await okJson(res)) as Batch;
  }

  /** A batch's state; with `includeDigests` every finished digest, keyed by its link. */
  async getBatch(batchId: string, options: { includeDigests?: boolean; signal?: AbortSignal } = {}): Promise<Batch> {
    const id = (batchId || "").trim();
    if (!id) throw new InvalidRequestError("batchId is required", 400);
    const q = options.includeDigests ? "?include=digests" : "";
    const { res } = await this.#send("GET", `/api/v1/digest/batch/${encodeURIComponent(id)}${q}`, undefined, undefined, options.signal);
    return (await okJson(res)) as Batch;
  }

  /** Poll a batch until it is done (default every 30 s, up to 15 minutes), then return it with its digests. */
  async waitForBatch(batchId: string, options: { interval?: number; maxWait?: number; signal?: AbortSignal } = {}): Promise<Batch> {
    const interval = options.interval ?? 30;
    const limit = options.maxWait ?? 900;
    const start = Date.now();
    for (;;) {
      const b = await this.getBatch(batchId, { includeDigests: true, signal: options.signal });
      if (b.status === "done") return b;
      const waited = (Date.now() - start) / 1000;
      if (waited >= limit) throw new JobPendingError(batchId, b.status, waited);
      await sleep(Math.min(interval, limit - waited), options.signal);
    }
  }

  /** Credits used and remaining for this key's account, and the key's last failed reads. */
  async usage(options: { signal?: AbortSignal } = {}): Promise<Usage> {
    const { res } = await this.#send("GET", "/api/v1/usage", undefined, undefined, options.signal);
    return (await okJson(res)) as Usage;
  }

  /** Validate the key without starting a read or spending a credit. */
  async checkKey(options: { signal?: AbortSignal } = {}): Promise<Record<string, unknown>> {
    const { res } = await this.#send("GET", "/api/v1/digest/credential-check", undefined, undefined, options.signal);
    return okJson(res);
  }

  async #send(method: string, path: string, body?: unknown, timeoutSeconds?: number, signal?: AbortSignal): Promise<Sent> {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(new Error("timeout")), (timeoutSeconds ?? this.timeout) * 1000);
    const onAbort = () => ctrl.abort(signal?.reason);
    signal?.addEventListener("abort", onAbort, { once: true });
    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.#key}`,
      Accept: "application/json, text/markdown",
      "User-Agent": `linkdigest-js/${VERSION}`,
    };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const t0 = Date.now();
    try {
      const res = await this.#fetch(this.baseUrl + path, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: ctrl.signal,
      });
      return { res, elapsed: (Date.now() - t0) / 1000 };
    } catch (err) {
      if (signal?.aborted) throw err;
      throw new NetworkError(`could not reach ${this.baseUrl}: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
    }
  }
}

// ---------------------------------------------------------------- helpers

function checkLang(code: string): string {
  if (!TRANSLATE_TO.test(code)) throw new InvalidRequestError("translateTo must be a language code like en, ja or zh-CN", 400);
  return code;
}

/** The request body for POST /api/v1/digest; optional fields are sent only when set. */
export function digestBody(url: string, o: DigestOptions & { format: Format }): Record<string, unknown> {
  if (typeof url !== "string" || !url.trim()) throw new InvalidRequestError("url is required", 400);
  if (o.format !== "json" && o.format !== "markdown") throw new InvalidRequestError('format must be "json" or "markdown"', 400);
  const body: Record<string, unknown> = { url: url.trim(), format: o.format };
  if (o.translateTo) body.translate_to = checkLang(o.translateTo);
  if (o.breakdown) body.breakdown = true;
  if (o.ask !== undefined) {
    if (typeof o.ask !== "string") throw new InvalidRequestError("ask must be a string", 400);
    const a = o.ask.split(/\s+/).filter(Boolean).join(" ");
    if (a) body.ask = a.slice(0, 300);
  }
  if (o.partialOk) body.partial_ok = true;
  const depth = o.depth ?? "full";
  if (!["full", "transcript", "script"].includes(depth)) throw new InvalidRequestError('depth must be "full", "transcript" or "script"', 400);
  if (depth !== "full") body.depth = depth;
  if (o.maxCredits !== undefined) {
    if (!Number.isInteger(o.maxCredits) || o.maxCredits < 1) throw new InvalidRequestError("maxCredits must be a whole number >= 1", 400);
    body.max_credits = o.maxCredits;
  }
  return body;
}

async function jsonOrEmpty(res: Response): Promise<Record<string, unknown>> {
  try {
    const data = await res.json();
    return data && typeof data === "object" && !Array.isArray(data) ? (data as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

function retryAfter(res: Response, body: Record<string, unknown>, fallback: number): number {
  for (const raw of [res.headers.get("retry-after"), body.retryAfter]) {
    const n = Number(raw);
    if (raw !== null && raw !== undefined && raw !== "" && Number.isFinite(n)) return Math.max(0, n);
  }
  return fallback;
}

async function errorFrom(res: Response): Promise<LinkDigestError> {
  const text = await res.text();
  let body: Record<string, unknown> = {};
  try {
    const parsed = JSON.parse(text);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) body = parsed;
  } catch {
    /* not JSON */
  }
  const ra = retryAfter(res, body, -1);
  return errorFor(res.status, body, Object.keys(body).length ? "" : text, ra < 0 ? null : ra);
}

async function okJson(res: Response): Promise<Record<string, unknown>> {
  if (res.status >= 400) throw await errorFrom(res);
  return jsonOrEmpty(res);
}

async function finish(res: Response, format: Format): Promise<Digest> {
  if (res.status >= 400) throw await errorFrom(res);
  if (res.status !== 200) throw new ServerError(`unexpected HTTP ${res.status} from the API`, res.status);
  const ctype = res.headers.get("content-type") ?? "";
  if (format === "markdown" && !ctype.includes("json")) return { markdown: await res.text() };
  return (await jsonOrEmpty(res)) as Digest;
}

export default LinkDigest;
