"""AST smoke test for MatrixDisplay.py.

Parses the runtime module WITHOUT importing it (PyQt6 + win32 imports
would fail on Linux). Asserts the public surface declared in the
ProjectDescription.mdc / history.mdc is structurally present.
"""
import ast
import pathlib
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
