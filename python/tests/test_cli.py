from __future__ import annotations

import io
import json

import pytest

import linkdigest.client as client_mod
from conftest import DIGEST, FakeTransport, jresp
from linkdigest import cli


@pytest.fixture()
def fake(monkeypatch):
    """Route the CLI's client through a fake transport, with a key in the env."""
    monkeypatch.setenv("LINKDIGEST_API_KEY", "ld_live_cli")
    transport = FakeTransport()
    monkeypatch.setattr(client_mod, "urllib_transport", transport)
    monkeypatch.setattr(client_mod.time, "sleep", lambda s: None)
    return transport


def run(capsys, *argv: str, stdin: str | None = None):
    code = cli.main(list(argv), stdin=io.StringIO(stdin) if stdin is not None else None)
    out, err = capsys.readouterr()
    return code, out, err


def test_prints_markdown_and_status_on_stderr(fake, capsys):
    fake.queue.append(jresp(200, DIGEST))
    code, out, err = run(capsys, "https://v.douyin.com/abc/")
    assert code == 0
    assert out.startswith("# 三步做出爆款口播")
    assert "douyin · 2 credit(s)" in err
    assert fake.body() == {"url": "https://v.douyin.com/abc/", "format": "json"}


def test_flags_reach_the_request_and_json_prints_the_data(fake, capsys):
    fake.queue.append(jresp(200, {**DIGEST, "cached": True, "credits": 0}))
    code, out, err = run(
        capsys, "https://xhslink.com/o/x", "--breakdown", "--translate", "en", "--partial-ok", "--max-credits", "3", "--json"
    )
    assert code == 0
    assert json.loads(out)["title"] == DIGEST["title"]
    assert "cached, 0 credits" in err
    assert fake.body() == {
        "url": "https://xhslink.com/o/x",
        "format": "json",
        "translate_to": "en",
        "breakdown": True,
        "partial_ok": True,
        "max_credits": 3,
    }


def test_dash_reads_share_text_from_stdin(fake, capsys):
    fake.queue.append(jresp(200, DIGEST))
    share = "3.07 复制打开抖音，看看【某作者的作品】 https://v.douyin.com/abc/ 01/02 Yz@a.Nw"
    code, _, _ = run(capsys, "-", stdin=share)
    assert code == 0
    assert fake.body()["url"] == share


def test_out_of_credits_exits_3_with_the_pay_link(fake, capsys):
    fake.queue.append(jresp(402, {"error": "Free credits used up.", "buy_url": "https://linkdigest.dev/buy?t=1"}))
    code, out, err = run(capsys, "https://v.douyin.com/abc/")
    assert code == 3 and out == ""
    assert "https://linkdigest.dev/buy?t=1" in err


def test_still_running_exits_4_and_says_how_to_collect(fake, capsys):
    fake.queue.append(jresp(202, {"pending": True, "jobId": "j42"}))
    code, _, err = run(capsys, "https://v.douyin.com/long/", "--max-wait", "0")
    assert code == 4
    assert "linkdigest --job j42" in err


def test_job_flag_collects(fake, capsys):
    fake.queue.append(jresp(200, DIGEST))
    code, out, _ = run(capsys, "--job", "j42", "-q")
    assert code == 0 and out.startswith("# ")
    assert fake.requests[0].url.endswith("/api/v1/digest/j42?format=json&wait=20")


def test_unreadable_link_exits_1(fake, capsys):
    fake.queue.append(jresp(422, {"error": "could not read this link: private account"}))
    code, _, err = run(capsys, "https://www.xiaohongshu.com/explore/1")
    assert code == 1 and "private account" in err


def test_no_key_exits_2_and_points_to_the_keys_page(monkeypatch, capsys):
    code, _, err = run(capsys, "https://v.douyin.com/abc/")
    assert code == 2 and "linkdigest.dev/app/keys" in err


def test_no_url_is_a_usage_error(fake, capsys):
    code, _, err = run(capsys)
    assert code == 2 and "give a link" in err


def test_check_key(fake, capsys):
    fake.queue.append(jresp(200, {"ok": True, "key": {"label": "ci", "hint": "…wxyz"}}))
    code, out, _ = run(capsys, "--check-key")
    assert code == 0 and "key ok" in out
