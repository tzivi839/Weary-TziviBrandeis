"""
tools.py - האחריות: אילו כלים יש ל-Weary, ואיך מפעילים אותם.

שלושה חלקים:
  1. SCHEMAS  - תיאור כל כלי ב-JSON Schema. זה מה שהמודל "רואה":
                שם, מה הכלי עושה, ואילו פרמטרים הוא מקבל.
  2. ToolBox  - dispatch: מקבל בקשה מהמודל (שם + פרמטרים) ומפעיל את הפונקציה
                המתאימה מ-shared/.
  3. שגיאות   - אם כלי נכשל, לא מפילים את התוכנה. מחזירים למודל את השגיאה
                עם is_error=True, והוא יכול לתקן את עצמו ולנסות שוב.

שימי לב: אין כאן לוגיקה של ארון. הכול מגיע מ-shared/, וגם ה-SDK ישתמש בזה.
"""
from shared.preferences import Preferences
from shared.wardrobe import CATEGORIES, OCCASIONS, RAIN_LEVELS, Wardrobe
from shared.weather import get_weather


def log(msg):
    print(f"[tools.py] {msg}")


# ---------- 1. הסכמות ----------
# תיאורים קצרים ובאנגלית: הם נשלחים למודל בכל קריאה, אז כל מילה עולה טוקנים.
SCHEMAS = [
    {
        "name": "add_item",
        "description": "Add a clothing item to the wardrobe. Estimate a sensible temperature range (C).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Item name in the user's language"},
                "category": {"type": "string", "enum": sorted(CATEGORIES),
                             "description": "bottom=skirt, one-piece=dress"},
                "color": {"type": "string"},
                "temp_min": {"type": "integer"},
                "temp_max": {"type": "integer"},
                "occasions": {"type": "array", "items": {"type": "string", "enum": sorted(OCCASIONS)}},
                "rain_ok": {"type": "boolean", "description": "Fine to wear in rain (default true)"},
                "heavy_rain_only": {"type": "boolean", "description": "Only for heavy rain, e.g. boots"},
                "wash_after_wear": {"type": "boolean",
                                    "description": "False for coats and shoes (default true)"},
            },
            "required": ["name", "category", "color", "temp_min", "temp_max", "occasions"],
        },
    },
    {
        "name": "remove_item",
        "description": "Permanently remove an item (torn, given away). Not for laundry.",
        "input_schema": {
            "type": "object",
            "properties": {"item_id": {"type": "string"}},
            "required": ["item_id"],
        },
    },
    {
        "name": "find_clothes",
        "description": "Clean items that fit the weather, day and occasion. Rules (laundry, "
                       "same weekday last week, Shabbat, heavy rain) are applied by the tool.",
        "input_schema": {
            "type": "object",
            "properties": {
                "temp": {"type": "integer", "description": "Expected temperature (C)"},
                "rain": {"type": "string", "enum": sorted(RAIN_LEVELS)},
                "day": {"type": "string", "description": "YYYY-MM-DD, the day to dress for"},
                "occasion": {"type": "string", "enum": sorted(OCCASIONS)},
            },
            "required": ["temp", "rain", "day"],
        },
    },
    {
        "name": "log_outfit",
        "description": "Record what the user wore. Washable items move to laundry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_ids": {"type": "array", "items": {"type": "string"}},
                "day": {"type": "string", "description": "YYYY-MM-DD"},
                "liked": {"type": "boolean"},
            },
            "required": ["item_ids", "day"],
        },
    },
    {
        "name": "laundry_done",
        "description": "Mark items as clean again. Omit item_ids to return all laundry.",
        "input_schema": {
            "type": "object",
            "properties": {"item_ids": {"type": "array", "items": {"type": "string"}}},
        },
    },
    {
        "name": "get_weather",
        "description": "Real weather forecast for a city and day.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name in English"},
                "day": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["city", "day"],
        },
    },
    {
        "name": "save_preference",
        "description": "Remember something about the user. Same topic replaces the old value.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Short key, e.g. city, colors, style"},
                "text": {"type": "string"},
            },
            "required": ["topic", "text"],
        },
    },
    {
        "name": "forget_preference",
        "description": "Delete a saved preference.",
        "input_schema": {
            "type": "object",
            "properties": {"topic": {"type": "string"}},
            "required": ["topic"],
        },
    },
]


# ---------- 2. dispatch ----------
class ToolBox:
    def __init__(self, state_dir, weather_client=None):
        # טוענים את המצב מהדיסק. בסשן 2 זה מה שמביא את הארון מסשן 1.
        self.wardrobe = Wardrobe(state_dir)
        self.prefs = Preferences(state_dir)
        self.weather_client = weather_client
        # מילון: שם הכלי -> הפונקציה שמבצעת אותו
        self.functions = {
            "add_item": self.wardrobe.add_item,
            "remove_item": self.wardrobe.remove_item,
            "find_clothes": self.wardrobe.find_clothes,
            "log_outfit": self.wardrobe.log_outfit,
            "laundry_done": self.wardrobe.laundry_done,
            "get_weather": lambda city, day: get_weather(city, day, self.weather_client),
            "save_preference": self.prefs.save_preference,
            "forget_preference": self.prefs.forget_preference,
        }

    def run(self, block):
        """
        מקבל בלוק tool_use מהמודל ומחזיר בלוק tool_result.
        tool_use_id מחבר בין הבקשה לתשובה, כדי שהמודל יידע איזו תוצאה שייכת לאיזו קריאה.
        """
        log(f"run {block.name}({block.input})")
        try:
            func = self.functions[block.name]
            output = func(**block.input)   # ** פורס את המילון לפרמטרים בשם
            is_error = False
        except KeyError:
            output, is_error = f"unknown tool: {block.name}", True
        except Exception as e:             # ValueError מ-shared, שגיאת רשת, פרמטר חסר...
            output, is_error = f"error: {e}", True

        log(("ERROR " if is_error else "ok ") + output.replace("\n", " / ")[:150])
        return {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
            "is_error": is_error,
        }
