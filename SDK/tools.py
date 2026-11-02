"""
tools.py (SDK) - אותם 8 כלים, עטופים ב-@tool של ה-SDK.

מה זה מחליף מה-API:
  tools.py ב-API עשה שלושה דברים: סכמות, dispatch, ושגיאות.
  כאן:
    - סכמות:  הפרמטר השלישי של @tool. לכלים פשוטים מספיק {"item_id": str}.
    - dispatch: ה-SDK מוצא לבד איזה כלי להפעיל לפי השם.
    - שגיאות: אם הפונקציה זורקת שגיאה, ה-SDK מחזיר אותה למודל כ-is_error בעצמו.
  הלוגיקה עצמה (הארון, החוקים, מזג האוויר) מגיעה מ-shared/, בדיוק כמו ב-API.

create_sdk_mcp_server אורז את הכלים ל"שרת MCP" שרץ בתוך התוכנה שלנו.
Claude Code רואה אותם בשמות כמו mcp__weary__add_item.
"""
from claude_agent_sdk import create_sdk_mcp_server, tool

from shared.preferences import Preferences
from shared.wardrobe import CATEGORIES, OCCASIONS, RAIN_LEVELS, Wardrobe
from shared.weather import get_weather

SERVER = "weary"


def log(msg):
    print(f"[SDK/tools.py] {msg}")


def _ok(text):
    """הפורמט שה-SDK מצפה לו מכלי: רשימת בלוקי תוכן."""
    log("ok " + text.replace("\n", " / ")[:150])
    return {"content": [{"type": "text", "text": text}]}


def build_server(state_dir, weather_client=None):
    """בונה את שרת הכלים. מחזיר (הגדרת השרת, רשימת הכלים)."""
    wardrobe = Wardrobe(state_dir)
    prefs = Preferences(state_dir)

    @tool("add_item", "Add a clothing item. Estimate a sensible temperature range (C).", {  # replaces: tools
        "type": "object",  # replaces: tools
        "properties": {  # replaces: tools
            "name": {"type": "string"},  # replaces: tools
            "category": {"type": "string", "enum": sorted(CATEGORIES)},  # replaces: tools
            "color": {"type": "string"},  # replaces: tools
            "temp_min": {"type": "integer"}, "temp_max": {"type": "integer"},  # replaces: tools
            "occasions": {"type": "array", "items": {"type": "string", "enum": sorted(OCCASIONS)}},  # replaces: tools
            "rain_ok": {"type": "boolean"},  # replaces: tools
            "heavy_rain_only": {"type": "boolean", "description": "e.g. boots"},  # replaces: tools
            "wash_after_wear": {"type": "boolean", "description": "False for coats, shoes"},  # replaces: tools
        },  # replaces: tools
        "required": ["name", "category", "color", "temp_min", "temp_max", "occasions"],  # replaces: tools
    })  # replaces: tools
    async def add_item(args):  # replaces: tools
        return _ok(wardrobe.add_item(**args))  # replaces: tools

    @tool("remove_item", "Permanently remove an item (torn, given away). Not for laundry.",  # replaces: tools
          {"item_id": str})  # replaces: tools
    async def remove_item(args):  # replaces: tools
        return _ok(wardrobe.remove_item(args["item_id"]))  # replaces: tools

    @tool("find_clothes", "Clean items that fit the weather, day and occasion. "  # replaces: tools
          "Rules (laundry, same weekday last week, Shabbat, heavy rain) are applied by the tool.", {  # replaces: tools
        "type": "object",  # replaces: tools
        "properties": {  # replaces: tools
            "temp": {"type": "integer"},  # replaces: tools
            "rain": {"type": "string", "enum": sorted(RAIN_LEVELS)},  # replaces: tools
            "day": {"type": "string", "description": "YYYY-MM-DD, the day to dress for"},  # replaces: tools
            "occasion": {"type": "string", "enum": sorted(OCCASIONS)},  # replaces: tools
        },  # replaces: tools
        "required": ["temp", "rain", "day"],  # replaces: tools
    })  # replaces: tools
    async def find_clothes(args):  # replaces: tools
        return _ok(wardrobe.find_clothes(**args))  # replaces: tools

    @tool("log_outfit", "Record what the user wore. Washable items move to laundry.", {  # replaces: tools
        "type": "object",  # replaces: tools
        "properties": {  # replaces: tools
            "item_ids": {"type": "array", "items": {"type": "string"}},  # replaces: tools
            "day": {"type": "string"}, "liked": {"type": "boolean"},  # replaces: tools
        },  # replaces: tools
        "required": ["item_ids", "day"],  # replaces: tools
    })  # replaces: tools
    async def log_outfit(args):  # replaces: tools
        return _ok(wardrobe.log_outfit(**args))  # replaces: tools

    @tool("laundry_done", "Mark items clean again. Omit item_ids to return all laundry.", {  # replaces: tools
        "type": "object",  # replaces: tools
        "properties": {"item_ids": {"type": "array", "items": {"type": "string"}}},  # replaces: tools
    })  # replaces: tools
    async def laundry_done(args):  # replaces: tools
        return _ok(wardrobe.laundry_done(args.get("item_ids")))  # replaces: tools

    @tool("get_weather", "Real weather forecast. City in English, day YYYY-MM-DD.",  # replaces: tools
          {"city": str, "day": str})  # replaces: tools
    async def weather(args):  # replaces: tools
        return _ok(get_weather(args["city"], args["day"], weather_client))  # replaces: tools

    @tool("save_preference", "Remember something about the user. Same topic replaces the old value.",  # replaces: tools
          {"topic": str, "text": str})  # replaces: tools
    async def save_preference(args):  # replaces: tools
        return _ok(prefs.save_preference(args["topic"], args["text"]))  # replaces: tools

    @tool("forget_preference", "Delete a saved preference.", {"topic": str})  # replaces: tools
    async def forget_preference(args):  # replaces: tools
        return _ok(prefs.forget_preference(args["topic"]))  # replaces: tools

    all_tools = [add_item, remove_item, find_clothes, log_outfit, laundry_done,  # replaces: tools
                 weather, save_preference, forget_preference]  # replaces: tools
    return create_sdk_mcp_server(name=SERVER, tools=all_tools), all_tools  # replaces: tools
