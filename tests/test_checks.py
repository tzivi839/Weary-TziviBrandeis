"""
test_checks.py - בודק שהבדיקות של התרחיש עצמן עובדות.
"מריצים" את התרחיש ביד (בלי מודל): קוראים לכלים בדיוק כמו שהמודל היה אמור,
ומוודאים שכל 10 הבדיקות עוברות. ואז מקלקלים משהו ומוודאים שבדיקה נכשלת.
"""
import json

from shared.checks import run_checks
from shared.preferences import Preferences
from shared.wardrobe import Wardrobe

SCENARIO = json.load(open("scenario.json", encoding="utf-8"))
CHECKS = SCENARIO["checks"]

CLOTHES = [  # (שם, קטגוריה, צבע, מינ', מקס', אירועים, הגדרות נוספות)
    ("חולצה לבנה", "top", "white", 12, 30, ["casual", "work"], {}),
    ("חולצה כחולה", "top", "blue", 12, 30, ["casual", "work"], {}),
    ("סוודר ירוק", "top", "green", 5, 18, ["casual", "work"], {}),
    ("חצאית שחורה", "bottom", "black", 5, 30, ["casual", "work"], {}),
    ("חצאית כתומה", "bottom", "orange", 12, 30, ["casual"], {}),
    ("שמלת שבת כחולה כהה", "one-piece", "navy", 10, 25, ["shabbat", "event"], {}),
    ("חולצה אלגנטית שמנת", "top", "cream", 12, 30, ["shabbat", "event"], {}),
    ("מעיל אפור", "outer", "gray", 0, 16, ["casual", "work", "shabbat"], {"wash_after_wear": False}),
    ("מגפיים שחורים", "shoes", "black", 0, 18, ["casual", "work"],
     {"heavy_rain_only": True, "wash_after_wear": False}),
    ("נעלי שבת שחורות", "shoes", "black", 5, 30, ["shabbat", "event"], {"wash_after_wear": False}),
    ("סניקרס לבנות", "shoes", "white", 10, 30, ["casual"], {"rain_ok": False, "wash_after_wear": False}),
]


def play_scenario(tmp_path):
    w, p = Wardrobe(tmp_path), Preferences(tmp_path)
    for name, cat, color, lo, hi, occ, extra in CLOTHES:
        w.add_item(name, cat, color, lo, hi, occ, **extra)
    p.save_preference("city", "Jerusalem")
    w.log_outfit(["top-001", "bottom-001", "outer-001"], day="2026-10-29", liked=True)
    mid = run_checks(CHECKS, "after_session_1", tmp_path, [])

    # סשן 2: מופע חדש שטוען מהדיסק
    w = Wardrobe(tmp_path)
    w.remove_item("top-003")
    w.laundry_done()
    turns = [
        {"turn": 5, "text": "היום אפשר את החולצה הכחולה עם החצאית הכתומה",
         "tools": [{"name": "get_weather", "input": {"city": "Jerusalem", "day": "2026-10-30"}}]},
        {"turn": 6, "text": "...",
         "tools": [{"name": "find_clothes", "input": {"temp": 14, "rain": "dry", "day": "2026-10-31"}}]},
    ]
    end = run_checks(CHECKS, "end", tmp_path, turns)
    return mid, end


def test_all_checks_pass_on_correct_run(tmp_path):
    mid, end = play_scenario(tmp_path)
    assert len(mid) + len(end) == 10
    assert all(r["passed"] for r in mid + end), mid + end


def test_check_fails_when_state_is_wrong(tmp_path):
    play_scenario(tmp_path)
    Wardrobe(tmp_path).log_outfit(["top-002"], day="2026-10-30")   # משהו נשאר בכביסה
    end = run_checks(CHECKS, "end", tmp_path, [])
    failed = {r["id"] for r in end if not r["passed"]}
    assert "laundry_cleared" in failed
