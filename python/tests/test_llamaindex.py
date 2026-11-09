"""LinkDigestReader, offline. Skipped when llama-index-core is not installed."""

from __future__ import annotations

import logging

import pytest

pytest.importorskip("llama_index.core")

from llama_index.core.schema import Document, MetadataMode  # noqa: E402

from conftest import DIGEST, FakeClock, FakeTransport, jresp  # noqa: E402
from linkdigest import LinkDigest, PaymentRequiredError, UnreadableLinkError  # noqa: E402
from linkdigest.integrations.llamaindex import LinkDigestReader  # noqa: E402

KEY = "ld_live_test_key"

READ = dict(
    DIGEST,
    posted_at="2026-11-01",
    coverage={
        "seconds_transcribed": 42.0,
        "duration_seconds": 42.0,
        "largest_frame_gap_seconds": 3.0,
        "images_read": None,
        "images_total": None,
        "not_captured": ["the music"],
    },
)


def reader(fake: FakeTransport, **kw) -> LinkDigestReader:
    c = LinkDigest(KEY, transport=fake)
    clock = FakeClock()
    c._clock = clock
    c._sleep = clock.sleep
    return LinkDigestReader(client=c, **kw)


def test_one_document_per_link_with_flat_metadata():
    fake = FakeTransport(jresp(200, READ))
    docs = reader(fake).load_data(["https://v.douyin.com/abc/"])

    assert len(docs) == 1 and isinstance(docs[0], Document)
    d = docs[0]
    assert d.text == DIGEST["raw_markdown"]
    assert d.id_ == "linkdigest:https://www.douyin.com/video/1"
    assert d.metadata == {
        "platform": "douyin",
        "title": "三步做出爆款口播",
        "author": "某作者",
        "source_url": "https://www.douyin.com/video/1",
        "posted_at": "2026-11-01",
        "transcript_source": "asr",
        "credits": 2,
        "cached": False,
        "coverage_seconds_transcribed": 42.0,
        "coverage_duration_seconds": 42.0,
        "coverage_not_captured": "the music",
    }
    # Vector stores such as Chroma take only flat str/int/float/bool values.
    assert all(isinstance(v, (str, int, float, bool)) for v in d.metadata.values())


def test_billing_fields_stay_out_of_embeddings_and_the_prompt():
    d = reader(FakeTransport(jresp(200, READ))).load_data(["https://v.douyin.com/abc/"])[0]
    for mode in (MetadataMode.EMBED, MetadataMode.LLM):
        text = d.get_content(metadata_mode=mode)
        assert "三步做出爆款口播" in text and "credits" not in text and "cached" not in text


def test_depth_from_the_reader_or_the_call():
    fake = FakeTransport(jresp(200, READ), jresp(200, READ))
    r = reader(fake, depth="script", translate_to="en")
    r.load_data("https://v.douyin.com/abc/")  # one link as a plain string
    assert fake.body(0) == {"url": "https://v.douyin.com/abc/", "format": "json", "depth": "script", "translate_to": "en"}
    r.load_data(["https://v.douyin.com/abc/"], depth="transcript")
    assert fake.body(1)["depth"] == "transcript"


def test_an_unreadable_link_is_logged_and_skipped(caplog: pytest.LogCaptureFixture):
    gone = jresp(422, {"error": "The post was removed.", "error_code": "unreadable"})
    fake = FakeTransport(gone, jresp(200, READ))
    with caplog.at_level(logging.WARNING, logger="linkdigest"):
        docs = reader(fake).load_data(["https://v.douyin.com/gone/", "https://v.douyin.com/abc/"])

    assert [d.metadata["title"] for d in docs] == ["三步做出爆款口播"]
    assert "https://v.douyin.com/gone/" in caplog.text and "The post was removed." in caplog.text


def test_errors_raise_stops_at_the_first_unreadable_link():
    gone = jresp(422, {"error": "The post was removed."})
    with pytest.raises(UnreadableLinkError):
        reader(FakeTransport(gone), errors="raise").load_data(["https://v.douyin.com/gone/", "https://v.douyin.com/abc/"])


def test_out_of_credits_stops_the_load_even_when_warning():
    broke = jresp(402, {"error": "No credits left.", "buy_url": "https://linkdigest.dev/buy?t=abc"})
    fake = FakeTransport(broke)
    with pytest.raises(PaymentRequiredError) as e:
        reader(fake).load_data(["https://v.douyin.com/a/", "https://v.douyin.com/b/"])
    assert e.value.buy_url == "https://linkdigest.dev/buy?t=abc"
    assert len(fake.requests) == 1  # the second link was not tried


def test_a_read_still_running_is_skipped_with_its_job_id(caplog: pytest.LogCaptureFixture):
    fake = FakeTransport(jresp(202, {"jobId": "job_9", "stage": "transcribing"}))
    with caplog.at_level(logging.WARNING, logger="linkdigest"):
        assert reader(fake, max_wait=0).load_data(["https://v.douyin.com/long/"]) == []
    assert "job_9" in caplog.text


def test_lazy_load_reads_one_link_at_a_time():
    fake = FakeTransport(jresp(200, READ), jresp(200, READ))
    it = reader(fake).lazy_load_data(["https://v.douyin.com/a/", "https://v.douyin.com/b/"])
    next(it)
    assert len(fake.requests) == 1


def test_bad_errors_value():
    with pytest.raises(ValueError):
        reader(FakeTransport(), errors="ignore")


def test_documents_go_into_an_index_and_answer_a_query():
    from llama_index.core import VectorStoreIndex
    from llama_index.core.embeddings import MockEmbedding
    from llama_index.core.llms import MockLLM

    docs = reader(FakeTransport(jresp(200, READ))).load_data(["https://v.douyin.com/abc/"])
    index = VectorStoreIndex.from_documents(docs, embed_model=MockEmbedding(embed_dim=8))
    answer = index.as_query_engine(llm=MockLLM()).query("What is the hook?")
    assert answer.source_nodes[0].node.metadata["source_url"] == "https://www.douyin.com/video/1"
