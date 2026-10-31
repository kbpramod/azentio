"""Run tests/eval_cases.json through the orchestrator (text mode) and print a measured pass/fail table.

Usage (from ai_backend/):   python -m tests.run_eval            # uses NLU_MODE from .env
                            NLU_MODE=rules python -m tests.run_eval
Writes tests/eval_results.json. Numbers reported are only what this run measured.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent))

import os  # noqa: E402

from app.mock_bank import MockBank  # noqa: E402
from app.orchestrator import Orchestrator  # noqa: E402
from app.state import new_session  # noqa: E402


def make_neon():
    from app.neon_bank import NeonBank
    return NeonBank()


def check(resp, exp) -> list[str]:
    fails = []
    reply = resp.reply_text
    names = [i.name.value for i in resp.intents]
    for i in exp.get("intents_include", []):
        if i not in names:
            fails.append(f"intent {i} missing (got {names})")
    for t in exp.get("reply_contains", []):
        if t.lower() not in reply.lower():
            fails.append(f"reply lacks '{t}'")
    for t in exp.get("reply_not_contains", []):
        if t.lower() in reply.lower():
            fails.append(f"reply must not contain '{t}'")
    if "verified" in exp and resp.verified != exp["verified"]:
        fails.append(f"verified={resp.verified}")
    if "state" in exp and resp.state != exp["state"]:
        fails.append(f"state={resp.state}")
    if "ticket_prefix" in exp and not any(t.ticket_id.startswith(exp["ticket_prefix"]) for t in resp.tickets):
        fails.append(f"no {exp['ticket_prefix']} ticket")
    if "escalated" in exp and (resp.escalation is not None) != exp["escalated"]:
        fails.append(f"escalated={resp.escalation is not None}")
    if "escalation_reason" in exp and (not resp.escalation or resp.escalation.reason != exp["escalation_reason"]):
        fails.append(f"escalation_reason={resp.escalation.reason if resp.escalation else None}")
    if "escalation_priority" in exp and (not resp.escalation or resp.escalation.priority != exp["escalation_priority"]):
        fails.append("escalation priority mismatch")
    for src in exp.get("sources_include", []):
        if src not in [s.system for s in resp.sources]:
            fails.append(f"source {src} missing")
    return fails


def run(verbose=True):
    cases = json.loads((ROOT / "eval_cases.json").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        # EVAL_BACKEND=neon runs against the shared database; default is a fresh in-memory mock per case
        backend = make_neon() if os.getenv("EVAL_BACKEND") == "neon" else MockBank()
        orch = Orchestrator(backend=backend)
        s = new_session()
        s.id = "EVAL-" + s.id  # eval rows in the DB are easy to find and clean up
        orch.greet(s)
        case_fails, lat = [], []
        for n, turn in enumerate(case["turns"], 1):
            t0 = time.perf_counter()
            resp = orch.handle_text(s, turn["say"])
            lat.append(int((time.perf_counter() - t0) * 1000))
            f = check(resp, turn["expect"])
            if f:
                case_fails.append({"turn": n, "say": turn["say"], "reply": resp.reply_text, "fails": f})
        results.append({"id": case["id"], "scenario": case["scenario"], "passed": not case_fails,
                        "failures": case_fails, "max_turn_ms": max(lat)})
    passed = sum(r["passed"] for r in results)
    if verbose:
        print(f"\n{'CASE':32} {'RESULT':6} {'MAX ms':>6}")
        for r in results:
            print(f"{r['id']:32} {'PASS' if r['passed'] else 'FAIL':6} {r['max_turn_ms']:>6}")
            for f in r["failures"]:
                print(f"    turn {f['turn']}: {f['fails']}\n      said:  {f['say']}\n      reply: {f['reply']}")
        print(f"\n{passed}/{len(results)} cases passed (text mode, this run)")
    (ROOT / "eval_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return results


if __name__ == "__main__":
    res = run()
    sys.exit(0 if all(r["passed"] for r in res) else 1)
