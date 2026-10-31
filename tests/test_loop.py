"""
test_loop.py - בדיקה offline של הלולאה, בלי מפתח ובלי לשלם.

FakeClient מתחזה ל-anthropic.Anthropic: במקום לפנות לשרת, הוא מחזיר
תשובות שהכנו מראש, אחת בכל קריאה. ככה בודקים שהלולאה, ה-dispatch והשגיאות עובדים.
"""
from types import SimpleNamespace as NS

from API.agent import Weary
from API.harness import loop, tools

USAGE = NS(input_tokens=100, output_tokens=20,
           cache_read_input_tokens=0, cache_creation_input_tokens=0)


def tool_use(id, name, input):
    return NS(type="tool_use", id=id, name=name, input=input)


def text(t):
    return NS(type="text", text=t)


def text_of(message):
    """הטקסט של הודעה, בין אם היא מחרוזת ובין אם רשימת בלוקים (כמו אחרי caching.py)."""
    content = message["content"]
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict))


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.sent = []                       # מה ה-harness שלח בכל קריאה
        self.messages = self                 # כדי ש-client.messages.create יעבוד

    def create(self, **kwargs):
        self.sent.append(kwargs)
        content, stop = self.responses.pop(0)
        return NS(content=content, stop_reason=stop, usage=USAGE)


def test_loop_runs_tools_until_text(tmp_path):
    client = FakeClient([
        # קריאה 1: המודל מבקש שני כלים באותה תשובה
        ([tool_use("t1", "save_preference", {"topic": "city", "text": "Jerusalem"}),
          tool_use("t2", "add_item", {"name": "חצאית שחורה", "category": "bottom",
                                      "color": "black", "temp_min": 5, "temp_max": 30,
                                      "occasions": ["casual"]})], "tool_use"),
        # קריאה 2: המודל עונה בטקסט, סוף התור
        ([text("שמרתי!")], "end_turn"),
    ])
    weary = Weary(state_dir=tmp_path, day="2026-10-29", client=client)
    result = weary.ask("אני גרה בירושלים ויש לי חצאית שחורה")

    assert result["text"] == "שמרתי!"
    assert result["model_calls"] == 2
    assert [t["name"] for t in result["tools"]] == ["save_preference", "add_item"]

    # שתי תוצאות הכלים חזרו בהודעה *אחת*
    tool_results = weary.messages[2]
    assert tool_results["role"] == "user"
    assert [r["tool_use_id"] for r in tool_results["content"]] == ["t1", "t2"]

    # והמצב באמת נשמר לדיסק
    assert tools.ToolBox(tmp_path).wardrobe.items[0]["id"] == "bottom-001"


def test_tool_error_goes_back_to_model(tmp_path):
    client = FakeClient([
        ([tool_use("t1", "remove_item", {"item_id": "top-999"})], "tool_use"),
        ([text("לא מצאתי את הבגד")], "end_turn"),
    ])
    weary = Weary(state_dir=tmp_path, day="2026-10-29", client=client)
    weary.ask("תמחק את top-999")

    result = weary.messages[2]["content"][0]
    assert result["is_error"] is True                  # השגיאה לא הפילה את התוכנה
    assert "top-999" in result["content"]              # והמודל רואה מה השתבש


def test_loop_stops_after_max_calls(tmp_path):
    endless = [([tool_use(f"t{i}", "laundry_done", {})], "tool_use")
               for i in range(loop.MAX_CALLS)]
    weary = Weary(state_dir=tmp_path, day="2026-10-29", client=FakeClient(endless))
    assert weary.ask("...")["model_calls"] == loop.MAX_CALLS


def test_cut_off_answer_is_not_saved(tmp_path):
    # המודל נקטע באמצע בקשה לכלי: אסור שבלוק חתוך ייכנס להיסטוריה
    client = FakeClient([([tool_use("t1", "add_item", {"name": "חצא"})], "max_tokens")])
    weary = Weary(state_dir=tmp_path, day="2026-10-29", client=client)
    result = weary.ask("הרבה בגדים...")
    assert "נקטעה" in result["text"]
    assert [m["role"] for m in weary.messages] == ["user"]   # רק ההודעה שלך נשארה
