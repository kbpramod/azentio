"""Speech-to-text with faster-whisper (local, free, robust to accents/noise).

Browser audio (webm/ogg/mp3/wav) is converted to 16 kHz mono wav with ffmpeg first.
Model loads once, lazily, so text-only mode starts fast and needs no STT install.
"""
import math
import subprocess
import tempfile
from pathlib import Path

from . import config

_model = None


class STTError(Exception):
    pass


def _get_model():
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise STTError("faster-whisper not installed. Run: pip install -r requirements-voice.txt") from exc
        _model = WhisperModel(config.STT_MODEL, device="cpu", compute_type="int8")
    return _model


def _to_wav(src: Path) -> Path:
    dst = src.with_suffix(".16k.wav")
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "16000", str(dst)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise STTError(f"Could not read audio: {r.stderr.strip()[:200]}")
    return dst


def transcribe_bytes(data: bytes, filename: str = "audio.webm", language: str = "en") -> tuple[str, float]:
    """Return (transcript, confidence 0..1)."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / Path(filename).name
        src.write_bytes(data)
        wav = _to_wav(src)
        segments, _info = _get_model().transcribe(
            str(wav), language=language, beam_size=5, vad_filter=True,  # VAD trims silence/noise
            temperature=0.0,  # reproducible output for the same file
        )
        segments = list(segments)
    text = " ".join(s.text.strip() for s in segments).strip()
    if not segments:
        return "", 0.0
    # confidence: mean token probability from average log-prob, penalised by no-speech probability
    conf = sum(math.exp(s.avg_logprob) * (1 - s.no_speech_prob) for s in segments) / len(segments)
    return text, round(conf, 3)
