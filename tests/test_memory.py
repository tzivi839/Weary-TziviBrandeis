"""
test_memory.py - בודק ש-Weary זוכר העדפות ולבושים בין סשנים. בלי מודל.
"""
from API.agent import Weary
from API.harness.memory import Memory
from shared.preferences import Preferences
from shared.wardrobe import Wardrobe
from tests.test_loop import FakeClient, text


def test_recall_summarizes_preferences_and_outfits(tmp_path):
    Preferences(tmp_path).save_preference("city", "Jerusalem")
    w = Wardrobe(tmp_path)
    w.add_item("חולצה לבנה", "top", "white", 12, 30, ["casual"])
    w.add_item("חצאית שחורה", "bottom", "black", 5, 30, ["casual"])
    w.log_outfit(["top-001", "bottom-001"], day="2026-10-29", liked=True)

    recalled = Memory(tmp_path).recall()
    assert "- city: Jerusalem" in recalled
    assert "2026-10-29: חולצה לבנה + חצאית שחורה (liked)" in recalled
    assert "2 items, 2 in laundry" in recalled


def test_only_recent_outfits(tmp_path):
    w = Wardrobe(tmp_path)
    w.add_item("מעיל", "outer", "gray", 0, 16, ["casual"], wash_after_wear=False)
    for day in ["2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"]:
        w.log_outfit(["outer-001"], day=day)
    recalled = Memory(tmp_path).recall()
    assert "2026-10-20" not in recalled        # הכי ישן נשאר בחוץ
    assert "2026-10-23" in recalled


def test_new_session_knows_city_from_memory(tmp_path):
    # סשן 1 שמר את העיר (בלי מודל, ישר לדיסק)
    Preferences(tmp_path).save_preference("city", "Jerusalem")
    # סשן 2: Weary חדש, בלי היסטוריית שיחה בכלל
    client = FakeClient([([text("בוקר טוב")], "end_turn")])
    Weary(state_dir=tmp_path, day="2026-10-30", client=client).ask("מה ללבוש?")
    assert "city: Jerusalem" in client.sent[0]["system"]   # המודל קיבל את זה בהוראות
