"""test_tokens.py - בודק את חישוב הטוקנים והעלות, בלי מודל."""
from types import SimpleNamespace as NS

from API.harness import tokens


def usage(inp, out, read=0, write=None):
    return NS(input_tokens=inp, output_tokens=out,
              cache_read_input_tokens=read, cache_creation_input_tokens=write)


def test_sums_all_calls_in_turn():
    t = tokens.summarize([usage(1000, 100), usage(500, 50, read=1500)])
    assert (t["input"], t["output"], t["cache_read"], t["cache_write"]) == (1500, 150, 1500, 0)
    assert t["cache_pct"] == 50.0             # 1500 מתוך 3000 טוקני קלט


def test_cost():
    # מיליון טוקני קלט ($4) + מיליון טוקני פלט ($20)
    assert tokens.summarize([usage(1_000_000, 1_000_000)])["cost_usd"] == 24.0


def test_meter_total():
    m = tokens.Meter()
    m.record([usage(1000, 100)])
    m.record([usage(1000, 100, read=2000)])
    assert m.total()["input"] == 2000
    assert m.total()["cache_pct"] == 50.0
