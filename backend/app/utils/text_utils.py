import re


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def count_tokens_rough(text: str) -> int:
    return max(1, len(text.split()))
