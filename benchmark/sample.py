#!/usr/bin/env python3
"""Pick the benchmark's links by rule, before any reader is run.

The links are not chosen by whether LinkDigest can read them:

  bilibili     the first 6 videos of Bilibili's public "popular" list that are
               10 minutes or shorter (api.bilibili.com/x/web-interface/popular)
  douyin       the first 6 results of a topic search for 「家常菜 做法」
  xiaohongshu  the first 6 results of a topic search for 「咖啡 探店」
  youtube      the first 6 results of a topic search for 「如何学习编程」 (the control:
               a platform every tool can open)

The three searches go through LinkDigest's search endpoint, which asks a web
index and returns links with the index's own title; nothing is read at this
step. Every link sampled is kept, including the ones no tool can read.

    LINKDIGEST_API_KEY=ld_live_... python3 sample.py > links.json
"""
import datetime
import json
import os
import sys
import urllib.request

BASE = os.environ.get("LINKDIGEST_BASE", "https://linkdigest.dev")
KEY = os.environ.get("LINKDIGEST_API_KEY", "")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
PER_PLATFORM = 6
QUERIES = {"douyin": "家常菜 做法", "xiaohongshu": "咖啡 探店", "youtube": "如何学习编程"}


def get_json(url, headers=None, data=None, timeout=90):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"User-Agent": UA, "Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def bilibili():
    out = []
    page = get_json("https://api.bilibili.com/x/web-interface/popular?ps=20&pn=1")
    for v in page["data"]["list"]:
        if v["duration"] <= 600:
            out.append({"platform": "bilibili", "url": f"https://www.bilibili.com/video/{v['bvid']}",
                        "title": v["title"], "seconds": v["duration"], "kind": "video",
                        "rule": "Bilibili popular list, first 6 of 10 minutes or less"})
        if len(out) == PER_PLATFORM:
            break
    return out


def search(platform, query):
    if not KEY:
        sys.exit("LINKDIGEST_API_KEY is not set")
    res = get_json(f"{BASE}/api/v1/search", {"Authorization": f"Bearer {KEY}", "User-Agent": "linkdigest-benchmark/1.0"},
                   {"query": query, "platform": platform, "limit": PER_PLATFORM})
    rows = res.get("results") or res.get("links") or []
    return [{"platform": platform, "url": r["url"], "title": r.get("title") or "", "seconds": None, "kind": "unknown",
             "rule": f"topic search 「{query}」, first {PER_PLATFORM} results"} for r in rows[:PER_PLATFORM]]


if __name__ == "__main__":
    links = bilibili()
    for platform, query in QUERIES.items():
        links += search(platform, query)
    json.dump({"sampled_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "links": links},
              sys.stdout, ensure_ascii=False, indent=1)
