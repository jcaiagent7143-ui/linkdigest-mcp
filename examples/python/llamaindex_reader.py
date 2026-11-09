"""Douyin / Xiaohongshu / Bilibili / YouTube links → LlamaIndex Documents → an index you can query.

    pip install "linkdigest-mcp[llamaindex]" llama-index
    export LINKDIGEST_API_KEY=ld_live_...     # https://linkdigest.dev/app/keys
    export OPENAI_API_KEY=...                 # LlamaIndex's default embeddings and LLM, for part 2
    python llamaindex_reader.py links.txt     # one link (or share text) per line

Part 1 reads the links (no model needed). Part 2 indexes them and asks a
question across all of them. A link that cannot be read (removed, private) is
logged and skipped; out of credits stops the run with a pay link.
"""

from __future__ import annotations

import os
import sys

from linkdigest.integrations.llamaindex import LinkDigestReader

if len(sys.argv) > 1:
    with open(sys.argv[1], encoding="utf-8") as f:
        urls = [ln.strip() for ln in f if ln.strip()]
else:
    urls = ["https://www.douyin.com/video/7685253896516363626"]

# depth="script": the spoken words only, 1 credit per started 2 minutes — the cheapest read.
docs = LinkDigestReader(depth="script", max_credits=10).load_data(urls)

# 1. One Document per link: the post as markdown, flat metadata.
for d in docs:
    m = d.metadata
    print(m.get("platform"), "|", m.get("title"), "|", m.get("author"), "|", m.get("credits"), "credits")

# 2. Ask across the whole set.
if docs and os.environ.get("OPENAI_API_KEY"):
    from llama_index.core import VectorStoreIndex

    index = VectorStoreIndex.from_documents(docs)
    answer = index.as_query_engine().query("What do these videos have in common? Name the video for each point.")
    print(answer)
