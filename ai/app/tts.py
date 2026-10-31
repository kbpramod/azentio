"""Text-to-speech integration contract.

Contract (for Member A):
  TurnResponse.reply_text       -> always present
  TurnResponse.reply_audio_url  -> URL of an mp3 when TTS_PROVIDER="edge";
                                   null when TTS_PROVIDER="browser" (frontend speaks reply_text
                                   with window.speechSynthesis)
Providers are swappable without changing the API.
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import config

log = logging.getLogger(__name__)
AUDIO_DIR = Path(__file__).parent.parent / "audio_out"
VOICE = "en-IN-NeerjaNeural"


def synthesize(text: str, session_id: str, turn_no: int) -> str | None:
    if config.TTS_PROVIDER != "edge":
        return None
    try:
        import edge_tts

        AUDIO_DIR.mkdir(exist_ok=True)
        out = AUDIO_DIR / f"{session_id}-{turn_no}.mp3"
        # run in a worker thread: the API handler already owns an event loop
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(asyncio.run, edge_tts.Communicate(text, VOICE).save(str(out))).result(timeout=15)
        return f"/audio/{out.name}"
    except Exception as exc:  # TTS failure must never break the turn; frontend falls back to browser voice
        log.warning("TTS failed, falling back to browser voice: %s", exc)
        return None
