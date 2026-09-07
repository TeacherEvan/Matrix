"""Behavioral tests for the MatrixWindow RNG injection surface (OBJ-001, OBJ-012).

These tests parse MatrixDisplay.py and inspect the MatrixWindow class without
importing it (PyQt6 + win32 imports would fail on Linux). They verify:
  - the __init__ accepts an optional rng parameter
  - the __init__ has a non-empty docstring (OBJ-012)
  - the module imports the logging stdlib module (OBJ-011)
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


@pytest.fixture(scope="module")
def matrixwindow(tree):
    classes = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    assert "MatrixWindow" in classes, "MatrixWindow class missing"
    return classes["MatrixWindow"]


def test_matrixwindow_init_accepts_rng(matrixwindow):
    """OBJ-001: __init__ must accept an optional `rng` parameter."""
    init = None
    for node in matrixwindow.body:
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            init = node
            break
    assert init is not None, "MatrixWindow.__init__ not found"

    arg_names = [a.arg for a in init.args.args]
    defaults = init.args.defaults
    # Find the position of `rng` and confirm it has a default (i.e. optional).
    assert "rng" in arg_names, f"rng parameter missing; got args={arg_names}"
    rng_index = arg_names.index("rng")
    # The default list aligns with the rightmost args; verify rng is optional.
    num_required = len(arg_names) - len(defaults)
    assert rng_index >= num_required, (
        f"rng must have a default value to be optional "
        f"(args={arg_names}, defaults={len(defaults)})"
    )


def test_matrixwindow_init_has_docstring(matrixwindow):
    """OBJ-012: __init__ must have a non-empty docstring."""
    init = next(
        n for n in matrixwindow.body
        if isinstance(n, ast.FunctionDef) and n.name == "__init__"
    )
    doc = ast.get_docstring(init)
    assert doc is not None, "MatrixWindow.__init__ docstring missing"
    assert len(doc) >= 50, f"Docstring too short ({len(doc)} chars); expected >=50"
    # Spot-check: the docstring should describe the rng parameter.
    assert "rng" in doc.lower(), "docstring does not mention `rng` parameter"


def test_logging_import_present(source):
    """OBJ-011: module must import `logging` from stdlib."""
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports.append(alias.name)
    assert "logging" in imports, f"logging import missing; got {imports}"


def test_module_logger_assigned(tree):
    """OBJ-011: module-level logger should be assigned via logging.getLogger."""
    found = False
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "logger"
        ):
            found = True
            break
    assert found, "module-level `logger` assignment missing"
