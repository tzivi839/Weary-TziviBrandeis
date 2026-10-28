"""
agent.py - Weary עצמו: מחבר את כל חלקי ה-harness לסוכן אחד.

בשלב הזה הוא מחבר רק את tools.py ו-loop.py.
בשלבים הבאים יתחברו לכאן גם tokens, history, memory, context, caching ו-compaction.

הרצה לשיחה חופשית עם WearMe (מתיקיית הפרויקט):
    python API/agent.py
"""
import sys
from datetime import date
from pathlib import Path

# כשמריצים "python API/agent.py", Python מחפש imports רק בתוך API/.
# השורה הזאת מוסיפה גם את תיקיית הפרויקט, כדי ש-"from shared..." יעבוד.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "API"))

import anthropic                          # noqa: E402  (import אחרי שינוי ה-path, בכוונה)
from harness import loop, tools          # noqa: E402

MODEL = "claude-opus-5-5"
EFFORT = "medium"   # אותו מודל ואותו effort גם בגרסת ה-SDK, כמו שהתרגיל דורש

SYSTEM = """You are Weary, the wardrobe assistant behind the WearMe app.
Today is {day} ({weekday}).
Answer in Hebrew, short and warm.
Always use tools: get_weather before suggesting clothes, then find_clothes.
Suggest one complete outfit (top + skirt, or a dress, plus shoes and outer layer if needed).
Never invent items that are not in the wardrobe.
Save anything the user tells you about themselves with save_preference."""


class Weary:
    def __init__(self, state_dir=ROOT / "state", day=None, client=None, weather_client=None):
        self.day = day or date.today().isoformat()
        # anthropic.Anthropic() קורא את המפתח לבד ממשתנה הסביבה ANTHROPIC_API_KEY.
        # המפתח לעולם לא כתוב בקוד.
        self.client = client or anthropic.Anthropic()
        self.toolbox = tools.ToolBox(state_dir, weather_client)
        self.messages = []   # השיחה. בשלב 7 (history.py) היא תישמר לדיסק

    def system_prompt(self):
        weekday = date.fromisoformat(self.day).strftime("%A")
        return SYSTEM.format(day=self.day, weekday=weekday)

    def ask(self, text):
        self.messages.append({"role": "user", "content": text})
        return loop.run_turn(
            self.client, self.messages, self.toolbox,
            model=MODEL, effort=EFFORT,
            system=self.system_prompt(), tools=tools.SCHEMAS,
        )


if __name__ == "__main__":
    weary = Weary()
    print(f"👗 WearMe ({weary.day}). כתבי 'יציאה' כדי לסיים.\n")
    while True:
        text = input("את: ").strip()
        if text in ("יציאה", "exit", "quit"):
            break
        if text:
            result = weary.ask(text)
            print(f"\nWearMe: {result['text']}\n")
