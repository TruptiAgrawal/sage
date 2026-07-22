"""
Token Tracer: Analyze token usage in agentic LLM workflows.

Wraps the Anthropic client (or any compatible client) to intercept API calls and track:
- Predicted vs actual input tokens
- Cache hits/writes
- Output tokens per turn
- Cumulative costs with cache savings

Works with both real Anthropic client and mock clients.
"""

from dataclasses import dataclass
from typing import Any, Optional

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None  # Allow running with mock client only


@dataclass
class TokenTurn:
    """A single turn in the agent loop with token accounting."""
    turn_num: int
    predicted_input: int
    actual_input: int
    cache_read: int
    cache_write: int
    output: int
    thinking: int = 0

    @property
    def total_this_turn(self) -> float:
        """
        Calculate what was actually paid this turn, accounting for cache.
        Cache reads cost 0.1x, cache writes cost 1.25x, everything else 1.0x.
        """
        cache_cost = self.cache_write * 1.25 + self.cache_read * 0.1
        uncached_cost = max(0, self.actual_input - self.cache_read - self.cache_write)
        return cache_cost + uncached_cost + self.output

    @property
    def cumulative_savings(self) -> float:
        """Cost saved by caching this turn vs if nothing were cached."""
        if self.cache_read == 0:
            return 0
        return self.cache_read * (1 - 0.1)  # 0.9x savings per cached token


class TokenTracer:
    """
    Drop-in wrapper for Anthropic client to track token usage per turn.

    Usage:
        client = Anthropic()
        tracer = TokenTracer(client)
        response = tracer.create_message(model="claude-opus-4-8", ...)
        tracer.table()
        tracer.summary()
    """

    def __init__(self, client: Anthropic, verbose: bool = True):
        """
        Initialize the tracer.

        Args:
            client: Anthropic client instance
            verbose: Print live feedback after each turn (default True)
        """
        self.client = client
        self.turns = []
        self.verbose = verbose

    def create_message(self, **kwargs) -> dict:
        """
        Drop-in replacement for client.messages.create()
        Intercepts, predicts, executes, and logs token usage.

        Args:
            **kwargs: Same arguments as client.messages.create()

        Returns:
            Response object from client.messages.create()
        """
        turn_num = len(self.turns) + 1

        # Step 1: Predict input tokens before sending
        predicted = self.client.messages.count_tokens(**kwargs)
        predicted_input = predicted.input_tokens

        # Step 2: Make the actual API call
        response = self.client.messages.create(**kwargs)

        # Step 3: Extract actual usage
        actual_input = response.usage.input_tokens
        cache_read = response.usage.cache_read_input_tokens or 0
        cache_write = response.usage.cache_creation_input_tokens or 0
        output = response.usage.output_tokens

        # Step 4: Log this turn
        turn = TokenTurn(
            turn_num=turn_num,
            predicted_input=predicted_input,
            actual_input=actual_input,
            cache_read=cache_read,
            cache_write=cache_write,
            output=output,
            thinking=0,
        )
        self.turns.append(turn)

        # Step 5: Print live feedback if verbose
        if self.verbose:
            cache_info = ""
            if cache_read > 0:
                cache_info += f"cache_read: {cache_read}t "
            if cache_write > 0:
                cache_info += f"cache_write: {cache_write}t "

            print(f"[Turn {turn_num}] Input: {actual_input}t (pred: {predicted_input}t) | "
                  f"{cache_info}| Output: {output}t | Turn cost: {turn.total_this_turn:.0f}t")

        return response

    def table(self) -> None:
        """Print a formatted table of token usage by turn."""
        if not self.turns:
            print("No turns tracked yet.")
            return

        print("\n" + "="*130)
        print("TOKEN USAGE BY TURN")
        print("="*130)
        print(f"{'Turn':<6} {'Pred Input':<12} {'Actual Input':<14} {'Cache Read':<12} "
              f"{'Cache Write':<13} {'Output':<10} {'Turn Cost':<12} {'Cumulative':<12}")
        print("-"*130)

        cumulative = 0
        for turn in self.turns:
            cumulative += turn.total_this_turn
            print(f"{turn.turn_num:<6} {turn.predicted_input:<12} {turn.actual_input:<14} "
                  f"{turn.cache_read:<12} {turn.cache_write:<13} {turn.output:<10} "
                  f"{turn.total_this_turn:<12.0f} {cumulative:<12.0f}")

        print("="*130)

    def summary(self) -> None:
        """Print a summary of total costs and cache savings."""
        if not self.turns:
            print("No turns tracked yet.")
            return

        total_input = sum(t.actual_input for t in self.turns)
        total_output = sum(t.output for t in self.turns)
        total_cache_read = sum(t.cache_read for t in self.turns)
        total_cache_write = sum(t.cache_write for t in self.turns)

        # Calculate costs
        cache_read_cost = total_cache_read * 0.1
        cache_write_cost = total_cache_write * 1.25
        uncached_input = total_input - total_cache_read - total_cache_write
        uncached_cost = uncached_input * 1.0
        output_cost = total_output * 1.0

        actual_total = cache_read_cost + cache_write_cost + uncached_cost + output_cost
        hypothetical_no_cache = total_input + total_output

        savings = hypothetical_no_cache - actual_total
        savings_pct = (savings / hypothetical_no_cache * 100) if hypothetical_no_cache > 0 else 0

        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Total turns:              {len(self.turns)}")
        print(f"Total input tokens:       {total_input:,}")
        print(f"Total output tokens:      {total_output:,}")
        print(f"Total cache reads:        {total_cache_read:,} (cost: {cache_read_cost:.0f}t @ 0.1x)")
        print(f"Total cache writes:       {total_cache_write:,} (cost: {cache_write_cost:.0f}t @ 1.25x)")
        print(f"Uncached input:           {uncached_input:,} (cost: {uncached_cost:.0f}t @ 1.0x)")
        print(f"Output tokens:            {total_output:,} (cost: {output_cost:.0f}t @ 1.0x)")
        print(f"\nActual total cost:        {actual_total:.0f}t")
        print(f"Without caching:          {hypothetical_no_cache:,}t")
        print(f"Savings from caching:     {savings:.0f}t ({savings_pct:.1f}%)")
        print("="*70)

    def get_cumulative_cost(self) -> float:
        """Get total cost across all turns."""
        return sum(t.total_this_turn for t in self.turns)

    def get_cache_savings(self) -> float:
        """Get total savings from caching across all turns."""
        if not self.turns:
            return 0
        total_cache_read = sum(t.cache_read for t in self.turns)
        return total_cache_read * (1 - 0.1)
