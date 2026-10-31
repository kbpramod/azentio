"""Speech-to-text evaluation: accents + background noise.

1) Generate SYNTHETIC test clips (neural TTS voices, several English accents) and noisy copies:
       python -m tests.audio_eval --generate
2) Transcribe every clip with faster-whisper, then check what the agent understood:
       python -m tests.audio_eval
Reports word error rate (WER), whether the expected intents/entities were extracted, and STT time.
Writes tests/audio_results.json. Note: TTS voices are cleaner than real callers; also test real recordings.
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
AUDIO = ROOT / "audio"
sys.path.insert(0, str(ROOT.parent))

VOICES = {"in-f": "en-IN-NeerjaNeural", "in-m": "en-IN-PrabhatNeural", "us-m": "en-US-GuyNeural", "gb-f": "en-GB-SoniaNeural"}
NOISE_LEVEL = 0.06  # pink noise amplitude mixed under the speech (roughly a busy room)

CLIPS = [
    {"id": "status_emi", "text": "I applied for a personal loan last week. What is the status, and when is my first instalment due?",
     "intents": ["loan_status", "emi_enquiry"], "entities": {"product": "personal"}},
    {"id": "customer_id", "text": "My customer ID is C 1 0 2 3.", "intents": [], "entities": {"customer_id": "C1023"}},
    {"id": "dob", "text": "My date of birth is 12th March 1995.", "intents": [], "entities": {"dob": "1995-03-12"}},
    {"id": "schedule", "text": "Can you send me the repayment schedule?", "intents": ["repayment_schedule"], "entities": {}},
    {"id": "fraud", "text": "There is a debit of twenty thousand rupees on my account that I never made.",
     "intents": ["complaint"], "entities": {"complaint_category": "unauthorised_txn"}},
    {"id": "correction", "text": "No, I meant my vehicle loan, not my personal loan.", "intents": [], "entities": {"product": "vehicle"}},
    {"id": "unknown", "text": "Can you increase my credit card limit?", "intents": ["unknown"], "entities": {}},
    {"id": "human", "text": "I want to talk to a real person.", "intents": ["human_handoff"], "entities": {}},
    {"id": "claim", "text": "What is happening with my insurance claim?", "intents": ["claim_status"], "entities": {}},
]


def clip_files():
    for c in CLIPS:
        for v in VOICES:
            for noisy in (False, True):
                yield c, v, noisy, AUDIO / f"{c['id']}__{v}{'__noisy' if noisy else ''}.mp3"


async def _tts(text, voice, out):
    import edge_tts
    await edge_tts.Communicate(text, voice).save(str(out))


def generate():
    AUDIO.mkdir(exist_ok=True)
    for c, v, noisy, path in clip_files():
        if noisy or path.exists():
            continue
        asyncio.run(_tts(c["text"], VOICES[v], path))
    for c, v, noisy, path in clip_files():
        if not noisy or path.exists():
            continue
        clean = AUDIO / f"{c['id']}__{v}.mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clean),
                        "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude={NOISE_LEVEL}",
                        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:normalize=0", str(path)], check=True)
    print(f"{sum(1 for _ in AUDIO.glob('*.mp3'))} clips in {AUDIO}")


def _words(s):
    s = s.lower().replace("instalment", "installment")
    return re.findall(r"[a-z0-9]+", s)


def wer(ref, hyp):
    r, h = _words(ref), _words(hyp)
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(h)] / max(len(r), 1)


def evaluate():
    from app import stt
    from app.nlu import rules_parse

    stt._get_model()  # load once, outside timing
    rows = []
    for c, v, noisy, path in clip_files():
        t0 = time.perf_counter()
        text, conf = stt.transcribe_bytes(path.read_bytes(), path.name)
        ms = int((time.perf_counter() - t0) * 1000)
        nlu = rules_parse(text)
        got = {i.name.value for i in nlu.intents}
        fails = [f"intent {i}" for i in c["intents"] if i not in got]
        fails += [f"{k}={getattr(nlu.entities, k)}" for k, val in c["entities"].items() if getattr(nlu.entities, k) != val]
        rows.append({"clip": path.name, "voice": v, "noisy": noisy, "transcript": text, "confidence": conf,
                     "wer": round(wer(c["text"], text), 3), "understood": not fails, "fails": fails, "stt_ms": ms})

    print(f"\n{'CLIP':38} {'WER':>5} {'CONF':>5} {'MS':>6}  OK")
    for r in rows:
        print(f"{r['clip']:38} {r['wer']:>5.2f} {r['confidence']:>5.2f} {r['stt_ms']:>6}  {'yes' if r['understood'] else 'NO  ' + '; '.join(r['fails'])}")
        if not r["understood"]:
            print(f"{'':40}heard: {r['transcript']}")
    for label, sel in (("clean", [r for r in rows if not r["noisy"]]), ("noisy", [r for r in rows if r["noisy"]])):
        print(f"{label:5}: understood {sum(r['understood'] for r in sel)}/{len(sel)}, "
              f"mean WER {sum(r['wer'] for r in sel) / len(sel):.2f}, "
              f"mean STT {sum(r['stt_ms'] for r in sel) // len(sel)} ms")
    (ROOT / "audio_results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true")
    args = ap.parse_args()
    generate() if args.generate else evaluate()
