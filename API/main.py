"""
main.py - מריץ את כל התרחיש על גרסת ה-API, ושומר את כל המדידות לקובץ.

הרצה (מתיקיית הפרויקט):
    python API/main.py --scenario scenario.json --out results/api.json

מה קורה:
  1. מוחקים את תיקיית המצב של הריצה -> כל ריצה מתחילה ממצב נקי (דרישת התרגיל).
  2. לכל סשן ב-scenario.json יוצרים Weary *חדש*, עם התאריך של הסשן.
     סשן 2 לא יודע כלום חוץ ממה שנשמר לדיסק בסשן 1 - בדיוק כמו הפעלה מחדש.
  3. אחרי כל תור שומרים: טוקנים, קריאות למודל, כלים, עלות וזמן.
  4. מריצים את הבדיקות: חלק אחרי סשן 1, וחלק בסוף.
  5. סופרים שורות קוד לכל קובץ ב-harness, וכותבים הכול ל-JSON.
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from API.agent import EFFORT, MODEL, Weary           # noqa: E402
from shared.checks import run_checks                  # noqa: E402
from shared.linecount import code_lines               # noqa: E402

HARNESS_PARTS = ["loop", "tools", "history", "memory", "context", "compaction", "caching", "tokens"]
STATE_DIR = ROOT / "state" / "api-run"   # נפרד מהארון של השיחות החופשיות שלך


def log(msg):
    print(f"[main.py] {msg}")


def run_scenario(scenario, state_dir=STATE_DIR, client=None, weather_client=None):
    shutil.rmtree(state_dir, ignore_errors=True)
    log(f"clean state: {state_dir}")

    turns, checks, number = [], [], 0
    started = time.time()

    for session in scenario["sessions"]:
        log(f"--- session {session['session']} ({session['day']}): new Weary, state from disk ---")
        weary = Weary(state_dir=state_dir, day=session["day"],
                      client=client, weather_client=weather_client)

        for user_text in session["turns"]:
            number += 1
            log(f"turn {number}: {user_text}")
            result = weary.ask(user_text)
            t = result["tokens"]
            turns.append({
                "turn": number,
                "session": session["session"],
                "day": session["day"],
                "user": user_text,
                "text": result["text"],
                "model_calls": result["model_calls"],
                "tools": result["tools"],
                "tokens": {k: t[k] for k in ("input", "cache_read", "cache_write", "output")},
                "cache_pct": t["cache_pct"],
                "cost_usd": t["cost_usd"],
                "seconds": result["seconds"],
                "compacted": result.get("compacted", False),
            })
            print(f"\nWearMe: {result['text']}\n")

        # הבדיקות של "אחרי סשן 1" רצות כאן, על המצב שבדיסק באותו רגע
        checks += run_checks(scenario["checks"], f"after_session_{session['session']}", state_dir, turns)

    checks += run_checks(scenario["checks"], "end", state_dir, turns)

    totals = {k: round(sum(t["tokens"][k] for t in turns)) for k in ("input", "cache_read", "cache_write", "output")}
    all_input = totals["input"] + totals["cache_read"] + totals["cache_write"]
    totals["cache_pct"] = round(100 * totals["cache_read"] / all_input, 1) if all_input else 0.0
    totals["model_calls"] = sum(t["model_calls"] for t in turns)
    totals["cost_usd"] = round(sum(t["cost_usd"] for t in turns), 5)
    totals["seconds"] = round(time.time() - started, 1)

    lines = {part: code_lines(ROOT / "API" / "harness" / f"{part}.py") for part in HARNESS_PARTS}
    lines["total"] = sum(lines.values())

    passed = sum(c["passed"] for c in checks)
    return {
        "version": "api",
        "model": MODEL,
        "effort": EFFORT,
        "turns": turns,
        "totals": totals,
        "checks": checks,
        "checks_passed": f"{passed}/{len(checks)}",
        "lines_of_code": lines,
    }


def main():
    parser = argparse.ArgumentParser(description="Run the Weary scenario on the API harness")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
    results = run_scenario(scenario)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    t = results["totals"]
    log(f"done: {t['model_calls']} model calls, cache {t['cache_pct']}%, "
        f"${t['cost_usd']:.4f}, {t['seconds']}s")
    log(f"checks passed: {results['checks_passed']}")
    for c in results["checks"]:
        log(f"  {'PASS' if c['passed'] else 'FAIL'}  {c['id']}")
    log(f"results written to {out}")


if __name__ == "__main__":
    main()
