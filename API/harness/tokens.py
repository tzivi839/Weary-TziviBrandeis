"""
tokens.py - האחריות: כמה טוקנים כל תור צרך, וכמה הוא עלה.

אחרי כל קריאה, ה-API מחזיר resp.usage עם ארבעה מספרים:
  input_tokens                 - טוקני קלט רגילים (בלי מה שהגיע מה-cache)
  cache_read_input_tokens      - קלט שנקרא מה-cache (זול מאוד)
  cache_creation_input_tokens  - קלט שנכתב ל-cache בפעם הראשונה (קצת יותר יקר מרגיל)
  output_tokens                - מה שהמודל כתב (הכי יקר)

תור אחד יכול לכלול כמה קריאות למודל (בגלל הכלים), אז מסכמים את כולן.
"""

# מחירים בדולרים למיליון טוקנים, ל-claude-opus-5-5.
# מקור: finout.io, "Claude Opus 5.5 pricing 2026". לעדכן אם המחירים משתנים.
PRICE_PER_MILLION = {
    "input": 4.00,
    "cache_read": 0.20,
    "cache_write": 5.00,    # cache של 5 דקות
    "output": 20.00,
}


def log(msg):
    print(f"[tokens.py] {msg}")


def summarize(usages):
    """מסכם את ה-usage של כל הקריאות בתור אחד, ומחשב עלות."""
    total = {
        "input": sum(u.input_tokens for u in usages),
        # "or 0" כי כשאין cache, ה-API עשוי להחזיר None במקום 0
        "cache_read": sum(u.cache_read_input_tokens or 0 for u in usages),
        "cache_write": sum(u.cache_creation_input_tokens or 0 for u in usages),
        "output": sum(u.output_tokens for u in usages),
    }
    cost = sum(total[k] * PRICE_PER_MILLION[k] for k in total) / 1_000_000
    total["cost_usd"] = round(cost, 5)

    # אחוז ה-cache: מתוך כל הקלט, כמה הגיע מה-cache. זה המספר שהדוח מבקש.
    all_input = total["input"] + total["cache_read"] + total["cache_write"]
    total["cache_pct"] = round(100 * total["cache_read"] / all_input, 1) if all_input else 0.0
    return total


class Meter:
    """סוכם את כל התורות בריצה, כדי להדפיס סיכום בסוף."""

    def __init__(self):
        self.turns = []

    def record(self, usages):
        t = summarize(usages)
        self.turns.append(t)
        log(f"turn: in={t['input']} cache_read={t['cache_read']} "
            f"cache_write={t['cache_write']} out={t['output']} "
            f"cache={t['cache_pct']}% cost=${t['cost_usd']:.4f}")
        return t

    def total(self):
        keys = ["input", "cache_read", "cache_write", "output", "cost_usd"]
        total = {k: round(sum(t[k] for t in self.turns), 5) for k in keys}
        all_input = total["input"] + total["cache_read"] + total["cache_write"]
        total["cache_pct"] = round(100 * total["cache_read"] / all_input, 1) if all_input else 0.0
        return total
