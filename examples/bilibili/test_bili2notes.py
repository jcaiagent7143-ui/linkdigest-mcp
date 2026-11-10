"""Offline tests for bili2notes (no network: a fake transport answers).

    python -m pytest examples/bilibili/test_bili2notes.py -q
"""

from __future__ import annotations

import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bili2notes as b  # noqa: E402

BV = "BV1JE411g7XF"


class Fake:
    """Answers from a queue and records what was asked."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, method, path, body, key):
        self.calls.append((method, path, body, key))
        if not self.answers:
            raise AssertionError(f"unexpected call: {method} {path}")
        return self.answers.pop(0)


class Tty(io.StringIO):
    def isatty(self):
        return True


def digest(p=2, **over):
    d = {
        "title": f"李宏毅2020机器学习 · P{p} Rule of ML 2020",
        "author": "大佬的迷弟的粉丝",
        "posted_at": "2020-03-07",
        "source_url": f"https://www.bilibili.com/video/{BV}?p={p}",
        "duration_seconds": 1324,
        "read_seconds": 1324,
        "credits": 12,
        "cached": False,
        "credits_left": 200,
        "key_points": ["建议用 Linux 或 Mac", "作业交到 GitHub"],
        "key_point_support": [
            {"point_index": 0, "t": 61.0, "quote": "强烈建议大家用Linux或是Mac的系统", "verified": True},
            {"point_index": 1, "t": None, "quote": "模型自己编的一句", "verified": False},
        ],
        "outline": [
            {"start": 0, "end": 26.3, "title": "助教自我介绍与课程大纲", "summary": ["介绍课程规定。"], "quote": "大家好,這樣聽得清楚嗎?", "generated": "model"},
            {"start": 26.3, "end": 1324, "title": "作业环境", "summary": ["用 Colab。", "交到 GitHub。"], "quote": "", "generated": "model"},
        ],
        "transcript": [{"t": 0, "text": "大家好"}, {"t": 3725, "text": "一小时之后"}],
        "on_screen": [{"t": 12, "text": "Rule of ML 2020"}],
        "parts": {"count": 119, "current": p, "items": [{"p": i, "title": f"第{i}节", "seconds": s} for i, s in ((1, 2228), (2, 1324), (3, 100), (4, 601))]},
    }
    d.update(over)
    return d


# ---- links ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "text, want",
    [
        ("https://www.bilibili.com/video/BV1pu411o7BE", "https://www.bilibili.com/video/BV1pu411o7BE"),
        ("【Transformer论文逐段精读】 https://b23.tv/abcDEF1复制此链接", "https://b23.tv/abcDEF1"),
        ("BV1JE411g7XF?p=2", "https://www.bilibili.com/video/BV1JE411g7XF?p=2"),
        ("看看这个 https://www.bilibili.com/video/BV1JE411g7XF?p=7&vd_source=1。", "https://www.bilibili.com/video/BV1JE411g7XF?p=7&vd_source=1"),
        ("www.bilibili.com/zh-Hans/video/BV1Wb421n7Ji/?buvid=x", "https://www.bilibili.com/zh-Hans/video/BV1Wb421n7Ji/?buvid=x"),
    ],
)
def test_the_link_is_found_in_whatever_was_pasted(text, want):
    assert b.find_link(text) == want


def test_text_without_a_bilibili_link_is_refused():
    with pytest.raises(b.Stop) as e:
        b.find_link("今天天气不错 https://example.com/video")
    assert e.value.code == 2


def test_part_ranges():
    assert b.parse_parts("1-3,5,9-", 10) == [1, 2, 3, 5, 9, 10]
    assert b.parse_parts("all", 3) == [1, 2, 3]
    assert b.parse_parts("-2", 5) == [1, 2]
    assert b.parse_parts("3，3，2", 5) == [3, 2], "full-width commas, no repeats, order kept"
    assert b.parse_parts("118-200", 119) == [118, 119], "clipped to the video's parts"
    for bad in ("", "abc", "5-2", "0-3", "200"):
        with pytest.raises(b.Stop):
            b.parse_parts(bad, 119)


def test_estimates_follow_the_published_rule():
    # The same figures the service charged on 2026-11-10: P1 37:08 script 19, P2 22:04 script 12.
    assert b.estimate_credits(2228, "script") == 19 and b.estimate_credits(1324, "script") == 12
    assert b.estimate_credits(2700, "transcript") == 24 and b.estimate_credits(300, "full") == 6
    assert b.estimate_credits(0, "script") == 1


# ---- the note --------------------------------------------------------------------

def test_a_note_has_the_outline_points_and_timed_transcript():
    note = b.render_note(digest())
    assert note.startswith("# 李宏毅2020机器学习 · P2 Rule of ML 2020\n")
    assert "分P：第 2 P / 共 119 P" in note and "时长：22:04" in note
    assert "### [00:00–00:26] 助教自我介绍与课程大纲" in note and "- 介绍课程规定。" in note
    assert "> 大家好,這樣聽得清楚嗎?" in note
    assert "### [00:26–22:04] 作业环境" in note
    # A quote is shown only when the service verified it, with its time.
    assert "  > [01:01] 强烈建议大家用Linux或是Mac的系统" in note
    assert "模型自己编的一句" not in note
    assert "[00:00] 大家好" in note and "[1:02:05] 一小时之后" in note
    assert "画面上的字" not in note and "画面上的字" in b.render_note(digest(), on_screen=True)


def test_a_note_without_an_outline_simply_has_none():
    note = b.render_note(digest(outline=[], parts=None))
    assert "## 大纲" not in note and "分P" not in note
    assert "## 要点" in note and "## 逐字稿" in note


def test_a_partial_read_says_how_far_it_got():
    assert "时长：22:04（读了前 09:00）" in b.render_note(digest(read_seconds=540))


def test_the_keyless_summary_says_what_a_key_adds():
    note = b.render_note({"title": "T", "key_points": ["a"], "transcript_count": 15, "source_url": "u"})
    assert "没有 API Key 时只返回摘要" in note and "15 段逐字稿" in note and b.KEYS in note


# ---- the command -----------------------------------------------------------------

def run(argv, fake, *, key="ld_live_test", stdin=None, monkeypatch=None):
    out, err = io.StringIO(), io.StringIO()
    if monkeypatch is not None:
        if key:
            monkeypatch.setenv("LINKDIGEST_API_KEY", key)
        else:
            monkeypatch.delenv("LINKDIGEST_API_KEY", raising=False)
    code = b.run(argv, send=fake, stdin=stdin or io.StringIO(), stdout=out, stderr=err, sleep=lambda s: None)
    return code, out.getvalue(), err.getvalue()


def test_one_link_is_read_and_printed(monkeypatch):
    fake = Fake((200, digest()))
    code, out, err = run([f"https://www.bilibili.com/video/{BV}?p=2", "--depth", "script"], fake, monkeypatch=monkeypatch)
    assert code == 0 and out.startswith("# 李宏毅2020机器学习")
    method, path, body, key = fake.calls[0]
    assert (method, path, key) == ("POST", "/api/v1/digest", "ld_live_test")
    assert body == {"url": f"https://www.bilibili.com/video/{BV}?p=2", "format": "json", "depth": "script"}
    assert "读完：12 积分" in err and "共 119 P" in err and "--parts" in err


def test_a_long_video_is_collected_not_resubmitted(monkeypatch):
    fake = Fake((202, {"pending": True, "jobId": "j1", "poll": "/api/v1/digest/j1?depth=script", "retryAfter": 1}), (202, {"pending": True, "jobId": "j1", "poll": "/api/v1/digest/j1?depth=script"}), (200, digest()))
    code, out, _ = run([BV], fake, monkeypatch=monkeypatch)
    assert code == 0 and [c[0] for c in fake.calls] == ["POST", "GET", "GET"]
    assert fake.calls[1][1] == "/api/v1/digest/j1?depth=script&wait=20"


def test_without_a_key_the_free_summary_is_used(monkeypatch):
    fake = Fake((200, {"title": "T", "key_points": ["a"], "transcript_count": 3, "trial": True, "credits": 0}))
    code, out, err = run([BV], fake, key=None, monkeypatch=monkeypatch)
    assert code == 0 and fake.calls[0][3] is None
    assert "没有 LINKDIGEST_API_KEY" in err and "没有 API Key 时只返回摘要" in out


def test_parts_need_a_key(monkeypatch):
    fake = Fake()
    code, _, err = run([BV, "--parts", "1-3"], fake, key=None, monkeypatch=monkeypatch)
    assert code == 3 and "--parts 需要 API Key" in err and fake.calls == []


def test_refusals_carry_the_services_own_words(monkeypatch):
    code, _, err = run([BV], Fake((402, {"error": "this link needs 45 credits and only 3 remain", "offer_zh": "补充积分：…"})), monkeypatch=monkeypatch)
    assert code == 4 and "needs 45 credits" in err and "补充积分" in err
    code, _, err = run([BV], Fake((422, {"error": "这条视频需要大会员才能看"})), monkeypatch=monkeypatch)
    assert code == 5 and "大会员" in err
    code, _, err = run([BV], Fake((401, {"error": "invalid or missing API key"})), monkeypatch=monkeypatch)
    assert code == 3 and "无效或已撤销" in err


def batch_answers(ps):
    urls = [f"https://www.bilibili.com/video/{BV}?p={p}" for p in ps]
    items = [{"url": u, "status": "done", "credits": 1} for u in urls]
    return [
        (202, {"batch_id": "b1", "status": "running", "total": len(urls), "done": 0, "failed": 0}),
        (200, {"batch_id": "b1", "status": "done", "total": len(urls), "done": len(urls), "failed": 0, "credits_total": 7}),
        (200, {"batch_id": "b1", "status": "done", "credits_total": 7, "items": items, "digests": {u: digest(p) for u, p in zip(urls, ps)}}),
    ]


def test_the_cost_is_shown_and_nothing_starts_without_a_yes(monkeypatch, tmp_path):
    fake = Fake((200, digest(2)))
    code, out, err = run([f"{BV}?p=2", "--parts", "1-4", "--depth", "script", "--out-dir", str(tmp_path)], fake, monkeypatch=monkeypatch)
    # Not a terminal and no --yes: the estimate is printed, the batch is never posted.
    assert code == 6 and len(fake.calls) == 1
    assert "要读 3 个分 P（script）" in err and "约  19 积分" in err and "合计最多约 26 积分" in err
    assert "加 --yes 才会开始" in err and "没有开始，没有扣费" in err


def test_answering_no_at_the_prompt_stops_it(monkeypatch, tmp_path):
    fake = Fake((200, digest(2)))
    code, _, err = run([f"{BV}?p=2", "--parts", "1,3", "--out-dir", str(tmp_path)], fake, stdin=Tty("n\n"), monkeypatch=monkeypatch)
    assert code == 6 and len(fake.calls) == 1 and "开始吗？" in err


def test_with_yes_the_other_parts_are_batched_and_written(monkeypatch, tmp_path):
    fake = Fake((200, digest(2)), *batch_answers([1, 3, 4]))
    code, out, err = run([f"{BV}?p=2", "--parts", "1-4", "--depth", "script", "--yes", "--out-dir", str(tmp_path)], fake, monkeypatch=monkeypatch)
    assert code == 0
    post = fake.calls[1]
    assert post[:2] == ("POST", "/api/v1/digest/batch")
    # The part already read is not read (or paid for) again.
    assert post[2]["urls"] == [f"https://www.bilibili.com/video/{BV}?p={p}" for p in (1, 3, 4)] and post[2]["depth"] == "script"
    assert fake.calls[-1][1] == "/api/v1/digest/batch/b1?include=digests"
    files = sorted(os.listdir(tmp_path))
    assert len(files) == 4 and files[0].startswith("P001-") and files[1].startswith("P002-")
    assert "实际扣了 7 积分" in err and "写了 4 个文件" in err
    assert (tmp_path / files[2]).read_text(encoding="utf-8").startswith("# 李宏毅2020机器学习 · P3")


def test_batches_respect_the_batch_size(monkeypatch, tmp_path):
    fake = Fake((200, digest(2)), *batch_answers([1, 3]), *batch_answers([4]))
    code, _, _ = run([f"{BV}?p=2", "--parts", "1-4", "--yes", "--batch-size", "2", "--out-dir", str(tmp_path)], fake, monkeypatch=monkeypatch)
    posts = [c for c in fake.calls if c[:2] == ("POST", "/api/v1/digest/batch")]
    assert code == 0 and [len(c[2]["urls"]) for c in posts] == [2, 1]


def test_a_single_video_has_no_parts_to_read(monkeypatch, tmp_path):
    code, _, err = run([BV, "--parts", "1-3", "--yes", "--out-dir", str(tmp_path)], Fake((200, digest(parts=None))), monkeypatch=monkeypatch)
    assert code == 5 and "不是分P视频" in err


def test_a_saved_response_renders_offline(tmp_path):
    import json

    f = tmp_path / "d.json"
    f.write_text(json.dumps(digest()), encoding="utf-8")
    fake = Fake()
    out, err = io.StringIO(), io.StringIO()
    assert b.run(["--from-json", str(f)], send=fake, stdout=out, stderr=err) == 0
    assert fake.calls == [] and "## 大纲" in out.getvalue()
