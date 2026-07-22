"""
Mock Anthropic Client for testing without API keys.

Simulates the Anthropic Messages API with configurable token counts,
cache behavior, and response sequences. Perfect for testing TokenTracer logic.
"""

from dataclasses import dataclass
from typing import Any, Optional, List
from enum import Enum


class CacheStrategy(Enum):
    """How the mock client simulates caching behavior."""
    NO_CACHE = "no_cache"              # No caching at all
    SIMPLE = "simple"                  # Cache first N tokens of system
    FULL = "full"                      # Full caching as implemented


@dataclass
class MockUsage:
    """Simulates response.usage from Anthropic API."""
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class MockContentBlock:
    """Simulates a content block in the response."""
    type: str = "text"
    text: str = ""


@dataclass
class MockResponse:
    """Simulates Anthropic API response."""
    content: List[MockContentBlock]
    usage: MockUsage
    stop_reason: str = "end_turn"

    def __init__(self, text: str, input_tokens: int, output_tokens: int,
                 cache_read: int = 0, cache_write: int = 0):
        self.content = [MockContentBlock(type="text", text=text)]
        self.usage = MockUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=cache_read,
            cache_creation_input_tokens=cache_write
        )
        self.stop_reason = "end_turn"


class MockAnthropicClient:
    """
    Simulates the Anthropic client for testing token accounting.

    Usage:
        mock_client = MockAnthropicClient(
            cache_strategy=CacheStrategy.FULL,
            system_prefix_tokens=900
        )

        # Configure responses for each turn
        mock_client.queue_response(
            input_tokens=900,
            output_tokens=30,
            text="Response for turn 1"
        )

        # Use like real client
        response = mock_client.messages.create(
            model="mock-model",
            messages=[...],
            max_tokens=1024
        )
    """

    def __init__(self, cache_strategy: CacheStrategy = CacheStrategy.FULL,
                 system_prefix_tokens: int = 900):
        """
        Initialize mock client.

        Args:
            cache_strategy: How to simulate caching (NO_CACHE, SIMPLE, FULL)
            system_prefix_tokens: Tokens in the system prompt (used for cache simulation)
        """
        self.cache_strategy = cache_strategy
        self.system_prefix_tokens = system_prefix_tokens
        self.response_queue = []
        self.call_count = 0
        self.cache_created = False
        self.cache_expires_at_turn = None

    def queue_response(self, text: str, input_tokens: int, output_tokens: int):
        """Queue a response to be returned on the next create_message call."""
        self.response_queue.append((text, input_tokens, output_tokens))

    def queue_scenario(self, scenario: List[tuple]):
        """
        Queue multiple responses at once.

        Args:
            scenario: List of (text, input_tokens, output_tokens) tuples
        """
        for text, input_tokens, output_tokens in scenario:
            self.queue_response(text, input_tokens, output_tokens)

    @property
    def messages(self):
        """Return a messages API-like interface."""
        return self

    def count_tokens(self, **kwargs) -> Any:
        """
        Simulate count_tokens API call.
        Returns predicted input tokens without executing the full request.
        """
        messages = kwargs.get("messages", [])
        system = kwargs.get("system", [])

        # Calculate predicted tokens
        predicted_input = self.system_prefix_tokens

        # Add message tokens (roughly ~4 tokens per word average)
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                predicted_input += len(content.split()) * 4

        class CountResult:
            def __init__(self, tokens):
                self.input_tokens = tokens

        return CountResult(predicted_input)

    def create(self, **kwargs) -> MockResponse:
        """
        Simulate messages.create() call.
        Pops from response_queue and simulates cache behavior.
        """
        self.call_count += 1
        turn_num = self.call_count

        if not self.response_queue:
            raise RuntimeError("No responses queued. Use queue_response() or queue_scenario() first.")

        text, input_tokens, output_tokens = self.response_queue.pop(0)

        # Simulate caching behavior
        cache_read = 0
        cache_write = 0

        if self.cache_strategy == CacheStrategy.FULL:
            # First turn: write cache
            if turn_num == 1:
                cache_write = self.system_prefix_tokens
                self.cache_created = True
                self.cache_expires_at_turn = turn_num + 100  # Simulating 5-min TTL

            # Subsequent turns: read from cache (if still valid)
            elif self.cache_created and turn_num < self.cache_expires_at_turn:
                cache_read = self.system_prefix_tokens

        elif self.cache_strategy == CacheStrategy.SIMPLE:
            # Simplified: just track basic cache
            if turn_num == 1 and not self.cache_created:
                cache_write = self.system_prefix_tokens // 2
                self.cache_created = True
            elif self.cache_created and turn_num > 1:
                cache_read = self.system_prefix_tokens // 2

        # Create response with cache info
        response = MockResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read=cache_read,
            cache_write=cache_write
        )

        return response

    def reset(self):
        """Reset for a new test scenario."""
        self.call_count = 0
        self.response_queue = []
        self.cache_created = False
        self.cache_expires_at_turn = None


# Pre-built scenarios for testing
SCENARIO_3_TURN_NO_CACHE = [
    ("Here's the answer to your first question.", 900, 30),
    ("Processing your follow-up...", 1400, 40),
    ("And here's the final answer.", 1700, 200),
]

SCENARIO_3_TURN_WITH_CACHE = [
    # Turn 1: Write cache
    ("Here's the answer.", 900, 30),
    # Turn 2: Read from cache (900t @ 0.1x + 500t new)
    ("Following up on that...", 1400, 40),
    # Turn 3: Read from cache (900t @ 0.1x + 800t new)
    ("Final thoughts.", 1700, 200),
]

SCENARIO_5_TURN_LONG_LOOP = [
    ("Turn 1 response", 1000, 50),
    ("Turn 2 response", 1200, 60),
    ("Turn 3 response", 1400, 70),
    ("Turn 4 response", 1600, 80),
    ("Turn 5 response", 1800, 100),
]

SCENARIO_TOOL_USE = [
    ("I'll search for information.", 950, 45),  # Tool call
    ("Here's what I found...", 2000, 55),      # After tool result
    ("Let me verify this.", 2500, 100),        # Another tool call
]
