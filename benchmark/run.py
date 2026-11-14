#!/usr/bin/env python3
"""Run every link in links.json through four readers and keep what each returned.

  linkdigest   POST /api/v1/digest (needs LINKDIGEST_API_KEY), max_credits 12 per link
  jina         GET https://r.jina.ai/<url>   (Jina Reader, no key; X-Locale zh-CN so it is served the Chinese page)
  fetch        one HTTP GET with a desktop browser User-Agent (what a model's own page fetch sees)
  ytdlp        yt-dlp --skip-download --dump-json (metadata and the caption tracks it lists)

Raw outputs go to raw/<nn>-<platform>/; nothing is scored here (score.py does that
from the files, so the scoring can be re-run and checked without re-reading).

    LINKDIGEST_API_KEY=ld_live_... python3 run.py            # everything
    python3 run.py --only jina,fetch,ytdlp                    # the keyless readers
"""
import gzip
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
BASE = os.environ.get("LINKDIGEST_BASE", "https://linkdigest.dev")
KEY = os.environ.get("LINKDIGEST_API_KEY", "")
BROWSER = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
MAX_CREDITS = 12
KEEP = 200_000          # characters kept of a text output
only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else {"linkdigest", "jina", "fetch", "ytdlp"}


def unzip(raw):
    """Some sites (Bilibili) answer gzip whether asked or not; a reader that did not unpack it would be scored on noise."""
    if raw[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(raw)
        except OSError:
            return raw
    return raw


def http(method, url, headers, body=None, timeout=90):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, unzip(r.read())
    except urllib.error.HTTPError as e:
        return e.code, unzip(e.read())
    except Exception as e:  # timeouts, resets: recorded, not hidden
        return 0, f"{type(e).__name__}: {e}".encode()


def linkdigest(url):
    h = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "User-Agent": "linkdigest-benchmark/1.0"}
    status, raw = http("POST", f"{BASE}/api/v1/digest", h, {"url": url, "format": "json", "max_credits": MAX_CREDITS}, timeout=120)
    deadline = time.time() + 420
    poll = None
    while status == 202 and time.time() < deadline:
        poll = json.loads(raw).get("poll_url") or poll     # the first 202 names the poll address; later ones only say "still running"
        status, raw = http("GET", poll + ("&" if "?" in poll else "?") + "wait=20", h, timeout=60)
    return status, raw.decode("utf-8", "replace")


def jina(url):
    status, raw = http("GET", "https://r.jina.ai/" + url, {"User-Agent": "linkdigest-benchmark/1.0", "Accept": "text/plain", "X-Locale": "zh-CN"}, timeout=90)
    return status, raw.decode("utf-8", "replace")[:KEEP]


def fetch(url):
    status, raw = http("GET", url, {"User-Agent": BROWSER, "Accept": "text/html,application/xhtml+xml", "Accept-Language": "zh-CN,zh;q=0.9"}, timeout=40)
    return status, raw.decode("utf-8", "replace")[:KEEP]


def ytdlp(url):
    try:
        p = subprocess.run(["yt-dlp", "--skip-download", "--dump-json", "--no-warnings", "--socket-timeout", "30", url],
                           capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return 0, "TimeoutExpired"
    if p.returncode != 0:
        return 1, (p.stderr or p.stdout)[-2000:]
    d = json.loads(p.stdout.splitlines()[0])
    keep = {k: d.get(k) for k in ("id", "title", "description", "duration", "uploader", "view_count", "like_count", "comment_count")}
    keep["subtitles"] = sorted((d.get("subtitles") or {}).keys())
    keep["automatic_captions"] = sorted((d.get("automatic_captions") or {}).keys())[:12]
    return 200, json.dumps(keep, ensure_ascii=False)


READERS = {"linkdigest": (linkdigest, "json"), "jina": (jina, "txt"), "fetch": (fetch, "html"), "ytdlp": (ytdlp, "json")}

if __name__ == "__main__":
    links = json.loads((HERE / "links.json").read_text())["links"]
    if "linkdigest" in only and not KEY:
        sys.exit("LINKDIGEST_API_KEY is not set (or pass --only jina,fetch,ytdlp)")
    log = []
    for n, link in enumerate(links, 1):
        d = HERE / "raw" / f"{n:02d}-{link['platform']}"
        d.mkdir(parents=True, exist_ok=True)
        for name, (fn, ext) in READERS.items():
            if name not in only:
                continue
            out = d / f"{name}.{ext}"
            meta = d / f"{name}.meta.json"
            if meta.exists():            # a re-run keeps what is already on disk
                continue
            t = time.time()
            status, text = fn(link["url"])
            took = round(time.time() - t, 1)
            out.write_text(text)
            meta.write_text(json.dumps({"reader": name, "url": link["url"], "status": status, "seconds": took, "chars": len(text),
                                        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
            print(f"{n:02d} {link['platform']:<11} {name:<10} status {status} · {took:>6}s · {len(text):>7} chars", flush=True)
            if name == "jina":
                time.sleep(4)            # keyless Jina Reader allows about 20 requests a minute
