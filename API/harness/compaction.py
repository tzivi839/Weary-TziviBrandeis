"""
compaction.py - האחריות: כשהשיחה ארוכה מדי, מסכמים אותה.

לכל מודל יש "חלון קונטקסט": כמות מקסימלית של טקסט שאפשר לשלוח לו בבת אחת.
וגם הרבה לפני שמגיעים לגבול, שיחה ארוכה עולה יותר כסף בכל שאלה.

מתי? אחרי כל תור בודקים כמה טוקני קלט הקריאה האחרונה שלחה.
      אם זה עבר את COMPACT_AT_TOKENS - מסכמים.
איך?  קריאה נפרדת ל-Claude: "הנה כל השיחה, סכם אותה בכמה שורות".
      הסיכום נשמר כשורה חדשה ב-history.jsonl (append-only: שום הודעה לא נמחקת).
ואז?  מהתור הבא, context.py שולח את הסיכום במקום כל ההודעות שהוא מחליף.

מה לא נכנס לסיכום? העדפות, ארון ויומן לבישה - אלה כבר שמורים בקבצים של shared/
ונשלפים ב-memory.py. הסיכום הוא רק על *השיחה*: מה ביקשת, מה הוצע, מה הוחלט.
"""

COMPACT_AT_TOKENS = 6000   # מעל כמה טוקני קלט בקריאה מסכמים
SUMMARY_MAX_TOKENS = 600

SUMMARY_PROMPT = """Summarize this conversation between a user and Weary, a wardrobe assistant.
Keep: what the user asked for, outfits suggested and chosen, decisions and open requests.
Skip: wardrobe contents and user preferences (stored elsewhere).
At most 8 short lines, in English."""


def log(msg):
    print(f"[compaction.py] {msg}")


def _get(block, key):
    """בלוק יכול להיות מילון (נטען מהדיסק) או אובייקט (מהסשן הנוכחי)."""
    return block.get(key) if isinstance(block, dict) else getattr(block, key, None)


def _as_text(messages):
    """הופך את השיחה לטקסט פשוט וקצר, כדי לשלוח אותה לסיכום."""
    lines = []
    for m in messages:
        if isinstance(m["content"], str):
            lines.append(f"{m['role']}: {m['content']}")
            continue
        for block in m["content"]:
            kind = _get(block, "type")
            if kind == "text":
                lines.append(f"{m['role']}: {_get(block, 'text')}")
            elif kind == "tool_use":
                lines.append(f"[tool {_get(block, 'name')} {_get(block, 'input')}]")
            elif kind == "tool_result":
                lines.append(f"[result {str(_get(block, 'content'))[:150]}]")
    return "\n".join(lines)


def last_input_tokens(usages):
    """כמה טוקני קלט שלחה הקריאה האחרונה בתור (כולל מה שהגיע מה-cache)."""
    u = usages[-1]
    return u.input_tokens + (u.cache_read_input_tokens or 0) + (u.cache_creation_input_tokens or 0)


def maybe_compact(client, messages, history, usages, *, model):
    """
    מסכם אם צריך. מחזיר את ה-usage של קריאת הסיכום (כדי ש-tokens.py יספור גם אותה),
    או None אם לא היה צורך.
    """
    size = last_input_tokens(usages)
    if size < COMPACT_AT_TOKENS:
        return None
    if messages[-1]["role"] != "assistant":
        return None   # התור לא הסתיים כרגיל (למשל נקטע), לא מסכמים באמצע

    log(f"last call sent {size} input tokens (limit {COMPACT_AT_TOKENS}) - summarizing")
    transcript = _as_text(messages)
    if history.summary:   # סיכום קודם נכנס לסיכום החדש, כדי ששום דבר לא ילך לאיבוד
        transcript = f"Earlier summary:\n{history.summary}\n\nLater conversation:\n{transcript}"

    resp = client.messages.create(
        model=model,
        max_tokens=SUMMARY_MAX_TOKENS,
        system=SUMMARY_PROMPT,
        messages=[{"role": "user", "content": transcript}],
    )
    summary = "".join(b.text for b in resp.content if b.type == "text").strip()
    history.save_summary(summary, upto=len(messages))
    log(f"summary: {len(summary)} chars instead of {len(messages)} messages")
    return resp.usage
