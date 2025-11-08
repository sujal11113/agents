"""Configuration helpers for the LiveKit interruption handler."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Iterable, Set

from .filler_lexicons import DEFAULT_COMMAND_PHRASES, DEFAULT_IGNORED_WORDS


def _parse_csv(value: str) -> Set[str]:
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(slots=True)
class InterruptConfig:
    """Runtime configuration loaded from the environment."""

    ignored_words: Set[str] = field(default_factory=lambda: set(DEFAULT_IGNORED_WORDS))
    command_phrases: Set[str] = field(default_factory=lambda: set(DEFAULT_COMMAND_PHRASES))
    asr_confidence_threshold: float = 0.45
    drop_low_conf_while_speaking: bool = True
    normalize_repeats: bool = True
    allow_dynamic_updates: bool = False

    @classmethod
    def from_env(cls) -> "InterruptConfig":
        """Create configuration by reading environment variables."""

        ignored = os.getenv("IGNORED_WORDS")
        commands = os.getenv("COMMAND_WORDS")
        confidence_raw = os.getenv("ASR_CONFIDENCE_THRESHOLD")
        drop_low_conf = os.getenv("ASR_DROP_LOWCONF_WHILE_SPEAKING")
        normalize_repeats = os.getenv("NORMALIZE_REPEATS")
        allow_dynamic_updates = os.getenv("ALLOW_DYNAMIC_UPDATES")

        ignored_words = (
            _parse_csv(ignored) if ignored is not None else set(DEFAULT_IGNORED_WORDS)
        )
        command_phrases = (
            _parse_csv(commands)
            if commands is not None
            else set(DEFAULT_COMMAND_PHRASES)
        )

        threshold = float(confidence_raw) if confidence_raw is not None else 0.45
        drop_low_conf_flag = (
            _parse_bool(drop_low_conf)
            if drop_low_conf is not None
            else True
        )
        normalize_repeats_flag = (
            _parse_bool(normalize_repeats)
            if normalize_repeats is not None
            else True
        )
        allow_updates_flag = (
            _parse_bool(allow_dynamic_updates)
            if allow_dynamic_updates is not None
            else False
        )

        return cls(
            ignored_words=ignored_words,
            command_phrases=command_phrases,
            asr_confidence_threshold=threshold,
            drop_low_conf_while_speaking=drop_low_conf_flag,
            normalize_repeats=normalize_repeats_flag,
            allow_dynamic_updates=allow_updates_flag,
        )

    def update_fillers(self, fillers: Iterable[str]) -> None:
        """Replace filler word set when dynamic updates are allowed."""

        if not self.allow_dynamic_updates:
            raise RuntimeError("Dynamic updates are disabled by configuration")
        self.ignored_words = {value.strip().lower() for value in fillers if value.strip()}

    def update_commands(self, commands: Iterable[str]) -> None:
        """Replace command phrase set when dynamic updates are allowed."""

        if not self.allow_dynamic_updates:
            raise RuntimeError("Dynamic updates are disabled by configuration")
        self.command_phrases = {
            value.strip().lower() for value in commands if value.strip()
        }
