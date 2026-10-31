"""
test_main.py - מריץ את כל התרחיש עם client מדומה, ובודק את מבנה קובץ התוצאות. בלי מודל.
"""
import json

from API.main import HARNESS_PARTS, run_scenario
from shared.linecount import code_lines
from tests.test_loop import FakeClient, text

SCENARIO = json.load(open("scenario.json", encoding="utf-8"))


def test_scenario_results_structure(tmp_path):
    n_turns = sum(len(s["turns"]) for s in SCENARIO["sessions"])
    client = FakeClient([([text(f"תשובה {i}")], "end_turn") for i in range(n_turns)])
    results = run_scenario(SCENARIO, state_dir=tmp_path / "run", client=client)

    assert len(results["turns"]) == n_turns
    first = results["turns"][0]
    assert set(first["tokens"]) == {"input", "cache_read", "cache_write", "output"}
    assert {"model_calls", "tools", "cost_usd", "seconds"} <= set(first)
    assert [t["session"] for t in results["turns"]] == [1] * 4 + [2] * 4
    assert len(results["checks"]) == len(SCENARIO["checks"])     # כל הבדיקות רצו
    assert set(results["lines_of_code"]) == set(HARNESS_PARTS) | {"total"}


def test_code_lines_skips_comments_docstrings_and_blanks(tmp_path):
    f = tmp_path / "x.py"
    f.write_text('"""docstring\nline 2"""\n\n# comment\nx = 1\n\ndef f():\n    """doc"""\n    return x\n',
                 encoding="utf-8")
    assert code_lines(f) == 3        # x = 1, def f():, return x
