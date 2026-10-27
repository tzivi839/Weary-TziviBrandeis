"""
checks.py - הבדיקות pass/fail של התרחיש. משותף ל-API ול-SDK.

התרגיל מבקש שרוב הבדיקות יהיו על המצב השמור (מה שבאמת נכתב לדיסק),
ולא רק על הטקסט של התשובה. לכן רוב סוגי הבדיקות פה קוראים את state/.

כל בדיקה ב-scenario.json מגדירה:
  when - מתי לבדוק: "after_session_1" (תמונת מצב באמצע) או "end" (בסוף הריצה)
  type - איזה סוג בדיקה (רשימה למטה)

turns הוא רשימה של מה שקרה בכל תור, בפורמט שה-harness כותב:
  {"turn": 5, "text": "...", "tools": [{"name": "get_weather", "input": {...}}]}
"""
from shared.preferences import Preferences
from shared.wardrobe import Wardrobe


def _as_list(x):
    return x if isinstance(x, list) else [x]


def _matching(items, name_contains):
    """כל הבגדים שהשם שלהם מכיל את הטקסט (המודל עשוי לנסח את השם קצת אחרת)."""
    return [i for i in items if name_contains in i["name"]]


def _check(check, items, prefs, turns):
    kind = check["type"]

    if kind == "item_count":
        return len(items) == check["equals"]

    if kind == "item_status":
        for name in _as_list(check["name_contains"]):
            found = _matching(items, name)
            if not found or any(i["status"] != check["status"] for i in found):
                return False
        return True

    if kind == "item_field":
        found = _matching(items, check["name_contains"])
        return bool(found) and all(i.get(check["field"]) == check["equals"] for i in found)

    if kind == "item_absent":
        return not _matching(items, check["name_contains"])

    if kind == "no_status":
        return all(i["status"] != check["status"] for i in items)

    if kind == "preference_contains":
        text = " ".join(prefs.values())
        return any(word in text for word in check["any_of"])

    # שתי הבדיקות האחרונות בודקות מה קרה בתור מסוים
    turn = next((t for t in turns if t["turn"] == check["turn"]), None)
    if turn is None:
        return False

    if kind == "tool_called":
        for call in turn["tools"]:
            if call["name"] != check["tool"]:
                continue
            # כל שדה שהוגדר צריך להכיל לפחות אחת מהאפשרויות
            if all(any(opt in str(call["input"].get(field, "")) for opt in options)
                   for field, options in check.get("input_contains", {}).items()):
                return True
        return False

    if kind == "text_not_contains":
        return check["text"] not in turn["text"]

    raise ValueError(f"unknown check type: {kind}")


def run_checks(checks, when, state_dir, turns):
    """מריץ את כל הבדיקות של שלב מסוים ומחזיר רשימה של {id, passed}."""
    items = Wardrobe(state_dir).items          # קוראים מחדש מהדיסק, לא מהזיכרון של התוכנה
    prefs = Preferences(state_dir).prefs
    results = []
    for check in checks:
        if check["when"] == when:
            results.append({"id": check["id"], "passed": _check(check, items, prefs, turns)})
    return results
