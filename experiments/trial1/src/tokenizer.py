"""Tokenization module using tiktoken."""
import tiktoken

def get_tokenizer(encoding: str = "o200k_base"):
    """Get a tiktoken encoder.
    Args:
        encoding: Encoding name (default: o200k_base used by Claude 3.5)
    Returns:
        tiktoken Encoding object
    """
    return tiktoken.get_encoding(encoding)

def tokenize(text: str, encoding: str = "o200k_base") -> dict:
    """Tokenize text and return breakdown.
    Args:
        text: Text to tokenize
        encoding: Encoding to use
    Returns:
        Dictionary with token information
    """
    enc = get_tokenizer(encoding)
    token_ids = enc.encode(text)
    token_strings = [
        enc.decode_single_token_bytes(tid).decode("utf-8", errors="replace")
        for tid in token_ids
    ]
    return {
        "text": text,
        "token_count": len(token_ids),
        "token_ids": token_ids,
        "tokens": token_strings,
        "encoding": encoding,
    }

def count_tokens(text: str, encoding: str = "o200k_base") -> int:
    """Count tokens in text.
    Args:
        text: Text to count
        encoding: Encoding to use
    Returns:
        Number of tokens
    """
    enc = get_tokenizer(encoding)
    return len(enc.encode(text))