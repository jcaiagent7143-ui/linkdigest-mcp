#!/usr/bin/env python3
"""Score what each reader returned, from the files run.py left in raw/. No network.

A reader "reached the post" when its output contains the post's own title: the
title the sampler recorded from the platform's list or the web index, before
any reader ran (any 8 consecutive characters of it, ignoring spaces and
punctuation). A login wall, a captcha page or the site's home page does not.

For speech, text in the picture and comments, LinkDigest's own structured
output is counted directly. The other readers return one block of text, so
they are probed: up to five sentences LinkDigest transcribed, five lines it
read from the picture and three comments are searched for in their output,
and a reader is credited when at least half are there. Where LinkDigest got
nothing, there is nothing to probe with and the cell is left out of the count
(shown as "-").

    python3 score.py            # writes results.json and prints the table
"""
import json
import pathlib
import re
import statistics

HERE = pathlib.Path(__file__).resolve().parent
READERS = ["linkdigest", "jina", "fetch", "ytdlp"]
EXT = {"linkdigest": "json", "jina": "txt", "fetch": "html", "ytdlp": "json"}
WALLS = ("登录后", "请登录", "打开App", "打开 App", "验证码", "captcha", "Sign in to confirm", "安全验证", "访问过于频繁", "当前笔记暂时无法浏览")


def norm(s):
    return re.sub(r"[^0-9a-z一-鿿]+", "", (s or "").lower())


def clean_title(t):
    t = re.sub(r"\s*-\s*(小红书|rednote|抖音|YouTube|哔哩哔哩.*)$", "", t or "", flags=re.I)
    return t.strip()


def has_title(title, text_norm):
    t = norm(clean_title(title))
    if not t:
        return None
    n = min(8, len(t))
    return any(t[i:i + n] in text_norm for i in range(0, len(t) - n + 1))


def spread(items, k):
    items = [x for x in items if len(norm(x)) >= 8]
    if len(items) <= k:
        return items
    step = len(items) / k
    return [items[int(i * step)] for i in range(k)]


def probe(probes, text_norm):
    """Fraction of probe strings whose first 12 normalised characters are in the text; None with nothing to probe."""
    if not probes:
        return None
    return sum(1 for p in probes if norm(p)[:12] in text_norm) / len(probes)


def score_link(n, link):
    d = HERE / "raw" / f"{n:02d}-{link['platform']}"
    row = {"n": n, "platform": link["platform"], "url": link["url"], "title": clean_title(link["title"]), "readers": {}}
    probes = {"speech": [], "picture": [], "comments": []}
    # LinkDigest first: its structured output also supplies the probes for the others.
    meta = json.loads((d / "linkdigest.meta.json").read_text()) if (d / "linkdigest.meta.json").exists() else None
    if meta:
        try:
            ld = json.loads((d / "linkdigest.json").read_text())
        except Exception:
            ld = {"error": "unparseable"}
        ok = meta["status"] == 200 and not ld.get("error")
        r = {"status": meta["status"], "seconds": meta["seconds"], "reached": False}
        if ok:
            text = norm(" ".join([ld.get("title") or "", ld.get("caption") or "", ld.get("raw_markdown") or ""]))
            cov = ld.get("coverage") or {}
            speech = [s.get("text", "") if isinstance(s, dict) else str(s) for s in (ld.get("transcript") or [])]
            picture = [o.get("text", "") for o in (ld.get("on_screen") or [])] + list(ld.get("ocr_text") or [])
            comments = [c.get("text", "") for c in (ld.get("comments") or []) if isinstance(c, dict)]
            probes = {"speech": spread(speech, 5), "picture": spread(picture, 5), "comments": spread(comments, 3)}
            r.update({
                "reached": bool(has_title(link["title"], text)) or bool(ld.get("title")),
                "title_matches_sample": has_title(link["title"], text),
                "kind": "video" if (ld.get("duration_seconds") or 0) > 0 else "images/text",
                "duration_seconds": ld.get("duration_seconds"),
                "read_seconds": ld.get("read_seconds"),
                "partial": bool(ld.get("partial")),
                "caption_chars": len(ld.get("caption") or ""),
                "speech_seconds": cov.get("seconds_transcribed") or 0,
                "speech_segments": len(speech),
                "picture_lines": len([p for p in picture if p.strip()]),
                "images_read": ld.get("images_read"), "images_total": ld.get("image_count"),
                "comments": len(comments),
                "key_points": len(ld.get("key_points") or []),
                "credits": ld.get("credits"), "cached": bool(ld.get("cached")),
                "not_captured": cov.get("not_captured") or [],
            })
        else:
            r.update({"error_code": ld.get("error_code") or ld.get("code"), "error": (ld.get("error") or "")[:240]})
        row["readers"]["linkdigest"] = r
    for name in ("jina", "fetch"):
        mp = d / f"{name}.meta.json"
        if not mp.exists():
            continue
        meta = json.loads(mp.read_text()); raw = (d / f"{name}.{EXT[name]}").read_text()
        t = norm(raw)
        reached = bool(has_title(link["title"], t))
        row["readers"][name] = {
            "status": meta["status"], "seconds": meta["seconds"], "chars": len(raw), "reached": reached,
            "wall": (not reached) and any(w.lower() in raw.lower() for w in WALLS),
            "speech": probe(probes["speech"], t), "picture": probe(probes["picture"], t), "comments": probe(probes["comments"], t),
        }
    mp = d / "ytdlp.meta.json"
    if mp.exists():
        meta = json.loads(mp.read_text()); raw = (d / "ytdlp.json").read_text()
        r = {"status": meta["status"], "seconds": meta["seconds"], "reached": False}
        if meta["status"] == 200:
            y = json.loads(raw)
            r.update({"reached": bool(has_title(link["title"], norm((y.get("title") or "") + (y.get("description") or "")))) or bool(y.get("title")),
                      "duration_seconds": y.get("duration"), "caption_tracks": y.get("subtitles") or [], "auto_caption_tracks": len(y.get("automatic_captions") or []),
                      "speech": None, "picture": None, "comments": None})
        else:
            r["error"] = raw.strip().splitlines()[-1][:200] if raw.strip() else ""
        row["readers"]["ytdlp"] = r
    return row


def credited(v):
    return v is not None and v >= 0.5


if __name__ == "__main__":
    spec = json.loads((HERE / "links.json").read_text())
    rows = [score_link(n, l) for n, l in enumerate(spec["links"], 1)]
    platforms = sorted({r["platform"] for r in rows}, key=["bilibili", "douyin", "xiaohongshu", "youtube"].index)
    summary = {}
    for name in READERS:
        s = {"links": 0, "reached": 0, "speech": 0, "speech_of": 0, "picture": 0, "picture_of": 0, "comments": 0, "comments_of": 0, "seconds": [], "by_platform": {}}
        for r in rows:
            x = r["readers"].get(name)
            if not x:
                continue
            ld = r["readers"].get("linkdigest") or {}
            s["links"] += 1; s["reached"] += bool(x.get("reached")); s["seconds"].append(x["seconds"])
            bp = s["by_platform"].setdefault(r["platform"], {"links": 0, "reached": 0})
            bp["links"] += 1; bp["reached"] += bool(x.get("reached"))
            if name == "linkdigest":
                s["speech"] += (x.get("speech_segments") or 0) > 0; s["picture"] += (x.get("picture_lines") or 0) > 0; s["comments"] += (x.get("comments") or 0) > 0
            elif name in ("jina", "fetch"):
                for k, of in (("speech", (ld.get("speech_segments") or 0) > 0), ("picture", (ld.get("picture_lines") or 0) > 0), ("comments", (ld.get("comments") or 0) > 0)):
                    if of:
                        s[k + "_of"] += 1; s[k] += credited(x.get(k))
            else:
                s["speech"] += bool(x.get("caption_tracks")) or (x.get("auto_caption_tracks") or 0) > 0
        s["median_seconds"] = round(statistics.median(s["seconds"]), 1) if s["seconds"] else None
        del s["seconds"]
        summary[name] = s
    ld_rows = [r["readers"]["linkdigest"] for r in rows if "linkdigest" in r["readers"]]
    summary["linkdigest"]["credits"] = sum((x.get("credits") or 0) for x in ld_rows)
    summary["linkdigest"]["speech_of"] = summary["linkdigest"]["picture_of"] = summary["linkdigest"]["comments_of"] = len(ld_rows)
    out = {"sampled_at": spec["sampled_at"], "max_credits_per_link": 12, "platforms": platforms, "summary": summary, "links": rows}
    (HERE / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("reader      reached          spoken words     text in picture  comments         median s")
    for name in READERS:
        s = summary[name]
        cell = lambda k: f"{s[k]}/{s[k + '_of']}" if s.get(k + "_of") else (str(s[k]) if name == "ytdlp" and k == "speech" else "-")
        print(f"{name:<11} {s['reached']}/{s['links']:<13} {cell('speech'):<16} {cell('picture'):<16} {cell('comments'):<16} {s['median_seconds']}")
    for name in READERS:
        print(name, {p: f"{v['reached']}/{v['links']}" for p, v in summary[name]["by_platform"].items()})
    print("linkdigest credits:", summary["linkdigest"]["credits"])
