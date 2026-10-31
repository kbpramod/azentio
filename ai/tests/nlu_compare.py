"""Compare intent detection on phrasing the rules were never written for: rules vs hybrid (rules + local LLM).

    python -m tests.nlu_compare            # needs Ollama running with the configured model
A case passes when every expected intent is found and every expected detail matches.
Extra intents are reported but not counted as failures.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent))

from app import config, nlu  # noqa: E402


def check(res, case):
    got = [i.name.value for i in res.intents]
    fails = [f"missing {i}" for i in case["intents"] if i not in got]
    fails += [f"{k}={getattr(res.entities, k)}" for k, v in case.get("entities", {}).items() if getattr(res.entities, k) != v]
    return got, fails


def run(file="nlu_unseen.json", modes=("rules", "hybrid")):
    cases = json.loads((ROOT / file).read_text(encoding="utf-8"))
    print(f"== {file} ==")
    summary = {}
    rows = []
    for mode in modes:
        config.NLU_MODE = mode
        ok, times, llm_calls = 0, [], 0
        for c in cases:
            t0 = time.perf_counter()
            res = nlu.parse(c["say"])
            ms = int((time.perf_counter() - t0) * 1000)
            got, fails = check(res, c)
            ok += not fails
            times.append(ms)
            llm_calls += res.source == "llm"
            rows.append({"mode": mode, "say": c["say"], "got": got, "source": res.source, "ok": not fails, "fails": fails, "ms": ms})
        summary[mode] = {"passed": ok, "total": len(cases), "llm_used": llm_calls,
                         "mean_ms": sum(times) // len(times), "max_ms": max(times)}

    print(f"\n{'SENTENCE':62} " + " ".join(f"{m.upper():7}" for m in modes))
    for c in cases:
        rs = [next(x for x in rows if x["mode"] == m and x["say"] == c["say"]) for m in modes]
        h = rs[-1]
        print(f"{c['say'][:61]:62} " + " ".join(f"{'ok' if r['ok'] else 'MISS':7}" for r in rs)
              + (f"  (LLM {h['ms']} ms)" if h["source"] == "llm" else "")
              + (f"  -> {'; '.join(h['fails'])} | got {','.join(h['got'])}" if not h["ok"] else ""))
    for mode, s in summary.items():
        print(f"{mode:7}: {s['passed']}/{s['total']} understood | LLM used {s['llm_used']}x | "
              f"mean {s['mean_ms']} ms, max {s['max_ms']} ms")
    (ROOT / "nlu_compare_results.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="nlu_unseen.json")
    ap.add_argument("--modes", nargs="+", default=["rules", "hybrid"])
    a = ap.parse_args()
    run(a.file, tuple(a.modes))
