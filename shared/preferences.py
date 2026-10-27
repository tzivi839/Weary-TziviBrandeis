"""
preferences.py - מה Weary יודע עלייך: עיר, טעם, חוקים אישיים.

כל העדפה נשמרת תחת "נושא" (topic), למשל "city" או "colors".
למה לפי נושא? כי ככה בקשה סותרת מטופלת נכון:
אם בסשן 2 נשמרת העדפה חדשה על אותו נושא, היא מחליפה את הישנה,
במקום ששתי העדפות סותרות יישארו בזיכרון ויבלבלו את המודל.
"""
from shared import store


class Preferences:
    def __init__(self, state_dir=store.DEFAULT_STATE_DIR):
        self.state_dir = state_dir
        self.prefs = store.load("preferences", {}, state_dir)   # {topic: text}

    def _save(self):
        store.save("preferences", self.prefs, self.state_dir)

    # ---------- כלי: שמירת העדפה ----------
    def save_preference(self, topic, text):
        old = self.prefs.get(topic)
        self.prefs[topic] = text
        self._save()
        # מחזירים גם מה היה קודם, כדי שהמודל יידע שהוא דרס משהו
        return f"saved {topic}" + (f" (replaced: {old})" if old else "")

    # ---------- כלי: מחיקת העדפה ----------
    def forget_preference(self, topic):
        if topic not in self.prefs:
            raise ValueError(f"no preference '{topic}'; known: {sorted(self.prefs)}")
        del self.prefs[topic]
        self._save()
        return f"forgot {topic}"

    def as_text(self):
        """ההעדפות כטקסט קצר, להכנסה לקונטקסט של כל תור (ישמש את context.py)."""
        if not self.prefs:
            return "no preferences yet"
        return "\n".join(f"- {topic}: {text}" for topic, text in self.prefs.items())
