"""
main.py (SDK) - מריץ את אותו תרחיש על גרסת ה-SDK, ושומר את המדידות באותו מבנה כמו ה-API.

הרצה (מתיקיית הפרויקט, בטרמינל *בלי* ANTHROPIC_API_KEY):
    python SDK/main.py --scenario scenario.json --out results/sdk.json
"""
import argparse
import asyncio
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from SDK.agent import EFFORT, MODEL, Weary, check_no_api_key  # noqa: E402
from shared.checks import run_checks                            # noqa: E402
from shared.linecount import replaces_lines                     # noqa: E402

HARNESS_PARTS = ["loop", "tools", "history", "memory", "context", "compaction", "caching", "tokens"]
STATE_DIR = ROOT / "state" / "sdk-run"
SDK_FILES = [ROOT / "SDK" / "agent.py", ROOT / "SDK" / "tools.py"]


def log(msg):
    print(f"[SDK/main.py] {msg}")


async def run_scenario(scenario, state_dir=STATE_DIR, client_factory=None, weather_client=None):
    shutil.rmtree(state_dir, ignore_errors=True)
    log(f"clean state: {state_dir}")
    extra = {"client_factory": client_factory} if client_factory else {}

    turns, checks, number = [], [], 0
    started = time.time()
    for session in scenario["sessions"]:
        log(f"--- session {session['session']} ({session['day']}): new Weary, state from disk ---")
        weary = Weary(state_dir, day=session["day"], weather_client=weather_client, **extra)
        for user_text in session["turns"]:
            number += 1
            log(f"turn {number}: {user_text}")
            r = await weary.ask(user_text)
            all_input = sum(r["tokens"][k] for k in ("input", "cache_read", "cache_write"))
            turns.append({
                "turn": number, "session": session["session"], "day": session["day"],
                "user": user_text, "text": r["text"], "model_calls": r["model_calls"],
                "tools": r["tools"], "tokens": r["tokens"],
                "cache_pct": round(100 * r["tokens"]["cache_read"] / all_input, 1) if all_input else 0.0,
                "cost_usd": r["cost_usd"], "seconds": r["seconds"],
            })
            print(f"\nWearMe: {r['text']}\n")
        checks += run_checks(scenario["checks"], f"after_session_{session['session']}", state_dir, turns)
    checks += run_checks(scenario["checks"], "end", state_dir, turns)

    totals = {k: sum(t["tokens"][k] for t in turns) for k in ("input", "cache_read", "cache_write", "output")}
    all_input = totals["input"] + totals["cache_read"] + totals["cache_write"]
    totals["cache_pct"] = round(100 * totals["cache_read"] / all_input, 1) if all_input else 0.0
    totals["model_calls"] = sum(t["model_calls"] for t in turns)
    totals["cost_usd"] = round(sum(t["cost_usd"] for t in turns), 5)
    totals["seconds"] = round(time.time() - started, 1)

    lines = replaces_lines(SDK_FILES, HARNESS_PARTS)
    lines["total"] = sum(lines.values())
    passed = sum(c["passed"] for c in checks)
    return {
        "version": "sdk", "model": MODEL, "effort": EFFORT,
        "turns": turns, "totals": totals,
        "checks": checks, "checks_passed": f"{passed}/{len(checks)}",
        "lines_of_code": lines,
    }


def main():
    parser = argparse.ArgumentParser(description="Run the Weary scenario on the Claude Agent SDK")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    check_no_api_key()

    scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
    results = asyncio.run(run_scenario(scenario))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    t = results["totals"]
    log(f"done: {t['model_calls']} model calls, cache {t['cache_pct']}%, ${t['cost_usd']:.4f}, {t['seconds']}s")
    log(f"checks passed: {results['checks_passed']}")
    for c in results["checks"]:
        log(f"  {'PASS' if c['passed'] else 'FAIL'}  {c['id']}")
    log(f"results written to {out}")


if __name__ == "__main__":
    main()
