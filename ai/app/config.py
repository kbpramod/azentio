"""Settings loaded from .env (see .env.example)."""
import os

from dotenv import load_dotenv

load_dotenv()

# NLU: "rules" (offline), "llm" (Claude), "auto" (Claude if a key is set, else rules)
NLU_MODE = os.getenv("NLU_MODE", "auto")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-opus-5-5")
LLM_EFFORT = os.getenv("LLM_EFFORT", "low")

# Where banking data comes from: "mock" (built-in), "neon" (shared Postgres), or "http" (BANKING_API_URL)
BANK_BACKEND = os.getenv("BANK_BACKEND", "mock")
DATABASE_URL = os.getenv("DATABASE_URL", "")
BANKING_API_URL = os.getenv("BANKING_API_URL", "").rstrip("/")

# base.en + beam 1: measured 18/18 noisy clips understood at ~1.8 s on 8 CPUs (small: ~5.3 s)
STT_MODEL = os.getenv("STT_MODEL", "base.en")
STT_BEAM = int(os.getenv("STT_BEAM", "1"))
# digits (customer IDs) score ~0.55-0.65, so the cutoff sits below that
STT_MIN_CONFIDENCE = float(os.getenv("STT_MIN_CONFIDENCE", "0.45"))

# "browser" = frontend speaks the text; "edge" = backend makes an mp3 with edge-tts
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "browser")

MAX_AUTH_ATTEMPTS = 3
KB_MIN_SCORE = 2
