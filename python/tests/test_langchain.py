"""LinkDigestTool, offline. Skipped when langchain-core is not installed."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("langchain_core")

from langchain_core.messages import ToolMessage  # noqa: E402

from conftest import DIGEST, FakeClock, FakeTransport, jresp  # noqa: E402
from linkdigest import AuthenticationError, LinkDigest  # noqa: E402
from linkdigest.integrations.langchain import LinkDigestTool  # noqa: E402

KEY = "ld_live_test_key"


def tool(fake: FakeTransport, **kw) -> LinkDigestTool:
    c = LinkDigest(KEY, transport=fake)
    clock = FakeClock()
    c._clock = clock
    c._sleep = clock.sleep
    return LinkDigestTool(client=c, **kw)


def call(t: LinkDigestTool, args: dict) -> ToolMessage:
    """As an agent calls it: a ToolCall, which returns a ToolMessage."""
    return t.invoke({"name": t.name, "args": args, "id": "call_1", "type": "tool_call"})


def test_reads_the_link_and_gives_the_model_markdown():
    fake = FakeTransport(jresp(200, DIGEST))
    t = tool(fake)
    out = t.invoke({"url": "https://v.douyin.com/abc/", "depth": "script"})

    assert out == DIGEST["raw_markdown"]
    assert fake.body() == {"url": "https://v.douyin.com/abc/", "format": "json", "depth": "script"}
    assert fake.requests[0].headers["Authorization"] == f"Bearer {KEY}"


def test_tool_call_carries_the_full_json_as_artifact():
    msg = call(tool(FakeTransport(jresp(200, DIGEST))), {"url": "https://v.douyin.com/abc/"})

    assert isinstance(msg, ToolMessage) and msg.status == "success"
    assert msg.content == DIGEST["raw_markdown"]
    assert msg.artifact["title"] == "三步做出爆款口播" and msg.artifact["credits"] == 2


def test_json_output_is_compact():
    out = tool(FakeTransport(jresp(200, DIGEST)), output="json").invoke({"url": "https://v.douyin.com/abc/"})
    data = json.loads(out)

    assert data["title"] == "三步做出爆款口播" and data["platform"] == "douyin"
    assert data["transcript"][1]["text"] == "开头三秒没人看"
    # raw_markdown is the markdown form; ocr_text repeats on_screen; empties are dropped.
    assert "raw_markdown" not in data and "ocr_text" not in data and "images" not in data
    assert "三步" in out  # not \u-escaped


def test_translate_to_is_sent():
    fake = FakeTransport(jresp(200, DIGEST))
    tool(fake).invoke({"url": "https://v.douyin.com/abc/", "translate_to": "en"})
    assert fake.body()["translate_to"] == "en"


def test_max_credits_is_the_tools_ceiling_not_the_models():
    fake = FakeTransport(jresp(200, DIGEST))
    tool(fake, max_credits=5).invoke({"url": "https://v.douyin.com/abc/"})
    assert fake.body()["max_credits"] == 5
    assert "max_credits" not in LinkDigestTool.model_fields["args_schema"].default.model_fields


def test_out_of_credits_tells_the_model_the_pay_link():
    refused = jresp(
        402,
        {
            "error": "This link needs 6 credits; 1 is left.",
            "error_code": "insufficient_credits",
            "buy_url": "https://linkdigest.dev/buy?t=abc",
        },
    )
    msg = call(tool(FakeTransport(refused)), {"url": "https://v.douyin.com/abc/"})

    assert msg.status == "error"
    assert "6 credits" in msg.content
    assert "https://linkdigest.dev/buy?t=abc" in msg.content
    assert "Nothing was charged" in msg.content


def test_unreadable_post_is_a_sentence_not_a_crash():
    gone = jresp(422, {"error": "The post was removed.", "error_code": "unreadable"})
    out = tool(FakeTransport(gone)).invoke({"url": "https://v.douyin.com/abc/"})
    assert out.startswith("This post cannot be read: The post was removed.")
    assert "retrying will not help" in out


def test_a_long_read_hands_back_its_job_id_and_is_collected_by_it():
    fake = FakeTransport(jresp(202, {"jobId": "job_9", "stage": "transcribing"}))
    msg = call(tool(fake, max_wait=0), {"url": "https://v.douyin.com/abc/"})

    assert 'job_id="job_9"' in msg.content and "transcribing" in msg.content
    assert msg.artifact == {"job_id": "job_9", "stage": "transcribing", "pending": True}
    assert len(fake.requests) == 1  # max_wait=0: no polling

    fake = FakeTransport(jresp(200, DIGEST))
    out = tool(fake).invoke({"job_id": "job_9"})
    assert out == DIGEST["raw_markdown"]
    assert fake.requests[0].method == "GET" and "/api/v1/digest/job_9?" in fake.requests[0].url


def test_waits_for_a_running_read_within_max_wait():
    fake = FakeTransport(jresp(202, {"jobId": "job_9"}), jresp(202, {"jobId": "job_9"}), jresp(200, DIGEST))
    assert tool(fake).invoke({"url": "https://v.douyin.com/abc/"}) == DIGEST["raw_markdown"]
    assert len(fake.requests) == 3


def test_no_url_and_no_job_id_asks_for_one():
    fake = FakeTransport()
    out = tool(fake).invoke({})
    assert "Give url" in out and not fake.requests


def test_a_bad_language_code_is_refused_before_any_request():
    fake = FakeTransport()
    out = tool(fake).invoke({"url": "https://v.douyin.com/abc/", "translate_to": "English"})
    assert "validation error" in out.lower() and not fake.requests


def test_schema_the_model_sees():
    schema = tool(FakeTransport()).tool_call_schema.model_json_schema()
    assert set(schema["properties"]) == {"url", "depth", "translate_to", "job_id"}
    assert schema["properties"]["depth"]["enum"] == ["full", "transcript", "script"]


def test_no_key_fails_when_the_tool_is_made_not_when_the_agent_calls_it():
    with pytest.raises(AuthenticationError):
        LinkDigestTool()


def test_the_key_is_not_in_the_tools_repr():
    assert KEY not in repr(tool(FakeTransport()))


def test_an_agent_calls_it_and_reads_the_result():
    pytest.importorskip("langchain.agents")
    from langchain.agents import create_agent
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage

    class Model(GenericFakeChatModel):
        def bind_tools(self, tools, **kw):
            return self

    model = Model(
        messages=iter(
            [
                AIMessage(content="", tool_calls=[{"name": "digest_url", "args": {"url": "https://v.douyin.com/abc/"}, "id": "c1"}]),
                AIMessage(content="It says the first three seconds need a hook."),
            ]
        )
    )
    fake = FakeTransport(jresp(200, DIGEST))
    out = create_agent(model, tools=[tool(fake)]).invoke({"messages": [{"role": "user", "content": "https://v.douyin.com/abc/"}]})

    read = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert read[0].content == DIGEST["raw_markdown"] and read[0].artifact["credits"] == 2
    assert out["messages"][-1].content.startswith("It says")
