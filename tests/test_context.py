"""
test_context.py - בודק מה נשלח ל-Claude בכל קריאה. בלי מודל.
"""
from API.harness import context


def tool_turn(question, result_text):
    """תור אחד: שאלה, בקשה לכלי, תוצאת הכלי, תשובה."""
    return [
        {"role": "user", "content": question},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t", "name": "x", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t", "content": result_text}]},
        {"role": "assistant", "content": [{"type": "text", "text": "ok"}]},
    ]


def test_context_goes_into_current_message_only():
    messages = tool_turn("שאלה ישנה", "x") + [{"role": "user", "content": "מה ללבוש?"}]
    system, sent = context.build(messages, "Today is 2026-10-30 (Friday).", "- city: Jerusalem")
    assert "2026-10" not in system                       # ה-system קבוע, בלי תאריך
    assert sent[0]["content"] == "שאלה ישנה"             # הודעה ישנה נשלחת כמו שהיא
    assert sent[-1]["content"].startswith("<context>")   # רק השאלה הנוכחית מקבלת context
    assert "city: Jerusalem" in sent[-1]["content"]
    assert messages[-1]["content"] == "מה ללבוש?"        # ההיסטוריה עצמה לא השתנתה


def test_only_last_turns_are_sent():
    messages = []
    for i in range(6):
        messages += tool_turn(f"שאלה {i}", "x")
    messages.append({"role": "user", "content": "שאלה אחרונה"})
    _, sent = context.build(messages, "", "")
    questions = [m["content"] for m in sent if isinstance(m["content"], str)]
    assert len(questions) == context.MAX_TURNS
    assert "שאלה 0" not in questions
    assert sent[0]["role"] == "user" and isinstance(sent[0]["content"], str)  # מתחיל בשאלה


def test_old_tool_results_are_trimmed_current_are_not():
    long = "top-001|חולצה לבנה|white\n" * 20
    messages = tool_turn("אתמול", long) + tool_turn("היום", long)[:3]   # התור הנוכחי באמצע
    _, sent = context.build(messages, "", "")
    assert sent[2]["content"][0]["content"].endswith("[old, trimmed]")  # תור ישן: מקוצר
    assert sent[-1]["content"][0]["content"] == long                    # תור נוכחי: מלא
    assert messages[2]["content"][0]["content"] == long                 # המקור לא השתנה
