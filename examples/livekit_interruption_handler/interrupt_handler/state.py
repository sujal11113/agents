"""Speaking state management for the LiveKit interruption handler."""

from __future__ import annotations

import asyncio


class SpeakingState:
    """Async-safe tracker for the agent TTS speaking state."""

    def __init__(self) -> None:
        self._speaking: bool = False
        self._lock = asyncio.Lock()

    async def set_speaking(self, speaking: bool) -> None:
        """Update the speaking flag in an async-safe manner."""

        async with self._lock:
            self._speaking = speaking

    async def is_speaking(self) -> bool:
        """Return whether the agent is currently speaking."""

        async with self._lock:
            return self._speaking
