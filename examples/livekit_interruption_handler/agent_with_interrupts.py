"""Runnable demo showcasing the interruption handler middleware."""

from __future__ import annotations

import asyncio
from typing import List, Optional

from interrupt_handler import InterruptMiddleware


class SimulatedAgent:
    """Simple agent with mock TTS and ASR wiring for demonstration purposes."""

    def __init__(self) -> None:
        self._tts_task: Optional[asyncio.Task[None]] = None
        self.user_transcripts: List[str] = []
        self.middleware = InterruptMiddleware(
            stop_tts=self.stop_tts_now,
            register_user_speech=self.register_user_speech,
        )

    async def speak(self, text: str) -> None:
        """Simulate TTS playback where longer text takes longer time."""

        await self.middleware.on_tts_start()

        async def _run() -> None:
            try:
                # Roughly 40 ms per character to keep the demo short.
                await asyncio.sleep(0.04 * len(text))
                print(f"[TTS playback complete] {text}")
            except asyncio.CancelledError:
                print("[TTS playback cancelled]")
                raise
            finally:
                await self.middleware.on_tts_end()

        self._tts_task = asyncio.create_task(_run())
        try:
            await self._tts_task
        except asyncio.CancelledError:
            pass

    async def stop_tts_now(self) -> None:
        """Stop the active TTS task if it exists."""

        if self._tts_task and not self._tts_task.done():
            self._tts_task.cancel()
            try:
                await self._tts_task
            except asyncio.CancelledError:
                pass

    async def register_user_speech(self, text: str) -> None:
        """Store and display user speech routed through the middleware."""

        self.user_transcripts.append(text)
        print(f"[REGISTERED USER SPEECH] {text}")

    async def run_demo(self) -> None:
        """Run a scripted scenario covering the key decision paths."""

        async def asr_event(text: str, confidence: Optional[float], is_final: bool) -> None:
            await self.middleware.on_asr_result(text, confidence, is_final)

        # Scenario 1: agent is speaking, filler should be ignored.
        speak_task = asyncio.create_task(self.speak("Welcome to SalesCode.ai!"))
        await asyncio.sleep(0.1)
        await asr_event("umm", 0.9, False)
        await asyncio.sleep(0.1)

        # Scenario 3: speaking + interruption command stops TTS.
        await asr_event("umm okay stop", 0.85, True)
        await asyncio.sleep(0.1)

        # Wait for speaking task to settle after interruption.
        await speak_task

        # Scenario 2: agent is quiet, filler should be registered normally.
        await asr_event("umm", 0.9, True)

        # Scenario 4: low confidence murmur while speaking should be dropped.
        speak_task = asyncio.create_task(self.speak("Let me outline the proposal."))
        await asyncio.sleep(0.1)
        await asr_event("mmm", 0.2, False)
        await asyncio.sleep(0.1)
        await speak_task

        print("\nMetrics:", self.middleware.metrics)
        print("Transcripts routed upstream:", self.user_transcripts)


async def main() -> None:
    agent = SimulatedAgent()
    await agent.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
