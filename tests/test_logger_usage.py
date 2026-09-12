"""Verify the module-level logger is actually USED, not just assigned.

OBJ-011 added ``logging`` + a module-level ``logger``; the original gate only
checked the symbol was *assigned*. This closes the gap by asserting the
logger is referenced in at least one real call site (not just its definition).
"""

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = ROOT / "MatrixDisplay.py"


def test_logger_is_assigned():
    """Module-level ``logger`` variable exists (regression guard)."""
    source = TARGET.read_text(encoding="utf-8")
    assert "logger" in source, "module-level logger missing"


def test_logger_is_called():
    """At least one ``logger.<method>(...)`` call exists beyond the definition."""
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(TARGET))
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name) and func.value.id == "logger":
                    calls.append(func.attr)
    assert calls, (
        "logger is assigned but never called — dead code. "
        f"Found {len(calls)} call sites."
    )


def test_no_bare_print_in_production():
    """No top-level ``print()`` calls remain in production code."""
    source = TARGET.read_text(encoding="utf-8")
    lines = source.splitlines()
    print_lines = [
        ln for ln in lines
        if ln.lstrip().startswith("print(")
    ]
    assert not print_lines, (
        f"{len(print_lines)} print() call(s) remain; use logger instead: "
        f"{print_lines[:3]}"
    )
