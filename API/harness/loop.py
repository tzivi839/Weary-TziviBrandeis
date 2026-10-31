"""
loop.py - האחריות: לולאת הסוכן. זה הלב של כל ה-harness.

תור אחד של משתמש יכול לכלול כמה קריאות למודל:
  1. שולחים למודל את השיחה + רשימת הכלים.
  2. אם המודל עונה stop_reason == "tool_use", הוא מבקש להפעיל כלים.
     מפעילים את כולם, ומחזירים את כל התוצאות בהודעה אחת (role="user").
  3. חוזרים לשלב 1, עד שהמודל עונה בטקסט רגיל (stop_reason אחר).

דוגמה: "מה ללבוש היום?"
  קריאה 1 -> המודל: get_weather          -> מחזירים "12-19C, rain"
  קריאה 2 -> המודל: find_clothes         -> מחזירים רשימת בגדים
  קריאה 3 -> המודל: "תלבשי את..."         -> stop_reason="end_turn", סוף התור
"""
import time

MAX_CALLS = 10   # הגנה: אם משהו משתבש, לא נכנסים ללולאה אינסופית (ולא משלמים עליה)


def log(msg):
    print(f"[loop.py] {msg}")


def run_turn(client, messages, toolbox, *, model, effort, build, tools, max_tokens=8000):
    """
    מריץ תור אחד. messages מתעדכנת במקום (מוסיפים לה את כל מה שקרה).
    build היא פונקציה מ-context.py: מקבלת את כל השיחה ומחזירה (system, מה לשלוח).
    היא נקראת לפני *כל* קריאה, כי בתוך תור השיחה גדלה (תוצאות כלים).
    מחזיר מילון עם הטקסט הסופי, הכלים שהופעלו, ה-usage של כל קריאה, והזמן.
    """
    start = time.time()
    tool_calls = []   # לקובץ התוצאות ולבדיקות: אילו כלים הופעלו ועם מה
    usages = []       # usage של כל קריאה למודל, בשביל tokens.py

    for call in range(1, MAX_CALLS + 1):
        system, to_send = build(messages)
        log(f"call {call}: sending {len(to_send)} messages")
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            messages=to_send,
            output_config={"effort": effort},
        )
        usages.append(resp.usage)
        log(f"call {call}: stop_reason={resp.stop_reason}")

        if resp.stop_reason == "max_tokens":
            # המודל נקטע באמצע (למשל באמצע בקשה לכלי). תשובה חתוכה לא נכנסת להיסטוריה:
            # בלוק tool_use בלי tool_result היה שובר את כל הקריאות הבאות בשיחה.
            log("ERROR answer was cut off (max_tokens) - not saved to history")
            return {
                "text": "(התשובה נקטעה כי הייתה ארוכה מדי. נסי לחלק את הבקשה לחלקים קטנים יותר.)",
                "tools": tool_calls,
                "usages": usages,
                "model_calls": len(usages),
                "seconds": round(time.time() - start, 2),
            }

        # התשובה של המודל נכנסת להיסטוריה כמו שהיא, כולל בלוקי ה-tool_use
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            break

        # מפעילים את *כל* הכלים שהמודל ביקש בתשובה הזאת...
        results = []
        for block in resp.content:
            if block.type == "tool_use":
                tool_calls.append({"name": block.name, "input": block.input})
                results.append(toolbox.run(block))
        # ...ומחזירים את כל התוצאות בהודעה אחת, כמו שה-API דורש
        messages.append({"role": "user", "content": results})
    else:
        log(f"stopped after {MAX_CALLS} calls")

    text = "".join(b.text for b in resp.content if b.type == "text")
    return {
        "text": text,
        "tools": tool_calls,
        "usages": usages,
        "model_calls": len(usages),
        "seconds": round(time.time() - start, 2),
    }
