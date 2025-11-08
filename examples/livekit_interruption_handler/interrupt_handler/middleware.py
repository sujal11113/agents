"""Middleware that filters ASR events for LiveKit interruption handling."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Optional

from .config import InterruptConfig
from .filter import has_command, is_filler_only, normalize_text
from .logger import get_logger
from .state import SpeakingState


class InterruptMiddleware:
    """Interruption aware middleware sitting between ASR and the agent."""

    def __init__(
        self,
        stop_tts: Callable[[], Awaitable[Any]],
        register_user_speech: Callable[[str], Awaitable[Any]],
        *,
        config: Optional[InterruptConfig] = None,
        state: Optional[SpeakingState] = None,
    ) -> None:
        self._stop_tts = stop_tts
        self._register_user_speech = register_user_speech
        self.config = config or InterruptConfig.from_env()
        self.state = state or SpeakingState()
        self.logger = get_logger()
        self.metrics = {
            "ignored_fillers": 0,
            "interruptions": 0,
            "lowconf_drops": 0,
        }
        self._lock = asyncio.Lock()

    async def on_tts_start(self) -> None:
        """Notify the middleware that TTS playback has started."""

        await self.state.set_speaking(True)
        self.logger.info("TTS started")

    async def on_tts_end(self) -> None:
        """Notify the middleware that TTS playback has ended."""

        await self.state.set_speaking(False)
        self.logger.info("TTS ended")

    async def on_asr_result(
        self,
        text: str,
        confidence: Optional[float],
        is_final: bool,
    ) -> None:
        """Process an ASR result and decide whether to interrupt TTS."""

        async with self._lock:
            speaking = await self.state.is_speaking()

            if text is None:
                text = ""

            normalized = normalize_text(
                text, normalize_repeats=self.config.normalize_repeats
            )

            if not normalized:
                self.logger.info(
                    "Ignoring empty transcription (speaking=%s, final=%s)",
                    speaking,
                    is_final,
                )
                return

            if speaking:
                if (
                    confidence is not None
                    and confidence < self.config.asr_confidence_threshold
                    and self.config.drop_low_conf_while_speaking
                ):
                    self.metrics["lowconf_drops"] += 1
                    self.logger.info(
                        "Dropped low-confidence murmur (confidence=%.2f, threshold=%.2f)",
                        confidence,
                        self.config.asr_confidence_threshold,
                    )
                    return

                if has_command(normalized, self.config.command_phrases):
                    self.metrics["interruptions"] += 1
                    self.logger.info(
                        "Command detected while speaking -> stopping TTS: '%s'", text
                    )
                    await self._stop_tts()
                    await self._register_user_speech(text)
                    return

                if is_filler_only(normalized, self.config.ignored_words):
                    self.metrics["ignored_fillers"] += 1
                    self.logger.info(
                        "Ignored filler while speaking: '%s' (final=%s)", text, is_final
                    )
                    return

                self.metrics["interruptions"] += 1
                self.logger.info(
                    "Non-filler speech detected while speaking -> stopping TTS: '%s'",
                    text,
                )
                await self._stop_tts()
                await self._register_user_speech(text)
                return

            self.logger.info(
                "Registering user speech (speaking=%s, final=%s): '%s'",
                speaking,
                is_final,
                text,
            )
            await self._register_user_speech(text)

    def update_fillers(self, fillers: list[str]) -> None:
        """Update the filler lexicon if allowed by configuration."""

        self.config.update_fillers(fillers)
        self.logger.info("Updated filler lexicon: %s", sorted(self.config.ignored_words))

    def update_commands(self, commands: list[str]) -> None:
        """Update the command lexicon if allowed by configuration."""

        self.config.update_commands(commands)
        self.logger.info(
            "Updated command lexicon: %s", sorted(self.config.command_phrases)
        )
