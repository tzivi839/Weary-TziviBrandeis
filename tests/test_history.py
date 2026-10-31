"""
test_history.py - בודק שהשיחה נשמרת לדיסק ושסשן חדש ממשיך ממנה. בלי מודל.
"""
import json

from API.agent import Weary
from API.harness.history import History
from tests.test_loop import FakeClient, text, text_of, tool_use


def test_new_session_continues_conversation(tmp_path):
    # סשן 1: שאלה עם כלי
    s1 = Weary(state_dir=tmp_path, day="2026-10-29", client=FakeClient([
        ([tool_use("t1", "save_preference", {"topic": "city", "text": "Jerusalem"})], "tool_use"),
        ([text("שמרתי")], "end_turn"),
    ]))
    s1.ask("אני גרה בירושלים")

    # סשן 2: מופע חדש לגמרי, כמו הפעלה מחדש של התוכנה
    client2 = FakeClient([([text("בוקר טוב")], "end_turn")])
    s2 = Weary(state_dir=tmp_path, day="2026-10-30", client=client2)
    assert len(s2.messages) == 4               # user, assistant, tool_result, assistant
    s2.ask("בוקר טוב")

    sent = client2.sent[0]["messages"]
    assert sent[0]["content"] == "אני גרה בירושלים"   # המודל קיבל גם את סשן 1
    assert text_of(sent[-1]).endswith("בוקר טוב")  # ואחריה השאלה החדשה


def test_history_is_append_only(tmp_path):
    h = History(tmp_path)
    h.save_new([{"role": "user", "content": "א"}])
    first_line = h.path.read_text(encoding="utf-8")
    h.save_new([{"role": "user", "content": "א"}, {"role": "assistant", "content": "ב"}])
    content = h.path.read_text(encoding="utf-8")
    assert content.startswith(first_line)      # השורה הראשונה לא השתנתה
    assert len(content.splitlines()) == 2      # ונוספה רק שורה אחת
    assert json.loads(content.splitlines()[1])["message"]["content"] == "ב"
