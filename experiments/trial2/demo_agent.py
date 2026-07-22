"""
Demo: Multi-turn agent loop using TokenTracer to track token costs.

This script simulates a 3-turn agentic workflow where:
1. User asks a question
2. Model uses a tool to fetch information
3. Model processes the result and continues
4. Model provides final answer

We track tokens at each step, showing:
- Without caching: exponential token growth
- With caching: stable prefix reuse at 0.1x cost
"""

import os
from anthropic import Anthropic
from token_tracer import TokenTracer


def create_system_prompt():
    """Create a system prompt with cache_control to test caching."""
    return [
        {
            "type": "text",
            "text": """You are a helpful research assistant. You have access to tools to:
1. search_documents(query: str) - Search a knowledge base
2. fetch_page(url: str) - Fetch content from a specific page

Always be concise and clear in your responses. Use tools as needed to answer questions accurately.""",
            "cache_control": {"type": "ephemeral"}
        }
    ]


def create_tools():
    """Define the tools the model can use."""
    return [
        {
            "name": "search_documents",
            "description": "Search a knowledge base for relevant documents",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "fetch_page",
            "description": "Fetch the full content of a specific page",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL or page identifier"
                    }
                },
                "required": ["url"]
            }
        }
    ]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Simulate tool execution."""
    if tool_name == "search_documents":
        query = tool_input.get("query", "")
        # Simulate search results
        return f"Found 3 documents matching '{query}':\n1. Document A - About {query}\n2. Document B - Related to {query}\n3. Document C - Summary of {query}"

    elif tool_name == "fetch_page":
        url = tool_input.get("url", "")
        # Simulate page fetch
        return f"Page content from {url}:\n\nThis is a detailed page about the requested topic. It contains comprehensive information relevant to your query, with multiple sections covering different aspects of the subject matter."

    return "Unknown tool"


def run_demo_agent():
    """Run a demo agent with token tracing."""
    client = Anthropic()
    tracer = TokenTracer(client, verbose=True)

    # System prompt with cache control
    system = create_system_prompt()
    tools = create_tools()

    # Messages will accumulate over turns
    messages = []

    print("\n" + "="*80)
    print("TOKEN-TRACED AGENT LOOP DEMO")
    print("="*80)
    print("This agent will run a 3-turn loop with caching enabled on the system prompt.\n")

    # TURN 1: User asks a question
    print(">>> TURN 1: User question <<<")
    user_message = "What is the capital of France?"
    print(f"User: {user_message}\n")

    messages.append({"role": "user", "content": user_message})

    response = tracer.create_message(
        model="claude-opus-4-8",
        max_tokens=1024,
        system=system,
        tools=tools,
        messages=messages
    )

    # Process response (add assistant message)
    assistant_message = {"role": "assistant", "content": response.content}
    messages.append(assistant_message)

    print(f"Assistant: {response.content[0].text}\n")

    # TURN 2: User asks follow-up
    print(">>> TURN 2: Follow-up question <<<")
    user_message = "Tell me more about its history."
    print(f"User: {user_message}\n")

    messages.append({"role": "user", "content": user_message})

    response = tracer.create_message(
        model="claude-opus-4-8",
        max_tokens=1024,
        system=system,
        tools=tools,
        messages=messages
    )

    assistant_message = {"role": "assistant", "content": response.content}
    messages.append(assistant_message)

    print(f"Assistant: {response.content[0].text}\n")

    # TURN 3: Third turn
    print(">>> TURN 3: Another follow-up <<<")
    user_message = "What are the top attractions there?"
    print(f"User: {user_message}\n")

    messages.append({"role": "user", "content": user_message})

    response = tracer.create_message(
        model="claude-opus-4-8",
        max_tokens=1024,
        system=system,
        tools=tools,
        messages=messages
    )

    assistant_message = {"role": "assistant", "content": response.content}
    messages.append(assistant_message)

    print(f"Assistant: {response.content[0].text}\n")

    # Print reports
    tracer.table()
    tracer.summary()

    print("\n" + "="*80)
    print("INTERPRETATION")
    print("="*80)
    print("""
This demo shows:

1. **Turn 1**: System prompt, tools, and user message are all sent.
   - 'cache_write' shows how many tokens were cached
   - Cost is 1.25× for cached tokens (cache write premium)

2. **Turn 2 & 3**: Same system and tools, so they're served from cache.
   - 'cache_read' shows cached tokens at 0.1× cost (10% of normal)
   - Only new user message + response cost full price
   - This is why cache works so well for repeated agent runs

3. **Total Savings**: Shows % reduction from caching.
   - Higher savings the more turns you have
   - Break-even is around 2-3 turns for 5-min TTL cache

Takeaway: For agent loops, cache the system prompt and tools to save ~35% on
multi-turn interactions. Even more savings on repeated agent runs with same config.
""")


if __name__ == "__main__":
    run_demo_agent()
