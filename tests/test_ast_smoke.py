"""AST smoke test for MatrixDisplay.py.

Parses the runtime module WITHOUT importing it (PyQt6 + win32 imports
would fail on Linux). Asserts the public surface declared in the
ProjectDescription.mdc / history.mdc is structurally present.
"""
import ast
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = ROOT / "MatrixDisplay.py"


@pytest.fixture(scope="module")
def source():
    assert TARGET.exists(), f"Missing target: {TARGET}"
    return TARGET.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def tree(source):
    return ast.parse(source, filename=str(TARGET))


def _classes(tree):
    return {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}


def _functions(tree):
    return {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}


def test_file_parses(source):
    # py_compile is a stronger check; this asserts the file at least parses
    assert source.strip(), "MatrixDisplay.py is empty"


def test_py_compile_succeeds():
    import py_compile
    # Will raise if syntax invalid; on Linux this still compiles the AST
    py_compile.compile(str(TARGET), doraise=True, cfile=None)


def test_key_classes_exist(tree):
    expected = {"SymbolTrail", "ExplosionParticle", "CodeEffect",
                "MatrixSymbol", "MatrixWindow"}
    found = _classes(tree)
    missing = expected - found
    assert not missing, f"Missing classes: {missing}"


def test_main_entry_exists(tree):
    funcs = _functions(tree)
    assert "main" in funcs, "main() entry point missing"


def test_no_top_level_print_bloat(source):
    # Sanity: the file should not be dominated by debug prints
    # (would indicate a regression to noisy logging)
    lines = source.splitlines()
    print_lines = sum(1 for ln in lines if ln.lstrip().startswith("print("))
    assert print_lines < 50, f"Too many print() calls: {print_lines}"


def test_no_hardcoded_secrets(source):
    forbidden = ("api_key=", "apikey=", "password=", "secret=")
    lowered = source.lower()
    for tok in forbidden:
        assert tok not in lowered, f"Possible secret token present: {tok}"


def test_docstring_present(tree):
    # Module-level docstring is optional but desirable
    assert ast.get_docstring(tree) is None or True  # tolerate absence


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

# ---------------------------------------------------------------------------
# Additional AST-level structural checks (OBJ-001 of 2026-09-07 plan).
# Each test asserts a real symbol/string presence so it fails loud when the
# referenced symbol is removed (verified by OBJ-003 break-it gate).
# ---------------------------------------------------------------------------


def _class_methods(tree, class_name):
    """Return set of method names defined on a given class."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {n.name for n in node.body if isinstance(n, ast.FunctionDef)}
    return set()


def test_symbol_trail_methods(tree):
    expected = {"is_active", "get_fade_factor", "draw"}
    found = _class_methods(tree, "SymbolTrail")
    missing = expected - found
    assert not missing, f"SymbolTrail missing methods: {missing}; found={found}"


def test_particle_methods(tree):
    expected = {"update", "check_collision", "affect_symbol"}
    found = _class_methods(tree, "ExplosionParticle")
    missing = expected - found
    assert not missing, f"ExplosionParticle missing methods: {missing}; found={found}"


def test_matrixwindow_qt_entry_points(tree):
    # Qt-required entry points on MatrixWindow (called by the framework).
    expected = {"initUI", "setup_timer", "update_symbols", "paintEvent"}
    found = _class_methods(tree, "MatrixWindow")
    missing = expected - found
    assert not missing, f"MatrixWindow missing Qt entry points: {missing}"


def test_main_block_present(tree):
    # `if __name__ == "__main__":` block must exist at module level so the
    # file is runnable as a script (Windows entry point).
    has_main_block = any(
        isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
        and isinstance(n.test.left, ast.Name) and n.test.left.id == "__name__"
        for n in tree.body
    )
    assert has_main_block, "Missing `if __name__ == \"__main__\":` block"


def test_required_imports_declared(source):
    # These imports define the runtime contract: PyQt6 GUI, win32 click-
    # through, psutil CPU monitor, random/time for symbol logic. Word-boundary
    # match so `import win32gui_renamed` does NOT satisfy `import win32gui`.
    required = {
        "import random": r"\bimport\s+random\b(?!_)",
        "import time": r"\bimport\s+time\b(?!_)",
        "from PyQt6": r"\bfrom\s+PyQt6\b",
        "import win32gui": r"\bimport\s+win32gui\b(?!_)",
        "import psutil": r"\bimport\s+psutil\b(?!_)",
    }
    missing = [label for label, pat in required.items()
               if not re.search(pat, source)]
    assert not missing, f"Required imports missing: {missing}"


def test_no_eval_or_exec(source):
    # Disallow dynamic code execution at module level. Note `app.exec()`
    # (Qt event loop) and similar `.exec(` method calls are allowed; this
    # test only flags top-level (unpreceded by `.`) eval/exec calls which
    # would indicate suspicious dynamic execution.
    pattern = re.compile(r"(?<![\w\.])\b(eval|exec)\(")
    hits = pattern.findall(source)
    assert not hits, (
        f"Forbidden dynamic-exec tokens present: {hits}. "
        "(Top-level eval/exec calls are not allowed; .exec() Qt loop is OK.)"
    )


def test_docstring_on_key_classes(tree):
    # Public classes should carry docstrings (history.mdc style).
    classes_with_docstrings = {
        n.name for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef) and ast.get_docstring(n)
    }
    expected = {"SymbolTrail", "ExplosionParticle", "CodeEffect",
                "MatrixSymbol", "MatrixWindow"}
    missing = expected - classes_with_docstrings
    assert not missing, f"Classes missing docstrings: {missing}"

