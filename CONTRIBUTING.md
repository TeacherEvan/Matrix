# Contributing to MatrixDisplay

## Runtime

`MatrixDisplay.py` is **Windows-only**. It uses `pywin32` for
click-through window layering and is hard-coupled to the Windows
desktop. Running the GUI on Linux/macOS will fail at `import win32gui`.

## Verify a change

Even without a Windows host you can verify structural integrity:

```bash
python -m py_compile MatrixDisplay.py
python -m pytest tests/
```

The AST smoke test parses `MatrixDisplay.py` and asserts the key
classes (`SymbolTrail`, `ExplosionParticle`, `CodeEffect`,
`MatrixSymbol`, `MatrixWindow`) and the `main()` entry point exist.
It does NOT import the module (Windows imports would fail on Linux).

## Style

- Python: 4-space indent, LF, UTF-8 (see `.editorconfig`)
- Max line length: 120 (pragmatic, not strict)
- Do not introduce new top-level deps without updating `requirements.txt`

## Pushing

This repo is published from a Windows dev machine. From CI / Linux
agents, commit locally and let the maintainer handle `git push`. Never
force-push to `main`.
