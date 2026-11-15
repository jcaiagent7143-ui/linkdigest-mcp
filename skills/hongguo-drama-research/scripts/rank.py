#!/usr/bin/env python3
"""红果短剧榜单 → the top dramas read in one batch, with viewers' reviews and one comparison.

    python3 scripts/rank.py                                   # AI剧 (default), top 12
    python3 scripts/rank.py --page real --top 20              # 真人剧
    python3 scripts/rank.py --page https://hongguoduanju.com/category/comic-drama
    python3 scripts/rank.py --format json > rank.json         # the batch JSON

What it reads: the public drama pages (hongguoduanju.com/detail?series_id=…) —
synopsis, tags, episode count, score and raters, likes, saves, heat, rank,
the top written reviews. It never opens an episode: the players are what the
site's robots.txt disallows, and the dramas are the rights holder's.

Standard library only. Reads LINKDIGEST_API_KEY. The ranking page is fetched
once, from your machine; the drama pages are read by linkdigest.dev.
Each drama is 1 credit, +1 for the review insight; the comparison is 1 per
started ten dramas. A drama already read by anyone is free.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import linkdigest as ld  # noqa: E402

BATCH = "https://linkdigest.dev/api/v1/digest/batch"
PAGES = {
    "home": "https://hongguoduanju.com/",
    "ai": "https://hongguoduanju.com/category/ai-drama",
    "real": "https://hongguoduanju.com/category/real-drama",
    "comic": "https://hongguoduanju.com/category/comic-drama",
}
DETAIL = "https://hongguoduanju.com/detail?series_id={}"


def series_ids(page_url: str, top: int) -> list[str]:
    req = urllib.request.Request(page_url, headers={"User-Agent": "Mozilla/5.0 (compatible; LinkDigest-skill/1.0)"})
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
    seen: list[str] = []
    for sid in re.findall(r"/detail\?series_id=(\d+)", html):
        if sid not in seen:
            seen.append(sid)
    return seen[:top]


def facts(caption: str) -> str:
    """The numbers line the drama page carries (集数 · 评分 · 热度 · 榜单)."""
    last = (caption or "").strip().split("\n")[-1]
    return last if ("集" in last and "·" in last) else ""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="红果短剧榜单：前 N 部剧的简介、评分、热度和剧评，读完出一页对比")
    p.add_argument("--page", default="ai", help="ai / real / comic / home，或一个 hongguoduanju.com 榜单、分类页地址")
    p.add_argument("--top", type=int, default=12, help="读前几部（默认 12，最多 24）")
    p.add_argument("--no-insight", action="store_true", help="不做剧评洞察（每部少 1 积分）")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p.add_argument("--timeout", type=int, default=900)
    args = p.parse_args(argv)

    key = os.environ.get("LINKDIGEST_API_KEY", "").strip()
    if not key:
        ld.log(f"需要 LINKDIGEST_API_KEY：在 {ld.KEYS_URL} 创建，然后 export LINKDIGEST_API_KEY=ld_live_...")
        return ld.EXIT_USAGE
    page = PAGES.get(args.page, args.page)
    if not page.startswith("https://hongguoduanju.com/"):
        ld.log("--page 只接受 ai / real / comic / home，或 hongguoduanju.com 的榜单、分类页地址。")
        return ld.EXIT_USAGE
    try:
        ids = series_ids(page, max(2, min(24, args.top)))
    except (urllib.error.URLError, OSError) as err:
        ld.log(f"打不开榜单页 {page}: {err}")
        return ld.EXIT_ERROR
    if len(ids) < 2:
        ld.log("榜单页上没找到剧（至少要 2 部）。")
        return ld.EXIT_ERROR
    links = [DETAIL.format(s) for s in ids]
    label = f"红果 {args.page} 前 {len(links)}"
    body = {"urls": links, "synthesis": True, "insight": not args.no_insight, "label": label}
    status, _, payload = ld.call("POST", BATCH, key, body, timeout=120)
    if status == 401:
        ld.log(f"Key 无效（401）。在 {ld.KEYS_URL} 重新创建。")
        return ld.EXIT_AUTH
    if status == 402:
        ld.log(f"积分不够（402，未扣费）：{ld.field(payload, 'error', '')}")
        return ld.EXIT_PAYMENT
    if status not in (200, 202):
        ld.log(f"提交失败（HTTP {status}）：{ld.field(payload, 'error', payload)}")
        return ld.EXIT_ERROR
    batch_id = ld.field(payload, "batch_id", "")
    ld.log(f"已提交 {len(links)} 部剧，批次 {batch_id}，正在读…")
    deadline = time.time() + args.timeout
    state = payload
    while time.time() < deadline:
        _, _, state = ld.call("GET", f"{BATCH}/{batch_id}", key, None, timeout=60)
        synth = ld.field(state, "synthesis", None) or {}
        if ld.field(state, "status", "") == "done" and (not synth or synth.get("status") not in ("running", "pending")):
            break
        time.sleep(6)
    else:
        ld.log(f"还没读完，稍后接着取：GET {BATCH}/{batch_id}")
        return ld.EXIT_TIMEOUT
    try:
        _, _, full = ld.call("GET", f"{BATCH}/{batch_id}?include=digests", key, None, timeout=60)
        if isinstance(full, dict) and isinstance(full.get("digests"), dict):
            state = full
    except (urllib.error.URLError, OSError):
        pass

    if args.format == "json":
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return ld.EXIT_OK
    digests = ld.field(state, "digests", None)
    digests = digests if isinstance(digests, dict) else {}
    print(f"# 红果短剧榜单：{label}\n")
    print("| # | 剧名 | 集数 · 评分 · 热度 · 榜单 | 标签 |\n|---|---|---|---|")
    for i, url in enumerate(links, 1):
        d = digests.get(url) or {}
        print(f"| {i} | {d.get('title') or url} | {facts(d.get('caption') or '')} | {' / '.join(d.get('tags') or [])} |")
    synth = ld.field(state, "synthesis", None) or {}
    text = synth.get("raw_markdown") or synth.get("summary") or ""
    print("\n## 对比\n")
    print(text or f"（没有生成对比：{ld.field(state, 'synthesis_error', '')}）")
    ld.log(f"完成：{ld.field(state, 'done', 0)} 部读到，{ld.field(state, 'failed', 0)} 部没读到；共 {ld.field(state, 'credits_total', 0)} 积分。")
    return ld.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
