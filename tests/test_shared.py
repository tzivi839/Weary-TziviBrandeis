"""
test_shared.py - בדיקות לקוד הדומיין, בלי מודל ובלי אינטרנט.

כל פונקציה שמתחילה ב-test_ היא בדיקה אחת, ו-pytest מריץ את כולן.
tmp_path הוא תיקייה זמנית ש-pytest יוצר לכל בדיקה, אז כל בדיקה מתחילה ממצב נקי
ולא נוגעת בארון האמיתי שלך.

תאריכים: 2026-10-29 = חמישי, 2026-10-30 = שישי, 2026-10-31 = שבת.
"""
import httpx
import pytest

from shared.preferences import Preferences
from shared.wardrobe import Wardrobe
from shared.weather import get_weather, rain_level


def make_wardrobe(tmp_path):
    w = Wardrobe(state_dir=tmp_path)
    w.add_item("חולצה לבנה", "top", "white", 12, 30, ["casual", "work"])        # top-001
    w.add_item("חולצה אלגנטית שמנת", "top", "cream", 12, 30, ["shabbat", "event"])  # top-002
    w.add_item("חצאית שחורה", "bottom", "black", 5, 30, ["casual", "work"])     # bottom-001
    w.add_item("שמלת שבת כחולה", "one-piece", "navy", 10, 25, ["shabbat", "event"])  # one-piece-001
    w.add_item("מעיל", "outer", "gray", 0, 16, ["casual", "work", "shabbat"],
               wash_after_wear=False)                                            # outer-001
    w.add_item("מגפיים", "shoes", "black", 0, 18, ["casual", "work"],
               heavy_rain_only=True, wash_after_wear=False)                     # shoes-001
    return w


def test_ids_are_per_category(tmp_path):
    w = make_wardrobe(tmp_path)
    assert [i["id"] for i in w.items][:3] == ["top-001", "top-002", "bottom-001"]


def test_weather_temperature(tmp_path):
    w = make_wardrobe(tmp_path)
    result = w.find_clothes(temp=22, rain="dry", day="2026-10-29")
    assert "top-001" in result        # חולצה מתאימה ל-22 מעלות
    assert "outer-001" not in result  # מעיל לא


def test_boots_only_in_heavy_rain(tmp_path):
    w = make_wardrobe(tmp_path)
    assert "shoes-001" not in w.find_clothes(10, "dry", "2026-10-29")
    assert "shoes-001" not in w.find_clothes(10, "rain", "2026-10-29")
    assert "shoes-001" in w.find_clothes(10, "heavy", "2026-10-29")


def test_shabbat_only_elegant_and_no_boots(tmp_path):
    w = make_wardrobe(tmp_path)
    # שבת עם גשם עז: עדיין בלי מגפיים, ורק בגדי שבת
    result = w.find_clothes(14, "heavy", "2026-10-31")
    assert "one-piece-001" in result and "top-002" in result
    assert "top-001" not in result     # חולצה יומיומית
    assert "shoes-001" not in result   # מגפיים


def test_laundry_rule(tmp_path):
    w = make_wardrobe(tmp_path)
    w.log_outfit(["top-001", "outer-001"], day="2026-10-29")
    result = w.find_clothes(14, "dry", "2026-10-30")
    assert "top-001" not in result    # בכביסה
    assert "outer-001" in result      # מעיל לא נכנס לכביסה


def test_same_weekday_last_week_rule(tmp_path):
    w = make_wardrobe(tmp_path)
    w.log_outfit(["outer-001"], day="2026-10-22")   # חמישי שעבר
    assert "outer-001" not in w.find_clothes(12, "dry", "2026-10-29")
    assert "outer-001" in w.find_clothes(12, "dry", "2026-10-30")


def test_disliked_combo_not_items(tmp_path):
    w = make_wardrobe(tmp_path)
    w.log_outfit(["top-001", "bottom-001"], day="2026-10-29", liked=False)
    w.laundry_done()
    result = w.find_clothes(20, "dry", "2026-10-30")
    assert "top-001|" in result and "bottom-001|" in result   # הבגדים עצמם עדיין מוצעים
    assert "avoid together: bottom-001+top-001" in result      # רק השילוב מסומן


def test_state_survives_new_instance(tmp_path):
    make_wardrobe(tmp_path).log_outfit(["top-001"], day="2026-10-29")
    fresh = Wardrobe(state_dir=tmp_path)   # "סשן 2": מופע חדש שטוען מהדיסק
    assert len(fresh.items) == 6
    assert fresh.log[0]["items"] == ["top-001"]


def test_bad_input_raises(tmp_path):
    w = make_wardrobe(tmp_path)
    with pytest.raises(ValueError):
        w.add_item("כובע", "hat", "red", 0, 10, ["casual"])
    with pytest.raises(ValueError):
        w.remove_item("top-999")
    with pytest.raises(ValueError):
        w.find_clothes(20, "sunny", "2026-10-29")


def test_preferences_replace_same_topic(tmp_path):
    p = Preferences(state_dir=tmp_path)
    p.save_preference("city", "Jerusalem")
    result = p.save_preference("city", "Haifa")     # בקשה סותרת
    assert "replaced: Jerusalem" in result
    assert Preferences(state_dir=tmp_path).prefs == {"city": "Haifa"}


def test_rain_levels():
    assert rain_level(20, 0) == "dry"
    assert rain_level(80, 3) == "rain"
    assert rain_level(90, 15) == "heavy"


def test_weather_offline():
    # client מדומה, רק בבדיקה: עונה תשובות קבועות בלי לגשת לאינטרנט
    def fake_api(request):
        if "geocoding" in request.url.host:
            return httpx.Response(200, json={"results": [
                {"name": "Jerusalem", "latitude": 31.77, "longitude": 35.21}]})
        return httpx.Response(200, json={"daily": {
            "temperature_2m_min": [9.6], "temperature_2m_max": [15.2],
            "precipitation_probability_max": [90], "precipitation_sum": [14.0]}})

    client = httpx.Client(transport=httpx.MockTransport(fake_api))
    assert get_weather("Jerusalem", "2026-10-29", client) == \
        "Jerusalem 2026-10-29: 10-15C, rain 90% 14.0mm -> heavy"
