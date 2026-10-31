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
