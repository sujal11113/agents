# LiveKit Voice Interruption Handling Challenge

## Overview
This sample adds a composable interruption layer that plugs in front of LiveKit's
existing ASR/VAD pipeline without touching any code under `livekit-agents/` or
`livekit-plugins/`. The middleware tracks when the agent TTS is speaking,
filters incoming transcription events, and decides when to stop the agent or
forward user speech upstream.

## Modules
All new files live inside `examples/livekit_interruption_handler/`:

- `interrupt_handler/config.py` – environment driven configuration loader.
- `interrupt_handler/filler_lexicons.py` – default filler and command phrases.
- `interrupt_handler/state.py` – async-safe speaking state tracker.
- `interrupt_handler/filter.py` – normalization, filler detection, and command matching.
- `interrupt_handler/logger.py` – shared logging configuration.
- `interrupt_handler/middleware.py` – core interruption logic and metrics.
- `agent_with_interrupts.py` – runnable demo wiring the middleware to mock TTS/ASR.
- `interrupt_handler/tests/test_interrupt_handler.py` – pytest unit tests.

## How it works
1. `SpeakingState` toggles on `on_tts_start` / `on_tts_end` using an
   `asyncio.Lock` to keep updates safe across tasks.
2. `InterruptMiddleware.on_asr_result` normalizes transcription text, evaluates
   confidence, filler words, and command phrases, and decides whether to:
   - Ignore the segment (filler-only or low-confidence murmurs while speaking).
   - Stop TTS immediately via the injected callback and register the speech.
   - Forward the speech upstream when the agent is not speaking.
3. All decisions are logged via `logging` and counted in `metrics`.

## Configuration
Environment variables override defaults at runtime:

| Variable | Default | Description |
| --- | --- | --- |
| `IGNORED_WORDS` | `uh,umm,um,er,erm,hmm,haan,han,haanji,arey,achha,acha,uhh,ummm` | CSV filler lexicon. |
| `COMMAND_WORDS` | `stop,wait,hold on,one second,no,not that,pause,bas,rohko,band karo` | CSV commands that stop the agent. |
| `ASR_CONFIDENCE_THRESHOLD` | `0.45` | Minimum confidence to consider speech while speaking. |
| `ASR_DROP_LOWCONF_WHILE_SPEAKING` | `true` | Drop low-confidence segments while TTS is active. |
| `NORMALIZE_REPEATS` | `true` | Collapse long character repeats before matching. |
| `ALLOW_DYNAMIC_UPDATES` | `false` | Enable runtime updates to filler/command lexicons. |

Set `ALLOW_DYNAMIC_UPDATES=true` to call `InterruptMiddleware.update_fillers([...])`
and `update_commands([...])` safely at runtime.

## Steps to test
1. (Optional) create a virtual environment and install deps:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   pip install pytest
   ```
2. Run the demo to observe logging and behavior:
   ```bash
   python examples/livekit_interruption_handler/agent_with_interrupts.py
   ```
   The script simulates:
   - Filler ignored while the agent talks.
   - A command interruption stopping TTS.
   - Filler recorded while the agent is silent.
   - Low-confidence murmur dropped during speech.
3. Execute unit tests:
   ```bash
   pytest -q examples/livekit_interruption_handler/interrupt_handler/tests/test_interrupt_handler.py
   ```

Example log excerpt:
```
2024-04-15 10:02:31,442 - livekit.interrupt_handler - INFO - TTS started
2024-04-15 10:02:31,532 - livekit.interrupt_handler - INFO - Ignored filler while speaking: 'umm' (final=False)
2024-04-15 10:02:31,640 - livekit.interrupt_handler - INFO - Command detected while speaking -> stopping TTS: 'umm okay stop'
2024-04-15 10:02:31,641 - livekit.interrupt_handler - INFO - TTS ended
2024-04-15 10:02:31,742 - livekit.interrupt_handler - INFO - Registering user speech (speaking=False, final=True): 'umm'
```

## Notes
- The middleware operates purely as an extension; no LiveKit VAD internals are
  modified.
- Designed for Hinglish and other mixed-language phrases via configurable
  lexicons.
- Python 3.10+ standard library only (plus `pytest` for tests).
- Remember to place work on a feature branch before submitting:
  `feature/livekit-interrupt-handler-<yourname>`.
