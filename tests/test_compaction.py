"""
test_compaction.py - בודק את סיכום השיחה. בלי מודל אמיתי.
"""
from types import SimpleNamespace as NS

from API.agent import Weary
from API.harness import compaction
from API.harness.history import History
from tests.test_loop import FakeClient, text, text_of


def big_usage(tokens):
    return NS(input_tokens=tokens, output_tokens=50,
              cache_read_input_tokens=0, cache_creation_input_tokens=0)


class FakeClientWithUsage(FakeClient):
    """כמו FakeClient, אבל אפשר לקבוע כמה טוקנים כל תשובה "עלתה"."""
    def __init__(self, responses, tokens):
        super().__init__(responses)
        self.tokens = list(tokens)

    def create(self, **kwargs):
        resp = super().create(**kwargs)
        resp.usage = big_usage(self.tokens.pop(0))
        return resp


def test_no_compaction_below_limit(tmp_path):
    client = FakeClientWithUsage([([text("היי")], "end_turn")], [500])
    result = Weary(state_dir=tmp_path, day="2026-10-30", client=client).ask("היי")
    assert result["compacted"] is False
    assert len(client.sent) == 1                      # רק הקריאה הרגילה


def test_compaction_above_limit_and_next_turn_uses_summary(tmp_path):
    over = compaction.COMPACT_AT_TOKENS + 1
    client = FakeClientWithUsage([
        ([text("תלבשי את החצאית השחורה")], "end_turn"),        # התור הרגיל
        ([text("User asked what to wear; Weary suggested the black skirt.")], "end_turn"),  # סיכום
        ([text("בוקר טוב")], "end_turn"),                       # התור הבא
    ], [over, 300, 400])
    weary = Weary(state_dir=tmp_path, day="2026-10-30", client=client)

    result = weary.ask("מה ללבוש?")
    assert result["compacted"] is True and result["model_calls"] == 2
    assert "מה ללבוש?" in client.sent[1]["messages"][0]["content"]   # הסיכום קיבל את השיחה

    # התור הבא: ההודעות שסוכמו לא נשלחות, והסיכום נמצא ב-context
    weary.ask("בוקר טוב")
    sent = client.sent[2]["messages"]
    assert len(sent) == 1
    assert "black skirt" in text_of(sent[0]) and text_of(sent[0]).endswith("בוקר טוב")


def test_summary_survives_restart_and_history_is_kept(tmp_path):
    h = History(tmp_path)
    h.save_new([{"role": "user", "content": "א"}, {"role": "assistant", "content": "ב"}])
    h.save_summary("short summary", upto=2)

    fresh = History(tmp_path)
    messages = fresh.load()
    assert len(messages) == 2                         # ההודעות המקוריות לא נמחקו
    assert (fresh.summary, fresh.summary_upto) == ("short summary", 2)
