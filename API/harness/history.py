"""
history.py - האחריות: לשמור את השיחה לדיסק, כדי שסשן הבא ימשיך מאותה נקודה.

הקובץ הוא state/history.jsonl. JSONL = שורה אחת של JSON לכל הודעה.

למה append-only (רק מוסיפים, אף פעם לא משנים או מוחקים)?
  1. בטוח: אם התוכנה קורסת באמצע, כל מה שנכתב קודם נשאר שלם.
  2. מהיר: מוסיפים שורה לסוף הקובץ, בלי לכתוב מחדש את כל השיחה.
  3. היסטוריה אמיתית: אפשר תמיד לראות בדיוק מה קרה ומתי.
כשנגיע ל-compaction.py, גם הסיכום יתווסף כשורה חדשה. שום דבר לא יימחק.
"""
import json
from pathlib import Path

FILE_NAME = "history.jsonl"


def log(msg):
    print(f"[history.py] {msg}")


def to_jsonable(x):
    """
    התשובות של Claude מגיעות כאובייקטים של ספריית anthropic, לא כמילונים רגילים.
    הפונקציה הופכת אותם (וכל מה שבתוכם) למשהו ש-JSON יודע לשמור.
    """
    if hasattr(x, "model_dump"):                  # אובייקט של anthropic
        return x.model_dump(mode="json", exclude_none=True)
    if isinstance(x, dict):
        return {k: to_jsonable(v) for k, v in x.items()}
    if isinstance(x, list):
        return [to_jsonable(v) for v in x]
    if hasattr(x, "__dict__"):                    # אובייקט פשוט (למשל בבדיקות)
        return {k: to_jsonable(v) for k, v in vars(x).items()}
    return x                                      # טקסט, מספר, True/False


class History:
    def __init__(self, state_dir):
        self.path = Path(state_dir) / FILE_NAME
        self.saved = 0   # כמה הודעות כבר נכתבו לדיסק

    def load(self):
        """קורא את כל השיחה מהדיסק. אם אין קובץ (סשן ראשון) - שיחה ריקה."""
        if not self.path.exists():
            log("no history yet - starting a new conversation")
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        messages = [json.loads(line)["message"] for line in lines if line.strip()]
        self.saved = len(messages)
        log(f"loaded {len(messages)} messages from {self.path.name}")
        return messages

    def save_new(self, messages):
        """מוסיף לסוף הקובץ רק את ההודעות שעוד לא נשמרו."""
        new = messages[self.saved:]
        if not new:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # mode "a" = append: כותבים לסוף הקובץ, בלי למחוק את מה שכבר יש בו
        with self.path.open("a", encoding="utf-8") as f:
            for message in new:
                f.write(json.dumps({"message": to_jsonable(message)}, ensure_ascii=False) + "\n")
        self.saved = len(messages)
        log(f"appended {len(new)} messages (total {self.saved})")
