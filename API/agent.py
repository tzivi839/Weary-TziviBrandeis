"""
agent.py - Weary עצמו: מחבר את כל חלקי ה-harness לסוכן אחד.

הוא מחבר את כל 8 הקבצים של harness/: tools, loop, tokens, history, memory, context,
caching ו-compaction.

הרצה לשיחה חופשית עם WearMe (מתיקיית הפרויקט):
    python API/agent.py            ממשיך את השיחה והארון מהפעם הקודמת
    python API/agent.py --reset    מתחיל מאפס: מוחק את כל התיקייה state/
"""
import shutil
import sys
from datetime import date
from pathlib import Path

# כשמריצים "python API/agent.py", Python מחפש imports רק בתוך API/.
# השורה הזאת מוסיפה גם את תיקיית הפרויקט, כדי ש-"from shared..." יעבוד.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "API"))

import anthropic                          # noqa: E402  (import אחרי שינוי ה-path, בכוונה)
from harness import (caching, compaction, context, history, loop,  # noqa: E402
                     memory, tokens, tools)

MODEL = "claude-opus-5-5"
EFFORT = "medium"   # אותו מודל ואותו effort גם בגרסת ה-SDK, כמו שהתרגיל דורש

# ההוראות (system prompt) עברו ל-context.py, שמחליט מה נשלח בכל קריאה


class Weary:
    def __init__(self, state_dir=ROOT / "state", day=None, client=None, weather_client=None):
        self.day = day or date.today().isoformat()
        # anthropic.Anthropic() קורא את המפתח לבד ממשתנה הסביבה ANTHROPIC_API_KEY.
        # המפתח לעולם לא כתוב בקוד.
        self.client = client or anthropic.Anthropic()
        self.toolbox = tools.ToolBox(state_dir, weather_client)
        # השיחה נטענת מהדיסק. בסשן הראשון זו רשימה ריקה
        self.history = history.History(state_dir)
        self.messages = self.history.load()
        self.meter = tokens.Meter()
        self.memory = memory.Memory(state_dir)

    def ask(self, text):
        self.messages.append({"role": "user", "content": text})
        # הזיכרון נשלף פעם אחת בתחילת כל תור, כדי שיכלול גם מה שנשמר בתור הקודם
        weekday = date.fromisoformat(self.day).strftime("%A")
        day_line = f"Today is {self.day} ({weekday})."
        memory_text = self.memory.recall()
        result = loop.run_turn(
            self.client, self.messages, self.toolbox,
            model=MODEL, effort=EFFORT, tools=tools.SCHEMAS,
            # לפני כל קריאה: context.py בוחר מה לשלוח, ו-caching.py מסמן מה לשמור ב-cache
            build=lambda msgs: caching.apply(*context.build(
                msgs, day_line, memory_text, self.history.summary, self.history.summary_upto)),
        )
        self.history.save_new(self.messages)

        # אחרי התור: אם השיחה ארוכה מדי, מסכמים אותה (קריאה נוספת למודל)
        summary_usage = compaction.maybe_compact(
            self.client, self.messages, self.history, result["usages"], model=MODEL)
        result["compacted"] = summary_usage is not None
        if summary_usage:
            result["usages"].append(summary_usage)
            result["model_calls"] += 1

        result["tokens"] = self.meter.record(result["usages"])
        return result


if __name__ == "__main__":
    if "--reset" in sys.argv:
        shutil.rmtree(ROOT / "state", ignore_errors=True)
        print("התחלה מאפס: הארון, ההעדפות וההיסטוריה נמחקו.")
    weary = Weary()
    print(f"👗 WearMe ({weary.day}). כתבי 'יציאה' כדי לסיים.\n")
    while True:
        text = input("את: ").strip()
        if text in ("יציאה", "exit", "quit"):
            t = weary.meter.total()
            print(f"סה\"כ בשיחה: {t['input'] + t['cache_read'] + t['cache_write']} טוקני קלט, "
                  f"{t['output']} טוקני פלט, ${t['cost_usd']:.4f}")
            break
        if text:
            result = weary.ask(text)
            print(f"\nWearMe: {result['text']}\n")
