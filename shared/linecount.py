"""
linecount.py - סופר שורות קוד, בשביל טבלת "שורות קוד לכל חלק ב-harness" בדוח.

נספרות רק שורות שיש בהן קוד אמיתי. לא נספרות:
  - שורות ריקות
  - הערות (#)
  - docstrings (ההסברים בין שלוש מירכאות בראש קובץ, מחלקה או פונקציה)
ככה ההסברים בעברית שכתבנו לא "מנפחים" את המספרים.
"""
import ast
from pathlib import Path


def _docstring_lines(tree):
    """מספרי השורות שתופסים docstrings."""
    lines = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                    and isinstance(body[0].value.value, str):
                lines.update(range(body[0].lineno, body[0].end_lineno + 1))
    return lines


def code_lines(path):
    """כמה שורות קוד יש בקובץ."""
    source = Path(path).read_text(encoding="utf-8")
    skip = _docstring_lines(ast.parse(source))
    count = 0
    for number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and number not in skip:
            count += 1
    return count


def replaces_lines(paths, parts):
    """
    ב-SDK: כמה שורות קוד מסומנות "# replaces: <part>", לכל part.
    שורת הערה בלבד לא נספרת. למשל compaction ו-caching יוצאים 0,
    כי ב-SDK אין להם שום קוד: Claude Code עושה אותם לבד.
    """
    counts = {part: 0 for part in parts}
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "# replaces:" not in stripped:
                continue
            part = stripped.split("# replaces:")[1].strip().split()[0]
            if part in counts:
                counts[part] += 1
    return counts
