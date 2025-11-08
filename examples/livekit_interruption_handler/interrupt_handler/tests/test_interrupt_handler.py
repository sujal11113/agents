"""Unit tests for the LiveKit interruption handler middleware."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from interrupt_handler.config import InterruptConfig
from interrupt_handler.middleware import InterruptMiddleware


def run(coro: asyncio.Future) -> None:
    asyncio.run(coro)


def test_filler_ignored_while_speaking() -> None:
    async def scenario() -> None:
        stop = AsyncMock()
        register = AsyncMock()
        middleware = InterruptMiddleware(
            stop_tts=stop, register_user_speech=register, config=InterruptConfig()
        )

        await middleware.on_tts_start()
        await middleware.on_asr_result("umm", 0.9, True)

        stop.assert_not_awaited()
        register.assert_not_awaited()
        assert middleware.metrics["ignored_fillers"] == 1

    run(scenario())


def test_command_stops_while_speaking() -> None:
    async def scenario() -> None:
        stop = AsyncMock()
        register = AsyncMock()
        middleware = InterruptMiddleware(
            stop_tts=stop, register_user_speech=register, config=InterruptConfig()
        )

        await middleware.on_tts_start()
        await middleware.on_asr_result("please wait", 0.7, True)

        stop.assert_awaited()
        register.assert_awaited_once_with("please wait")
        assert middleware.metrics["interruptions"] == 1

    run(scenario())


def test_nonfiller_interrupts_while_speaking() -> None:
    async def scenario() -> None:
        stop = AsyncMock()
        register = AsyncMock()
        middleware = InterruptMiddleware(
            stop_tts=stop, register_user_speech=register, config=InterruptConfig()
        )

        await middleware.on_tts_start()
        await middleware.on_asr_result("i have a question", 0.8, True)

        stop.assert_awaited()
        register.assert_awaited_once_with("i have a question")
        assert middleware.metrics["interruptions"] == 1

    run(scenario())


def test_filler_registers_when_quiet() -> None:
    async def scenario() -> None:
        stop = AsyncMock()
        register = AsyncMock()
        middleware = InterruptMiddleware(
            stop_tts=stop, register_user_speech=register, config=InterruptConfig()
        )

        await middleware.on_asr_result("umm", 0.8, True)

        stop.assert_not_awaited()
        register.assert_awaited_once_with("umm")
        assert middleware.metrics["ignored_fillers"] == 0

    run(scenario())


def test_low_confidence_drop_while_speaking() -> None:
    async def scenario() -> None:
        stop = AsyncMock()
        register = AsyncMock()
        middleware = InterruptMiddleware(
            stop_tts=stop, register_user_speech=register, config=InterruptConfig()
        )

        await middleware.on_tts_start()
        await middleware.on_asr_result("hmm", 0.1, False)

        stop.assert_not_awaited()
        register.assert_not_awaited()
        assert middleware.metrics["lowconf_drops"] == 1

    run(scenario())
