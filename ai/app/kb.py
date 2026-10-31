"""FAQ knowledge base with an abstain threshold.

Level 1: keyword-overlap retrieval over a SYNTHETIC FAQ (replace with the organiser's KB when provided;
upgrade to embeddings, e.g. Chroma, if the KB is large). Returns None when evidence is weak -> agent abstains.
"""
import json
import re
from pathlib import Path

from . import config

KB_PATH = Path(__file__).parent.parent / "data" / "kb_synthetic.json"
STOP = {"the", "a", "an", "is", "are", "what", "how", "do", "i", "my", "for", "to", "of", "can", "you", "me", "on", "in", "and", "it", "please", "tell"}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP and len(w) > 2}


def _load():
    return json.loads(KB_PATH.read_text(encoding="utf-8"))


def search(question: str):
    q = _tokens(question)
    best, best_score = None, 0
    for item in _load():
        score = len(q & _tokens(item["question"] + " " + " ".join(item["keywords"])))
        if score > best_score:
            best, best_score = item, score
    if best is None or best_score < config.KB_MIN_SCORE:
        return None
    return {**best, "score": best_score}
