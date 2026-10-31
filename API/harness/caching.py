"""
caching.py - האחריות: לסמן ל-Claude אילו חלקים לשמור ב-cache (נקודות cache_control).

איך prompt caching עובד:
  Claude קורא כל בקשה לפי הסדר: tools -> system -> messages.
  נקודת cache_control אומרת: "שמור את כל מה שעד כאן". בקריאה הבאה, אם ההתחלה
  זהה בדיוק עד הנקודה, Claude קורא אותה מה-cache במקום לעבד אותה מחדש.

המחיר (claude-opus-5-5, למיליון טוקנים):
  קלט רגיל $4 | כתיבה ל-cache $5 (פעם אחת) | קריאה מה-cache $0.20 (פי 20 פחות!)

שתי נקודות (מותר עד 4):
  1. על ה-system: שומר tools + system. הם זהים בכל קריאה, בכל תור, בכל סשן
     (בזכות context.py, שהוציא מה-system את התאריך והזיכרון).
  2. על הבלוק האחרון בהודעה האחרונה: נקודה "זזה". בתוך תור עם כלים,
     כל קריאה קוראת מה-cache את כל מה שהקריאה הקודמת כבר שלחה.

שימי לב: ה-cache נשמר 5 דקות, וצריך לפחות 512 טוקנים. מתחת לזה Claude פשוט
לא שומר (בלי שגיאה). רואים את זה ב-tokens.py: cache_read=0 ו-cache_write=0.
"""
from .history import to_jsonable   # "." = מאותה תיקייה (harness)

CACHE = {"type": "ephemeral"}   # ephemeral = נשמר 5 דקות מהשימוש האחרון


def log(msg):
    print(f"[caching.py] {msg}")


def _with_breakpoint(message):
    """עותק של ההודעה, עם cache_control על הבלוק האחרון שלה."""
    content = message["content"]
    if isinstance(content, str):
        blocks = [{"type": "text", "text": content}]   # cache_control צריך בלוק, לא מחרוזת
    else:
        blocks = [to_jsonable(b) for b in content]      # עותקים, כדי לא לשנות את המקור
    blocks[-1] = {**blocks[-1], "cache_control": CACHE}
    return {**message, "content": blocks}


def apply(system, messages):
    """מקבל (system, messages) מ-context.py ומחזיר אותם עם נקודות cache."""
    system_blocks = [{"type": "text", "text": system, "cache_control": CACHE}]
    marked = messages[:-1] + [_with_breakpoint(messages[-1])]
    log("breakpoints: tools+system, last message")
    return system_blocks, marked
