"""
store.py - שמירה וטעינה של המצב של Weary לדיסק, כקבצי JSON.

כל המצב יושב בתיקייה אחת (ברירת מחדל: state/).
למה זה חשוב: התרגיל דורש שכל ריצה תתחיל "ממצב נקי",
ומה שצריך בשביל זה הוא פשוט למחוק את התיקייה.
"""
import json
from pathlib import Path

DEFAULT_STATE_DIR = Path("state")


def load(name, default, state_dir=DEFAULT_STATE_DIR):
    """טוען את state/<name>.json. אם הקובץ לא קיים עדיין, מחזיר את default."""
    path = Path(state_dir) / f"{name}.json"
    if not path.exists():
        return default
    # encoding="utf-8" חשוב ב-Windows, אחרת עברית נשברת
    return json.loads(path.read_text(encoding="utf-8"))


def save(name, data, state_dir=DEFAULT_STATE_DIR):
    """שומר את data לקובץ state/<name>.json (ויוצר את התיקייה אם צריך)."""
    path = Path(state_dir) / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    # ensure_ascii=False כדי שעברית תישמר כעברית קריאה ולא כ-א...
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
