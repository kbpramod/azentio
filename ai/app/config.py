"""Settings loaded from .env (see .env.example)."""
import os

from dotenv import load_dotenv

load_dotenv()

# NLU: "rules" (offline), "llm" (Claude), "auto" (Claude if a key is set, else rules)
NLU_MODE = os.getenv("NLU_MODE", "auto")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-opus-5-5")
LLM_EFFORT = os.getenv("LLM_EFFORT", "low")

# Empty = use the built-in mock bank; otherwise Member B's API base URL
BANKING_API_URL = os.getenv("BANKING_API_URL", "").rstrip("/")

STT_MODEL = os.getenv("STT_MODEL", "small")
STT_MIN_CONFIDENCE = float(os.getenv("STT_MIN_CONFIDENCE", "0.6"))

# "browser" = frontend speaks the text; "edge" = backend makes an mp3 with edge-tts
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "browser")

MAX_AUTH_ATTEMPTS = 3
KB_MIN_SCORE = 2
