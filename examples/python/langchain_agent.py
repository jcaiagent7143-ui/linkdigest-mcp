"""A LangChain agent that can read Douyin, Xiaohongshu, Bilibili, TikTok and YouTube links.

    pip install "linkdigest-mcp[langchain]" langchain langchain-anthropic
    export LINKDIGEST_API_KEY=ld_live_...     # https://linkdigest.dev/app/keys
    export ANTHROPIC_API_KEY=...              # or any model langchain.agents.create_agent accepts
    python langchain_agent.py "https://v.douyin.com/xxxx/" "这条视频卖的是什么？列出它说的卖点"

Part 1 calls the tool directly (no model needed). Part 2 hands it to an agent,
which decides when to read the link. A link anyone has read before is free.
"""

from __future__ import annotations

import os
import sys

from linkdigest.integrations.langchain import LinkDigestTool

url = sys.argv[1] if len(sys.argv) > 1 else "https://www.douyin.com/video/7685253896516363626"
question = sys.argv[2] if len(sys.argv) > 2 else "What is this video selling, and what does it claim?"

# max_credits is your ceiling per link: a read that would cost more is refused and costs nothing.
tool = LinkDigestTool(max_credits=10)

# 1. The tool on its own: the post as markdown (transcript with times, on-screen text, key points).
print(tool.invoke({"url": url, "depth": "script"})[:600], "\n...")

# 2. In an agent.
if os.environ.get("ANTHROPIC_API_KEY"):
    from langchain.agents import create_agent

    agent = create_agent(model=os.environ.get("MODEL", "anthropic:claude-sonnet-5-5"), tools=[tool])
    result = agent.invoke({"messages": [{"role": "user", "content": f"{question}\n\n{url}"}]})
    print(result["messages"][-1].content)
