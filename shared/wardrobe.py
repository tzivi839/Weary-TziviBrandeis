"""
wardrobe.py - הארון של Weary: הבגדים, יומן הלבישה, וחוקי הסינון.

זה "קוד הדומיין". אין כאן שום AI - רק Python רגיל.
גם גרסת ה-API וגם גרסת ה-SDK משתמשות בדיוק בקוד הזה.

החלטה חשובה (טובה לדוח): חוקים "קשיחים" מקודדים כאן ולא משאירים למודל לנחש:
  - מזג אוויר (טמפרטורה, גשם, גשם עז)
  - כביסה
  - לא אותו בגד באותו יום בשבוע שעבר
  - שבת = רק בגדים אלגנטיים (ולכן גם לא מגפיים)
טעם אישי (למשל "לא ירוק עם כתום") נשמר כהעדפה בזיכרון, והמודל מתחשב בו.

עוד החלטה: הפלט של הפונקציות קצר ובאנגלית (חוץ משמות הבגדים).
טקסט באנגלית עולה פחות טוקנים מעברית, וזה חלק מ-token optimization.
"""
from datetime import date, timedelta

from shared import store

# bottom = חצאית, one-piece = שמלה
CATEGORIES = {"top", "bottom", "one-piece", "outer", "shoes"}
OCCASIONS = {"casual", "work", "event", "shabbat"}
RAIN_LEVELS = {"dry", "rain", "heavy"}   # כמו שהכלי של מזג האוויר מחזיר
SATURDAY = 5                              # ב-Python: שני=0 ... שבת=5


class Wardrobe:
    def __init__(self, state_dir=store.DEFAULT_STATE_DIR):
        self.state_dir = state_dir
        # טוענים מהדיסק. אם זו הפעם הראשונה, מתחילים עם רשימות ריקות.
        self.items = store.load("wardrobe", [], state_dir)
        self.log = store.load("wear_log", [], state_dir)

    def _save(self):
        store.save("wardrobe", self.items, self.state_dir)
        store.save("wear_log", self.log, self.state_dir)

    def _get(self, item_id):
        """מחזיר בגד לפי id, או זורק שגיאה ברורה אם הוא לא קיים."""
        for item in self.items:
            if item["id"] == item_id:
                return item
        # ValueError יהפוך אחר כך ל-is_error שחוזר למודל, והמודל יוכל לתקן את עצמו
        raise ValueError(f"no item with id '{item_id}'")

    # ---------- כלי: הוספת בגד ----------
    def add_item(self, name, category, color, temp_min, temp_max, occasions,
                 rain_ok=True, heavy_rain_only=False, wash_after_wear=True):
        # בדיקות קלט: עדיף לתפוס טעות כאן מאשר לשמור נתונים שבורים
        if category not in CATEGORIES:
            raise ValueError(f"category must be one of {sorted(CATEGORIES)}")
        bad = set(occasions) - OCCASIONS
        if bad:
            raise ValueError(f"unknown occasions {sorted(bad)}; allowed: {sorted(OCCASIONS)}")
        if temp_min > temp_max:
            raise ValueError("temp_min must be <= temp_max")

        # id בפורמט top-001, top-002... המספר הבא בתוך הקטגוריה
        numbers = [int(i["id"].split("-")[-1]) for i in self.items if i["category"] == category]
        item_id = f"{category}-{max(numbers, default=0) + 1:03d}"

        self.items.append({
            "id": item_id,
            "name": name,
            "category": category,
            "color": color,
            "temp_min": temp_min,
            "temp_max": temp_max,
            "occasions": list(occasions),
            "rain_ok": rain_ok,
            "heavy_rain_only": heavy_rain_only,   # למשל מגפיים
            "wash_after_wear": wash_after_wear,
            "status": "clean",
        })
        self._save()
        return f"added {item_id}"

    # ---------- כלי: הוצאת בגד מהארון לתמיד (נקרע, נמסר...) ----------
    def remove_item(self, item_id):
        item = self._get(item_id)
        self.items.remove(item)
        self._save()
        return f"removed {item_id}"

    # ---------- כלי: מציאת בגדים מתאימים (כאן כל החוקים) ----------
    def find_clothes(self, temp, rain, day, occasion=None):
        """
        day = היום שבשבילו מתלבשים (לא בהכרח היום, למשל "מה ללבוש מחר בשבת?").
        מחזיר רק בגדים שעוברים את כל החוקים:
          1. נקי (לא בכביסה)
          2. הטמפרטורה בטווח של הבגד
          3. יורד גשם -> רק בגדים שמתאימים לגשם
          4. בגד "רק לגשם עז" (מגפיים) -> רק כשיש גשם עז
          5. לא נלבש באותו יום בשבוע שעבר
          6. שבת -> רק בגדים שמתאימים לשבת. אחרת לפי האירוע, אם צוין
        """
        if rain not in RAIN_LEVELS:
            raise ValueError(f"rain must be one of {sorted(RAIN_LEVELS)}")
        day = date.fromisoformat(day)
        if day.weekday() == SATURDAY:
            occasion = "shabbat"   # בשבת זה תמיד שבת, גם אם המודל לא ביקש

        last_week = (day - timedelta(days=7)).isoformat()
        worn_last_week = {i for entry in self.log if entry["date"] == last_week
                          for i in entry["items"]}
        # שילובים שלא אהבת: כל אחד הוא קבוצה של בגדים שנלבשו יחד.
        # לא פוסלים את הבגדים עצמם, רק את השילוב.
        disliked_combos = [set(entry["items"]) for entry in self.log
                           if entry.get("liked") is False]

        lines = []
        ids = set()
        for item in self.items:
            if item["status"] != "clean":
                continue
            if not item["temp_min"] <= temp <= item["temp_max"]:
                continue
            if rain != "dry" and not item["rain_ok"]:
                continue
            if item.get("heavy_rain_only") and rain != "heavy":
                continue
            if item["id"] in worn_last_week:
                continue
            if occasion and occasion not in item["occasions"]:
                continue
            # שורה קומפקטית אחת לבגד, במקום כל ה-JSON שלו
            lines.append(f"{item['id']}|{item['name']}|{item['color']}")
            ids.add(item["id"])

        if not lines:
            return "no matching clothes"

        # אזהרה רק על שילובים שכל הבגדים שלהם באמת ברשימה.
        # שילוב שאחד מהבגדים שלו בכביסה לא רלוונטי היום, אז לא מבזבזים עליו טוקנים.
        for combo in disliked_combos:
            if combo <= ids:   # <= בין sets פירושו "כל האיברים נמצאים גם ב-"
                lines.append("avoid together: " + "+".join(sorted(combo)))
        return "\n".join(lines)

    # ---------- כלי: רישום מה נלבש ----------
    def log_outfit(self, item_ids, day, liked=None):
        for item_id in item_ids:
            if self._get(item_id)["status"] != "clean":
                raise ValueError(f"{item_id} is in the laundry")

        self.log.append({"date": day, "items": list(item_ids), "liked": liked})

        # מה שמסומן wash_after_wear עובר לכביסה. מעיל ונעליים - לא.
        to_laundry = []
        for item_id in item_ids:
            item = self._get(item_id)
            if item["wash_after_wear"]:
                item["status"] = "laundry"
                to_laundry.append(item_id)

        self._save()
        return f"logged {day}; to laundry: {', '.join(to_laundry) or 'none'}"

    # ---------- כלי: הכביסה מוכנה ----------
    def laundry_done(self, item_ids=None):
        """מחזיר בגדים מהכביסה. בלי item_ids - את כל מה שבכביסה."""
        returned = []
        for item in self.items:
            if item["status"] == "laundry" and (item_ids is None or item["id"] in item_ids):
                item["status"] = "clean"
                returned.append(item["id"])
        self._save()
        return f"clean again: {', '.join(returned) or 'none'}"
