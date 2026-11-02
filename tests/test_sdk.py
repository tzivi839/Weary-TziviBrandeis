"""
test_sdk.py - בדיקות offline לגרסת ה-SDK. בלי Claude Code, בלי login ובלי אינטרנט.

FakeSDKClient מתחזה ל-ClaudeSDKClient: הוא לא מריץ את Claude Code, אלא מחזיר
הודעות שהכנו מראש (AssistantMessage עם בקשה לכלי, ואז ResultMessage).
"""
import asyncio
import json

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, ToolUseBlock

from SDK import agent as sdk_agent
from SDK.agent import Weary
from SDK.main import HARNESS_PARTS, run_scenario
from SDK.tools import build_server
from shared.preferences import Preferences


def result(session_id="s1", turns=2):
    return ResultMessage(subtype="success", duration_ms=10, duration_api_ms=8, is_error=False,
                         num_turns=turns, session_id=session_id, total_cost_usd=0.0123,
                         usage={"input_tokens": 50, "cache_read_input_tokens": 900,
                                "cache_creation_input_tokens": 100, "output_tokens": 70},
                         result="תלבשי את החצאית השחורה")


class FakeSDKClient:
    created = []                       # כל ה-options שה-agent יצר, לבדיקה

    def __init__(self, options):
        self.options = options
        FakeSDKClient.created.append(options)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def query(self, prompt):
        self.prompt = prompt

    async def receive_response(self):
        yield AssistantMessage(content=[ToolUseBlock(id="t1", name="mcp__weary__get_weather",
                                                     input={"city": "Jerusalem", "day": "2026-10-30"})],
                               model="claude-opus-5-5")
        yield result()


def ask(weary, text):
    return asyncio.run(weary.ask(text))


def test_tools_wrap_shared_code(tmp_path):
    _, tools = build_server(tmp_path)
    by_name = {t.name: t for t in tools}
    assert len(tools) == 8
    out = asyncio.run(by_name["save_preference"].handler({"topic": "city", "text": "Jerusalem"}))
    assert out["content"][0]["text"] == "saved city"
    assert Preferences(tmp_path).prefs == {"city": "Jerusalem"}     # נשמר דרך shared/


def test_options_follow_the_assignment(tmp_path):
    FakeSDKClient.created.clear()
    ask(Weary(tmp_path, day="2026-10-30", client_factory=FakeSDKClient), "מה ללבוש?")
    o = FakeSDKClient.created[0]
    assert o.strict_mcp_config is True
    assert o.tools == []                                             # בלי כלים מובנים
    assert len(o.allowed_tools) == 8 and all(t.startswith("mcp__weary__") for t in o.allowed_tools)
    assert o.system_prompt.startswith("You are Weary")               # system prompt משלנו
    assert o.setting_sources == ["project"]
    assert (o.model, o.effort) == ("claude-opus-5-5", "medium")


def test_turn_measurement_and_tools(tmp_path):
    r = ask(Weary(tmp_path, day="2026-10-30", client_factory=FakeSDKClient), "מה ללבוש?")
    assert r["tokens"] == {"input": 50, "cache_read": 900, "cache_write": 100, "output": 70}
    assert r["cost_usd"] == 0.0123 and r["model_calls"] == 2
    assert r["tools"] == [{"name": "get_weather", "input": {"city": "Jerusalem", "day": "2026-10-30"}}]


def test_session_two_resumes_and_gets_memory(tmp_path):
    Preferences(tmp_path).save_preference("city", "Jerusalem")
    ask(Weary(tmp_path, day="2026-10-29", client_factory=FakeSDKClient), "היי")
    FakeSDKClient.created.clear()
    s2 = Weary(tmp_path, day="2026-10-30", client_factory=FakeSDKClient)   # מופע חדש
    ask(s2, "בוקר טוב")
    assert FakeSDKClient.created[0].resume == "s1"                  # ממשיך את השיחה מהדיסק
    assert "city: Jerusalem" in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")


def test_refuses_to_run_with_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    with pytest.raises(SystemExit):
        sdk_agent.check_no_api_key()


def test_sdk_scenario_results_structure(tmp_path):
    scenario = json.load(open("scenario.json", encoding="utf-8"))
    results = asyncio.run(run_scenario(scenario, state_dir=tmp_path / "run", client_factory=FakeSDKClient))
    assert results["version"] == "sdk" and len(results["turns"]) == 8
    assert set(results["lines_of_code"]) == set(HARNESS_PARTS) | {"total"}
    assert results["lines_of_code"]["caching"] == 0                  # אוטומטי: אין קוד
