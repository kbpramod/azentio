"""Speech-to-text evaluation: accents, background noise, phone audio and fast speech.

1) Generate SYNTHETIC test clips (neural TTS voices, several English accents) plus harder variants:
       python -m tests.audio_eval --generate
2) Transcribe every clip with faster-whisper, then check what the agent understood:
       python -m tests.audio_eval
Reports word error rate (WER), whether the expected intents/entities were extracted, and STT time,
per variant. Writes tests/audio_results.json.
Note: TTS voices are cleaner than real callers; also test real recordings from the team.
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

# variant -> how it is made from the clean clip (ffmpeg); "fast" is re-synthesised at +30% rate
NOISE = "anoisesrc=color=pink:amplitude={amp}"
VARIANTS = {
    "clean": None,
    "noisy": {"noise": 0.06},                       # busy room
    "loud": {"noise": 0.15},                        # street / crowd
    "phone": {"noise": 0.03, "phone": True},        # 300-3400 Hz, 8 kHz, light noise
    "fast": {"noise": 0.06, "rate": "+30%"},        # quick talker + busy room
}

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


def clip_path(cid, voice, variant):
    return AUDIO / f"{cid}__{voice}{'' if variant == 'clean' else '__' + variant}.mp3"


def clip_files(variants=None):
    for c in CLIPS:
        for v in VOICES:
            for var in (variants or VARIANTS):
                yield c, v, var, clip_path(c["id"], v, var)


async def _tts(text, voice, out, rate="+0%"):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


def _ffmpeg(src, out, noise=0.0, phone=False):
    chain = "[0:a]highpass=f=300,lowpass=f=3400,aresample=8000[s]" if phone else "[0:a]anull[s]"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src)]
    if noise:
        cmd += ["-f", "lavfi", "-i", NOISE.format(amp=noise),
                "-filter_complex", f"{chain};[1:a]aresample={'8000' if phone else '24000'}[n];"
                                   "[s][n]amix=inputs=2:duration=first:normalize=0"]
    else:
        cmd += ["-filter_complex", chain, "-map", "[s]"]
    subprocess.run(cmd + [str(out)], check=True)


def generate():
    AUDIO.mkdir(exist_ok=True)
    for c in CLIPS:
        for v, voice in VOICES.items():
            clean = clip_path(c["id"], v, "clean")
            if not clean.exists():
                asyncio.run(_tts(c["text"], voice, clean))
            for var, spec in VARIANTS.items():
                out = clip_path(c["id"], v, var)
                if spec is None or out.exists():
                    continue
                src = clean
                if spec.get("rate"):
                    src = AUDIO / f"_tmp_{c['id']}_{v}_fast.mp3"
                    asyncio.run(_tts(c["text"], voice, src, rate=spec["rate"]))
                _ffmpeg(src, out, spec.get("noise", 0), spec.get("phone", False))
                if src != clean:
                    src.unlink(missing_ok=True)
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


def evaluate(variants=None):
    from app import config, stt
    from app.nlu import rules_parse

    stt._get_model()  # load once, outside timing
    rows = []
    for c, v, var, path in clip_files(variants):
        if not path.exists():
            continue
        t0 = time.perf_counter()
        text, conf = stt.transcribe_bytes(path.read_bytes(), path.name)
        ms = int((time.perf_counter() - t0) * 1000)
        nlu = rules_parse(text)
        got = {i.name.value for i in nlu.intents}
        fails = [f"intent {i}" for i in c["intents"] if i not in got]
        fails += [f"{k}={getattr(nlu.entities, k)}" for k, val in c["entities"].items() if getattr(nlu.entities, k) != val]
        rows.append({"clip": path.name, "voice": v, "variant": var, "transcript": text, "confidence": conf,
                     "wer": round(wer(c["text"], text), 3), "understood": not fails, "fails": fails,
                     "would_ask_repeat": conf < config.STT_MIN_CONFIDENCE, "stt_ms": ms})
        if fails:
            print(f"MISS {path.name}: {'; '.join(fails)} | heard: {text}", flush=True)

    print(f"\n{'VARIANT':8} {'UNDERSTOOD':>11} {'MEAN WER':>9} {'ASK REPEAT':>11} {'MEAN STT':>9}")
    for var in dict.fromkeys(r["variant"] for r in rows):
        sel = [r for r in rows if r["variant"] == var]
        print(f"{var:8} {sum(r['understood'] for r in sel):>5}/{len(sel):<5} {sum(r['wer'] for r in sel) / len(sel):>9.2f} "
              f"{sum(r['would_ask_repeat'] for r in sel):>11} {sum(r['stt_ms'] for r in sel) // len(sel):>7} ms")
    total = sum(r["understood"] for r in rows)
    print(f"{'ALL':8} {total:>5}/{len(rows):<5}")
    (ROOT / "audio_results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--variants", nargs="*", help=f"subset of {list(VARIANTS)}")
    args = ap.parse_args()
    generate() if args.generate else evaluate(args.variants)
