"""
agent.py (SDK) - Weary על Claude Agent SDK.

ב-API כתבנו 8 קבצים של harness. כאן Claude Code מריץ את ה-harness, ואנחנו רק מגדירים אותו.
כל שורה שמחליפה קובץ מה-API מסומנת "# replaces: <שם>".

  loop        -> client.query() + receive_response()
  tools       -> SDK/tools.py (@tool + create_sdk_mcp_server)
  history     -> resume=session_id (Claude Code שומר את השיחה בעצמו)
  memory      -> CLAUDE.md בתיקיית הפרויקט, עם setting_sources=["project"]
  context     -> שורת תאריך בכל שאלה. כל השאר Claude Code מוסיף לבד, והמודל שולף בכלים
  compaction  -> אוטומטי ב-Claude Code
  caching     -> אוטומטי ב-Claude Code
  tokens      -> ResultMessage.usage ו-total_cost_usd

הרשאות: ה-SDK רץ על ה-login שלך ב-Claude Code. אם ANTHROPIC_API_KEY מוגדר בטרמינל,
החיוב עובר למפתח, ולכן Weary מסרב לרוץ במצב כזה.
"""
import truststore
truststore.inject_into_ssl()
import os
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions,  # noqa: E402
                              ClaudeSDKClient, ResultMessage, ToolUseBlock)

from SDK.tools import SERVER, build_server  # noqa: E402
from shared import store                    # noqa: E402
from shared.preferences import Preferences  # noqa: E402
from shared.wardrobe import Wardrobe        # noqa: E402

MODEL = "claude-opus-5-5"   # אותו מודל ואותו effort כמו ב-API
EFFORT = "medium"

SYSTEM = """You are Weary, the wardrobe assistant behind the WearMe app.
Answer in Hebrew, short and warm.
Today's date is in <context> in the user's message. What you remember about the user is in CLAUDE.md.
Always use tools: get_weather before suggesting clothes, then find_clothes.
Suggest one complete outfit (top + skirt, or a dress, plus shoes and outer layer if needed).
Never invent items that are not in the wardrobe.
Save anything the user tells you about themselves with save_preference.
Use what you remember without asking again, e.g. the user's city."""


def log(msg):
    print(f"[SDK/agent.py] {msg}")


def check_no_api_key():
    if os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is set, so the SDK would bill the API key instead of your "
                 "Claude Code login. Open a new terminal (or run: Remove-Item Env:ANTHROPIC_API_KEY).")


class Weary:
    def __init__(self, state_dir, day=None, client_factory=ClaudeSDKClient, weather_client=None):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.day = day or date.today().isoformat()
        self.client_factory = client_factory
        self.server, tools = build_server(state_dir, weather_client)  # replaces: tools
        self.tool_names = [f"mcp__{SERVER}__{t.name}" for t in tools]  # replaces: tools
        self.session_id = store.load("sdk_session", {}, state_dir).get("id")  # replaces: history
        self.write_memory()

    def write_memory(self):
        """בתחילת כל סשן: מה Weary יודע עלייך נכתב ל-CLAUDE.md, ש-Claude Code טוען לבד."""
        prefs = Preferences(self.state_dir).as_text()  # replaces: memory
        items = Wardrobe(self.state_dir).items  # replaces: memory
        laundry = sum(i["status"] == "laundry" for i in items)  # replaces: memory
        memory = f"# What Weary remembers\n{prefs}\nWardrobe: {len(items)} items, {laundry} in laundry\n"  # replaces: memory
        (self.state_dir / "CLAUDE.md").write_text(memory, encoding="utf-8")  # replaces: memory
        log("wrote CLAUDE.md (memory for this session)")

    def options(self):
        return ClaudeAgentOptions(
            model=MODEL,
            effort=EFFORT,
            system_prompt=SYSTEM,                  # system prompt משלנו, לא של Claude Code
            mcp_servers={SERVER: self.server},  # replaces: tools
            tools=[],                              # רשימת כלים מצומצמת: בלי Bash, Read וכו'
            allowed_tools=self.tool_names,         # רק הכלים שלנו, בלי לבקש אישור
            permission_mode="dontAsk",             # כל כלי אחר נחסם
            strict_mcp_config=True,                # רק שרת ה-MCP שלנו, בלי הגדרות מהמחשב
            cwd=str(self.state_dir),  # replaces: memory
            setting_sources=["project"],  # replaces: memory
            resume=self.session_id,  # replaces: history
            max_turns=10,  # replaces: loop
            # compaction: אין שורה. Claude Code מסכם לבד כשהשיחה מתקרבת לגבול החלון.  # replaces: compaction
            # caching: אין שורה. Claude Code מסמן נקודות cache לבד.  # replaces: caching
        )

    async def ask(self, text):
        start = time.time()
        weekday = date.fromisoformat(self.day).strftime("%A")
        prompt = f"<context>Today is {self.day} ({weekday}).</context>\n\n{text}"  # replaces: context
        reply, tools_used, result = "", [], None

        # client חדש לכל שאלה, שממשיך את אותה שיחה דרך resume.
        # ככה כל ResultMessage מתאר בדיוק תור אחד, והמדידה נקייה.
        async with self.client_factory(options=self.options()) as client:
            await client.query(prompt)  # replaces: loop
            async for message in client.receive_response():  # replaces: loop
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, ToolUseBlock):
                            name = block.name.replace(f"mcp__{SERVER}__", "")
                            log(f"model called {name}({block.input})")
                            tools_used.append({"name": name, "input": block.input})
                elif isinstance(message, ResultMessage):
                    result = message

        self.session_id = result.session_id  # replaces: history
        store.save("sdk_session", {"id": self.session_id}, self.state_dir)  # replaces: history
        usage = result.usage or {}  # replaces: tokens
        tokens = {  # replaces: tokens
            "input": usage.get("input_tokens", 0),  # replaces: tokens
            "cache_read": usage.get("cache_read_input_tokens", 0),  # replaces: tokens
            "cache_write": usage.get("cache_creation_input_tokens", 0),  # replaces: tokens
            "output": usage.get("output_tokens", 0),  # replaces: tokens
        }  # replaces: tokens
        cost = round(result.total_cost_usd or 0, 5)  # replaces: tokens
        log(f"turn: {tokens} calls={result.num_turns} cost=${cost:.4f}")
        reply = result.result or ""
        return {
            "text": reply,
            "tools": tools_used,
            "model_calls": result.num_turns,
            "tokens": tokens,
            "cost_usd": cost,
            "seconds": round(time.time() - start, 2),
        }


if __name__ == "__main__":
    import asyncio

    async def chat():
        check_no_api_key()
        weary = Weary(ROOT / "state" / "sdk-chat")
        print(f"👗 WearMe (SDK, {weary.day}). כתבי 'יציאה' כדי לסיים.\n")
        while (text := input("את: ").strip()) not in ("יציאה", "exit", "quit"):
            if text:
                print(f"\nWearMe: {(await weary.ask(text))['text']}\n")

    asyncio.run(chat())
