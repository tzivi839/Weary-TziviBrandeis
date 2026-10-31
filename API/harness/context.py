"""
context.py - האחריות: מה בדיוק נשלח ל-Claude בכל קריאה.

ההיסטוריה המלאה נשמרת בדיסק (history.py), אבל לא כולה צריכה להישלח.
ארבעה כללים:

  1. הוראות קבועות ב-system.
     רק החוקים של Weary, שלא משתנים אף פעם. בלי תאריך ובלי זיכרון.

  2. מידע משתנה מוצמד לשאלה הנוכחית בלבד.
     התאריך והזיכרון (memory.py) נכנסים לתחילת ההודעה האחרונה שלך, בתוך <context>.
     למה לא ב-system? כי כל שינוי ב-system "שובר" את ה-cache של כל מה שאחריו
     (נראה את זה ב-caching.py). ככה ה-system וההודעות הישנות נשארים זהים מתור לתור.
     ההודעה בדיסק נשארת נקייה: ההצמדה קורית רק בעותק שנשלח.

  3. חלון של התורות האחרונים בלבד.
     נשלחים רק MAX_TURNS התורות האחרונים. מה שקרה לפני כן (למשל הכנסת כל הארון
     בסשן הקודם) כבר נשמר בארון ובזיכרון, ולא צריך לשלוח אותו שוב.
     החלון תמיד מתחיל בהודעה שלך, כדי לא לחתוך באמצע זוג tool_use/tool_result.

  4. תוצאות כלים ישנות מקוצרות.
     רשימת בגדים מאתמול כבר לא נכונה (חלק בכביסה), אז אין טעם לשלוח אותה שוב במלואה.
     תוצאות בתור הנוכחי נשלחות מלאות.
"""

MAX_TURNS = 4            # כמה תורות אחרונים נשלחים
OLD_RESULT_CHARS = 80    # לאיזה אורך מקצרים תוצאת כלי ישנה

SYSTEM = """You are Weary, the wardrobe assistant behind the WearMe app.
Answer in Hebrew, short and warm.
Today's date and what you remember about the user are in <context> in the latest message.
Always use tools: get_weather before suggesting clothes, then find_clothes.
Suggest one complete outfit (top + skirt, or a dress, plus shoes and outer layer if needed).
Never invent items that are not in the wardrobe.
Save anything the user tells you about themselves with save_preference.
Use what you remember without asking again, e.g. the user's city."""


def log(msg):
    print(f"[context.py] {msg}")


def _is_user_text(message):
    """הודעה שאת כתבת (ולא הודעת tool_result שגם היא role=user)."""
    return message["role"] == "user" and isinstance(message["content"], str)


def _trim_tool_results(message):
    """עותק של הודעת tool_result, עם תוכן מקוצר. המקור (וההיסטוריה בדיסק) לא משתנים."""
    if message["role"] != "user" or isinstance(message["content"], str):
        return message, 0
    trimmed, count = [], 0
    for block in message["content"]:
        content = block.get("content", "")
        if block.get("type") == "tool_result" and len(content) > OLD_RESULT_CHARS:
            block = {**block, "content": content[:OLD_RESULT_CHARS] + "...[old, trimmed]"}
            count += 1
        trimmed.append(block)
    return {**message, "content": trimmed}, count


def build(messages, day_line, memory_text, summary=None, summary_upto=0):
    """
    מקבל את כל השיחה ומחזיר (system, הודעות לשליחה).
    אם יש סיכום (compaction.py): ההודעות שהוא מחליף לא נשלחות, והסיכום עצמו
    נכנס ל-<context> של השאלה הנוכחית.
    """
    if summary:
        memory_text += f"\nSummary of earlier conversation:\n{summary}"
    turn_starts = [i for i, m in enumerate(messages) if _is_user_text(m) and i >= summary_upto]
    window_start = turn_starts[-MAX_TURNS] if len(turn_starts) > MAX_TURNS else turn_starts[0]
    current = turn_starts[-1]   # איפה מתחיל התור הנוכחי

    to_send, trimmed = [], 0
    for i in range(window_start, len(messages)):
        message = messages[i]
        if i < current:                       # תור ישן: מקצרים תוצאות כלים
            message, n = _trim_tool_results(message)
            trimmed += n
        elif i == current:                    # השאלה הנוכחית: מצמידים את ה-context
            message = {"role": "user", "content":
                       f"<context>\n{day_line}\n{memory_text}\n</context>\n\n{message['content']}"}
        to_send.append(message)

    log(f"sending {len(to_send)} of {len(messages)} messages "
        f"(dropped {window_start}, trimmed {trimmed} old tool results)")
    return SYSTEM, to_send
