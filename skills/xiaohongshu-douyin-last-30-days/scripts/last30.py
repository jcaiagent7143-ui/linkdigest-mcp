#!/usr/bin/env python3
"""What Xiaohongshu and Douyin posted about a topic in the last N days (LinkDigest API).

    python3 last30.py "Claude Code"                    # search both, read the 6 newest, print an evidence pack
    python3 last30.py "露营装备" --days 14 --read 4
    python3 last30.py "扫地机器人" --read 0             # list what was found, read nothing
    python3 last30.py "AI 编程" --platforms douyin --format json
    python3 last30.py "Claude Code" --brief             # one hosted run: ranked, summed up, every quote checked

Search finds the posts (it knows each post's date from its id, so the window is exact); the reads
bring back what was said (speech as text, the words in the images) and the like / comment / save
counts. The output is ranked by those counts. Writing the brief is the agent's job.

Standard library only. Reads LINKDIGEST_API_KEY; talks only to linkdigest.dev.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import linkdigest as ld  # noqa: E402

PULSE = "https://linkdigest.dev/api/v1/pulse"
SEARCH = "https://linkdigest.dev/api/v1/search"
DIGEST = "https://linkdigest.dev/api/v1/digest"
NAMES = {"xiaohongshu": "小红书", "douyin": "抖音"}
COUNT_WORDS = ("likes", "comments", "saves", "shares")


def _num(text: str) -> int:
    """'3,457' / '1.2万' / '12k' as an integer."""
    t = text.replace(",", "").strip().lower()
    m = re.fullmatch(r"([\d.]+)\s*([kw万]?)", t)
    if not m:
        return 0
    return int(float(m.group(1)) * {"": 1, "k": 1_000, "w": 10_000, "万": 10_000}[m.group(2)])


def counts_of(digest: dict) -> dict:
    """Likes, comments, saves and shares of a read: the `stats` object when there is one, else the Engagement line."""
    out = {}
    stats = digest.get("stats") if isinstance(digest.get("stats"), dict) else {}
    for want, keys in (("likes", ("likes", "like_count", "liked")), ("comments", ("comments", "comment_count")),
                       ("saves", ("saves", "collects", "collect_count", "favorites")), ("shares", ("shares", "share_count"))):
        for k in keys:
            if isinstance(stats.get(k), (int, float)):
                out[want] = int(stats[k])
                break
    line = re.search(r"\*\*Engagement:\*\*([^\n]+)", str(digest.get("raw_markdown") or ""))
    if line:
        for value, word in re.findall(r"([\d.,]+\s*[kKwW万]?)\s+(likes|comments|saves|shares)", line.group(1)):
            out.setdefault(word, _num(value))
    return out


def score(c: dict) -> int:
    """One number to sort by: a comment is worth two likes, a save or a share one. Shown beside the raw counts."""
    return c.get("likes", 0) + 2 * c.get("comments", 0) + c.get("saves", 0) + c.get("shares", 0)


def search(key: str, topic: str, platform: str, days: int, limit: int):
    # The API reads the window from the words of the query ("最近 30 天"), and dates each post from its id.
    status, _, payload = ld.call("POST", SEARCH, key, {"query": f"{topic} 最近 {days} 天", "platform": platform, "limit": limit}, timeout=150)
    return status, payload


def read(key: str, url: str, platform: str, max_credits: int, timeout: int = 600):
    body = {"url": url, "format": "json", "max_credits": max_credits}
    if platform == "douyin":
        body["depth"] = "script"  # the speech only: what was said, at the lowest price
    status, _, payload = ld.call("POST", DIGEST, key, body, timeout=120)
    started = time.time()
    while status == 202 and time.time() - started < timeout:
        poll = ld.field(payload, "poll_url") or (DIGEST + "/" + str(ld.field(payload, "jobId", "")))
        time.sleep(3)
        status, _, payload = ld.call("GET", poll + ("&" if "?" in poll else "?") + "wait=20", key, timeout=60)
    return status, payload


def brief(key: str, topic: str, days: int, platforms: list[str], read_n: int, hackernews: bool, fmt: str) -> int:
    """One hosted run (Topic Pulse, 近期热议): the server searches with the window, drops every
    post dated outside it before a read is paid for, reads the rest, ranks every item in code and
    writes a brief whose every point quotes its posts (the quotes are checked against the posts'
    own words). Prints the report; the run's cost is on its first lines."""
    size = "quick" if read_n <= 6 else "standard" if read_n <= 12 else "deep"
    body = {"topic": topic, "days": days, "size": size, "sources": platforms + (["hackernews"] if hackernews else [])}
    try:
        status, _headers, payload = ld.call("POST", PULSE, key, body, timeout=60)
    except (urllib.error.URLError, OSError) as err:
        ld.log(f"连不上 linkdigest.dev: {err}{ld.net_hint(err)}")
        return ld.EXIT_ERROR
    if status == 401:
        ld.log(f"Key 无效（401）。在 {ld.KEYS_URL} 重新创建。")
        return ld.EXIT_AUTH
    if status == 402:
        ld.log(f"积分不够这次运行（402，未扣费）：{ld.field(payload, 'error', '')} 付款链接：{ld.field(payload, 'starter_url', '') or ld.field(payload, 'buy_url', '')}")
        return ld.EXIT_PAYMENT
    if status != 202 or not ld.field(payload, "pulse_id"):
        ld.log(f"没能开始（HTTP {status}）：{str(ld.field(payload, 'error', ''))[:200]}")
        return ld.EXIT_ERROR
    poll = ld.field(payload, "poll") or f"{PULSE}/{payload['pulse_id']}"
    ld.log(f"已开始：预计约 {ld.field(payload, 'estimate', '?')} 积分，窗口 {ld.field(payload, 'window', {})}；一般 2–5 分钟")
    deadline, last = time.time() + 20 * 60, ""
    while time.time() < deadline:
        time.sleep(10)
        try:
            status, _headers, payload = ld.call("GET", poll, key, timeout=60)
        except (urllib.error.URLError, OSError):
            continue  # one lost poll is not the end of the run
        state = ld.field(payload, "status", "")
        if state != last:
            last = state
            ld.log({"searching": "搜索中…", "reading": "在读帖子…", "aggregating": "在写总结…"}.get(state, state))
        if state in ("done", "failed"):
            break
    else:
        ld.log(f"20 分钟还没结束，先停在这里；稍后用同一个 Key GET {poll} 取结果。")
        return ld.EXIT_ERROR
    if fmt == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return ld.EXIT_OK if state == "done" else ld.EXIT_ERROR
    if state == "failed":
        print(f"# 近 {days} 天：{topic}\n\n没有写成总结：{ld.field(payload, 'error', '')}\n\n花了 {ld.field(payload, 'credits_total', 0)} 积分。\n")
        for c in ld.field(payload, "coverage", []) or []:
            print(f"- {c.get('source')}: {c.get('state')} · found {c.get('found')} · in window {c.get('in_window')}" + (f" · {c['note']}" if c.get("note") else ""))
        return ld.EXIT_ERROR
    try:
        status, _headers, text = ld.call("GET", poll + "?format=md", key, timeout=60)
    except (urllib.error.URLError, OSError) as err:
        ld.log(f"结果已生成，但取 Markdown 时断了：{err}。GET {poll}?format=md 再取一次。")
        return ld.EXIT_ERROR
    print(text if isinstance(text, str) else (ld.field(ld.field(payload, "pulse", {}) or {}, "markdown", "") or json.dumps(payload, ensure_ascii=False)))
    if ld.field(payload, "share_url"):
        print(f"\n分享链接（不用登录就能打开，30 天有效）：{payload['share_url']}")
    return ld.EXIT_OK


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="近 N 天小红书 / 抖音在说什么 · the last N days on Xiaohongshu and Douyin")
    p.add_argument("topic", help="话题、产品、品牌或人名，如 Claude Code、露营装备")
    p.add_argument("--days", type=int, default=30, help="往回看几天（1–365，默认 30）")
    p.add_argument("--platforms", default="xiaohongshu,douyin", help="xiaohongshu,douyin 之一或两个（默认两个）")
    p.add_argument("--read", type=int, default=6, help="读最新的几条（默认 6；0 = 只列出找到的，不读）")
    p.add_argument("--max-credits", type=int, default=8, help="每条最多花多少积分，超过的不读、不扣费（默认 8）")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p.add_argument("--brief", action="store_true", help="交给服务器一次做完：按热度排序、写好总结、每条引用都核对过（近期热议）")
    p.add_argument("--hackernews", action="store_true", help="只和 --brief 一起用：再加上 Hacker News 上的讨论（免费）")
    args = p.parse_args(argv)

    key = os.environ.get("LINKDIGEST_API_KEY", "").strip()
    if not key:
        ld.log(f"需要 LINKDIGEST_API_KEY：在 {ld.KEYS_URL} 创建（注册送 10 积分，不用卡），然后 export LINKDIGEST_API_KEY=ld_live_...")
        return ld.EXIT_USAGE
    platforms = [x.strip() for x in args.platforms.split(",") if x.strip()]
    if not platforms or any(x not in NAMES for x in platforms) or not 1 <= args.days <= 365 or not 0 <= args.read <= 20:
        ld.log("--platforms 只能是 xiaohongshu、douyin；--days 是 1 到 365；--read 是 0 到 20")
        return ld.EXIT_USAGE

    if args.brief:
        if args.days > 90 or args.read < 1:
            ld.log("--brief 的时间窗是 1 到 90 天，--read 至少 1（6 条以内 quick，12 条以内 standard，再多 deep）")
            return ld.EXIT_USAGE
        return brief(key, args.topic, args.days, platforms, args.read, args.hackernews, args.format)

    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)).date().isoformat()
    found, searched, spent = [], [], 0
    for platform in platforms:
        try:
            status, payload = search(key, args.topic, platform, args.days, 10)
        except (urllib.error.URLError, OSError) as err:
            ld.log(f"连不上 linkdigest.dev: {err}{ld.net_hint(err)}")
            return ld.EXIT_ERROR
        if status == 401:
            ld.log(f"Key 无效（401）。在 {ld.KEYS_URL} 重新创建。")
            return ld.EXIT_AUTH
        if status == 402:
            ld.log(f"积分不够这次搜索（402，未扣费）：{ld.field(payload, 'error', '')} 付款链接：{ld.field(payload, 'starter_url', '') or ld.field(payload, 'buy_url', '')}")
            return ld.EXIT_PAYMENT
        if status != 200:
            searched.append({"platform": platform, "found": 0, "in_window": 0, "note": f"search answered HTTP {status}: {str(ld.field(payload, 'error', ''))[:120]}"})
            continue
        results = ld.field(payload, "results", []) or []
        spent += int(ld.field(payload, "credits", 0) or 0)
        inside = [r for r in results if not r.get("posted_at") or r["posted_at"] >= cutoff]
        searched.append({"platform": platform, "found": len(results), "in_window": len(inside), "undated": sum(1 for r in inside if not r.get("posted_at"))})
        found += [{"platform": platform, "url": r.get("url"), "title": r.get("title") or "", "posted_at": r.get("posted_at")} for r in inside if r.get("url")]

    # Newest first, taking turns between the platforms so one cannot crowd the other out.
    by_platform = {x: sorted((f for f in found if f["platform"] == x), key=lambda f: f["posted_at"] or "", reverse=True) for x in platforms}
    order = []
    while any(by_platform.values()):
        for x in platforms:
            if by_platform[x]:
                order.append(by_platform[x].pop(0))

    posts, skipped = [], []
    for item in order[: args.read]:
        ld.log(f"读 {NAMES[item['platform']]} {item['posted_at'] or '日期未知'} {item['title'][:30]}")
        try:
            status, d = read(key, item["url"], item["platform"], args.max_credits)
        except (urllib.error.URLError, OSError) as err:
            skipped.append({**item, "why": f"network: {err}"})
            continue
        if status != 200:
            skipped.append({**item, "why": f"HTTP {status}: {str(ld.field(d, 'error', ''))[:140]}"})
            if status == 402 and ld.field(d, "error_code") != "media_too_long" and "max_credits" not in str(ld.field(d, "error", "")):
                ld.log("积分不够，后面的不读了。")
                break
            continue
        spent += int(d.get("credits") or 0)
        counts = counts_of(d)
        support = [s for s in (d.get("key_point_support") or []) if isinstance(s, dict) and s.get("quote")]
        quotes = [{"t": s.get("t"), "text": str(s["quote"])[:160]} for s in support[:3]]
        if not quotes:
            quotes = [{"t": seg.get("t"), "text": str(seg.get("text", ""))[:160]} for seg in (d.get("transcript") or [])[:2] if isinstance(seg, dict)]
        posted = d.get("posted_at") or item["posted_at"]
        posts.append({
            "platform": item["platform"], "url": d.get("source_url") or item["url"], "title": d.get("title") or item["title"],
            "author": d.get("author") or "", "posted_at": posted, "in_window": (not posted) or str(posted)[:10] >= cutoff,
            "counts": counts, "score": score(counts), "key_points": [str(k) for k in (d.get("key_points") or [])[:4]],
            "quotes": quotes, "credits": d.get("credits"), "cached": d.get("cached"),
        })
    posts.sort(key=lambda x: x["score"], reverse=True)

    pack = {"topic": args.topic, "days": args.days, "since": cutoff, "searched": searched, "listed": len(order),
            "read": len(posts), "credits_spent": spent, "posts": posts, "not_read": skipped,
            "unread_links": [f for f in order[args.read:]]}
    if args.format == "json":
        print(json.dumps(pack, ensure_ascii=False, indent=2))
        return ld.EXIT_OK

    print(f"# 近 {args.days} 天：{args.topic}（{cutoff} 起）\n")
    for s in searched:
        note = f"，{s['note']}" if s.get("note") else ""
        print(f"- {NAMES[s['platform']]}：搜索找到 {s['found']} 条，其中 {s['in_window']} 条在时间窗内{note}")
    print(f"- 读了 {len(posts)} 条，共花 {spent} 积分；按互动排序（赞 + 2×评论 + 收藏 + 转发）\n")
    for i, x in enumerate(posts, 1):
        c = x["counts"]
        shown = " · ".join(f"{c[k]:,} {k}" for k in COUNT_WORDS if k in c) or "互动数未返回"
        flag = "" if x["in_window"] else "（发布日期早于时间窗）"
        print(f"## {i}. [{NAMES[x['platform']]}] {x['title']}\n")
        print(f"{x['author']} · {x['posted_at'] or '日期未知'}{flag} · {shown}\n{x['url']}\n")
        for k in x["key_points"]:
            print(f"- {k}")
        for q in x["quotes"]:
            when = f"[{int(q['t']) // 60:02d}:{int(q['t']) % 60:02d}] " if isinstance(q.get("t"), (int, float)) else ""
            print(f"  > {when}{q['text']}")
        print()
    if skipped:
        print("## 没读成的\n")
        for s in skipped:
            print(f"- [{NAMES[s['platform']]}] {s['title'][:40]} {s['url']} — {s['why']}")
        print()
    if pack["unread_links"]:
        print("## 找到但没读的（加大 --read 可以读）\n")
        for f in pack["unread_links"]:
            print(f"- [{NAMES[f['platform']]}] {f['posted_at'] or '日期未知'} {f['title'][:40]} {f['url']}")
    if not posts and not order:
        ld.log("时间窗内没有找到帖子。搜索走的是网页已收录的内容，新帖收录有延迟；换一个更具体的中文说法，或把 --days 调大。")
    return ld.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
