"""
agent.py - Weary עצמו: מחבר את כל חלקי ה-harness לסוכן אחד.

בשלב הזה הוא מחבר את tools.py, loop.py, tokens.py, history.py ו-memory.py.
בשלבים הבאים יתחברו לכאן גם context, caching ו-compaction.

הרצה לשיחה חופשית עם WearMe (מתיקיית הפרויקט):
    python API/agent.py            ממשיך את השיחה והארון מהפעם הקודמת
    python API/agent.py --reset    מתחיל מאפס: מוחק את כל התיקייה state/
"""
import truststore
truststore.inject_into_ssl()
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
from harness import history, loop, memory, tokens, tools  # noqa: E402

MODEL = "claude-opus-5-5"
EFFORT = "medium"   # אותו מודל ואותו effort גם בגרסת ה-SDK, כמו שהתרגיל דורש

SYSTEM = """You are Weary, the wardrobe assistant behind the WearMe app.
Today is {day} ({weekday}).
Answer in Hebrew, short and warm.
Always use tools: get_weather before suggesting clothes, then find_clothes.
Suggest one complete outfit (top + skirt, or a dress, plus shoes and outer layer if needed).
Never invent items that are not in the wardrobe.
Save anything the user tells you about themselves with save_preference.
Use what you remember (below) without asking again, e.g. the user's city.

What you remember about the user:
{memory}"""


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

    def system_prompt(self):
        weekday = date.fromisoformat(self.day).strftime("%A")
        # הזיכרון נשלף מחדש בכל תור, כדי שיכלול גם מה שנשמר בתור הקודם
        return SYSTEM.format(day=self.day, weekday=weekday, memory=self.memory.recall())

    def ask(self, text):
        self.messages.append({"role": "user", "content": text})
        result = loop.run_turn(
            self.client, self.messages, self.toolbox,
            model=MODEL, effort=EFFORT,
            system=self.system_prompt(), tools=tools.SCHEMAS,
        )
        self.history.save_new(self.messages)
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
