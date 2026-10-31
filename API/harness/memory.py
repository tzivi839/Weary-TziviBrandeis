"""
memory.py - האחריות: מה Weary זוכר עלייך בין סשנים, ואיך שולפים את זה.

איפה הזיכרון נשמר?
  לא בקובץ נפרד: הוא כבר יושב ב-state/, בקבצים ש-shared/ כותב:
    preferences.json - ההעדפות (עיר, צבעים, חוקים אישיים)
    wear_log.json    - יומן הלבישה (מה נלבש ומתי, ואם אהבת)

איך שולפים?
  recall() מחזירה "תקציר זיכרון" קצר, שנכנס להוראות של Weary בכל תור.

למה צריך את זה, אם השיחה הקודמת כבר נטענת מ-history.py?
  1. שיחה ארוכה תסוכם בהמשך (compaction.py), ופרטים עלולים ללכת לאיבוד בסיכום.
     הזיכרון נשמר בנפרד, מסודר לפי נושאים, ולא הולך לאיבוד.
  2. המודל לא צריך לחפש "איפה היא אמרה שהיא גרה?" בתוך עשרות הודעות.
     התשובה מחכה לו בראש ההוראות, בשורה אחת.
  3. זה זול: כמה עשרות טוקנים, במקום לשלוח שוב את כל השיחה הישנה.
"""
from shared.preferences import Preferences
from shared.wardrobe import Wardrobe

RECENT_OUTFITS = 3   # כמה לבושים אחרונים לזכור. יותר מזה לא עוזר להחלטה של היום


def log(msg):
    print(f"[memory.py] {msg}")


class Memory:
    def __init__(self, state_dir):
        self.state_dir = state_dir

    def recall(self):
        # קוראים מחדש מהדיסק בכל פעם, כי הכלים אולי שינו משהו בתור הקודם
        prefs = Preferences(self.state_dir)
        wardrobe = Wardrobe(self.state_dir)
        names = {item["id"]: item["name"] for item in wardrobe.items}

        lines = ["Preferences:", prefs.as_text()]

        recent = wardrobe.log[-RECENT_OUTFITS:]
        if recent:
            lines.append("Recent outfits:")
            for entry in recent:
                # בגד שכבר הוצא מהארון מופיע לפי ה-id שלו
                worn = " + ".join(names.get(i, i) for i in entry["items"])
                liked = {True: " (liked)", False: " (disliked)"}.get(entry.get("liked"), "")
                lines.append(f"- {entry['date']}: {worn}{liked}")

        laundry = sum(1 for item in wardrobe.items if item["status"] == "laundry")
        lines.append(f"Wardrobe: {len(wardrobe.items)} items, {laundry} in laundry")

        text = "\n".join(lines)
        log(f"recalled {len(prefs.prefs)} preferences, {len(recent)} recent outfits")
        return text
