"""Settings loaded from .env (see .env.example)."""
import os

from dotenv import load_dotenv

load_dotenv()

# NLU: "rules" | "hybrid" (rules first, LLM when rules don't understand) | "llm" (LLM every turn)
NLU_MODE = os.getenv("NLU_MODE", "hybrid")
# LLM: "ollama" = free local model (no key, offline) | "anthropic" = Claude API (needs a key)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
# measured on 8 CPUs: 1.5b ~3.5-4.5 s per call, 3b ~6-8 s, same accuracy on our test sentences
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "8"))  # seconds; on timeout the rules answer
LLM_MODEL = os.getenv("LLM_MODEL", "claude-opus-5-5")
LLM_EFFORT = os.getenv("LLM_EFFORT", "low")

# Where banking data comes from: "mock" (built-in), "neon" (shared Postgres), or "http" (BANKING_API_URL)
BANK_BACKEND = os.getenv("BANK_BACKEND", "mock")
DATABASE_URL = os.getenv("DATABASE_URL", "")
BANKING_API_URL = os.getenv("BANKING_API_URL", "").rstrip("/")
# The team server records calls/turns/audit; only turn this on when running the AI service on its own
RECORD_CALLS = os.getenv("RECORD_CALLS", "false").lower() == "true"

# base.en + beam 1: measured 18/18 noisy clips understood at ~1.8 s on 8 CPUs (small: ~5.3 s)
STT_MODEL = os.getenv("STT_MODEL", "base.en")
STT_BEAM = int(os.getenv("STT_BEAM", "1"))
# digits (customer IDs) score ~0.55-0.65, so the cutoff sits below that
STT_MIN_CONFIDENCE = float(os.getenv("STT_MIN_CONFIDENCE", "0.45"))

# "browser" = frontend speaks the text; "edge" = backend makes an mp3 with edge-tts
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "browser")

MAX_AUTH_ATTEMPTS = 3
KB_MIN_SCORE = 2
