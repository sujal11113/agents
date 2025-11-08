"""Text normalization and interruption detection helpers."""

from __future__ import annotations

import re
from typing import Iterable, Set

_REPEAT_PATTERN = re.compile(r"(.)\1{2,}")


def normalize_text(text: str, *, normalize_repeats: bool = True) -> str:
    """Lowercase and optionally collapse long character repeats."""

    normalized = text.strip().lower()
    if normalize_repeats:
        normalized = _REPEAT_PATTERN.sub(r"\1", normalized)
    return normalized


def is_filler_only(text: str, fillers: Set[str]) -> bool:
    """Return True when all whitespace-delimited tokens are fillers."""

    if not text:
        return False

    tokens = [token for token in text.split() if token]
    if not tokens:
        return False
    return all(token in fillers for token in tokens)


def _phrase_to_pattern(phrase: str) -> str:
    tokens = [re.escape(token) for token in phrase.split() if token]
    if not tokens:
        return ""
    return r"\b" + r"\s+".join(tokens) + r"\b"


def has_command(text: str, commands: Iterable[str]) -> bool:
    """Detect if any command phrase appears in the text."""

    for phrase in commands:
        pattern = _phrase_to_pattern(phrase)
        if pattern and re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False
