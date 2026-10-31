"""
test_caching.py - בודק את נקודות ה-cache. בלי מודל.
"""
from API.agent import Weary
from API.harness import caching
from tests.test_loop import FakeClient, text, text_of, tool_use


def test_breakpoints_on_system_and_last_message():
    messages = [{"role": "user", "content": "א"}, {"role": "assistant", "content": "ב"},
                {"role": "user", "content": "ג"}]
    system, marked = caching.apply("rules", messages)
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert marked[-1]["content"][-1] == {"type": "text", "text": "ג",
                                         "cache_control": {"type": "ephemeral"}}
    assert marked[0] == messages[0]                 # הודעות קודמות לא משתנות
    assert messages[-1]["content"] == "ג"           # והמקור לא השתנה


def test_prefix_is_identical_between_calls_in_a_turn(tmp_path):
    """
    התנאי לכך שה-cache יעבוד: הקריאה השנייה בתור מתחילה *בדיוק* כמו הראשונה.
    """
    client = FakeClient([
        ([tool_use("t1", "laundry_done", {})], "tool_use"),
        ([text("סיימתי")], "end_turn"),
    ])
    Weary(state_dir=tmp_path, day="2026-10-30", client=client).ask("הכביסה מוכנה")
    first, second = client.sent
    assert first["system"] == second["system"]
    assert first["tools"] == second["tools"]
    # ההודעה הראשונה זהה בתוכן (רק נקודת ה-cache זזה קדימה, להודעה האחרונה)
    assert text_of(first["messages"][0]) == text_of(second["messages"][0])
    assert "cache_control" in second["messages"][-1]["content"][-1]   # הנקודה על האחרונה
