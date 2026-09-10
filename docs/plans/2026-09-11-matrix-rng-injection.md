# Matrix Display — RNG Injection Surface Implementation Plan

**Date:** 2026-09-11
**Repo:** TeacherEvan/Matrix (MatrixDisplay.py)
**Status:** VERIFIED COMPLETE (all objectives ticked; gates green)

## Objective

Make the Matrix display's randomness **deterministic and testable** by routing
all RNG through an injectable `rng` parameter on `MatrixWindow` and every helper
class, instead of the module-level `random` global. This is the change already
present in the working tree (commit `14ce7cb`); this plan documents and verifies it.

## Acceptance Criteria

| ID | Criterion | Evidence |
|----|-----------|----------|
| AC-001 | Helper classes (`CodeEffect`, `ExplosionParticle`, `MatrixSymbol`) accept `rng=None` and store `self.rng` | `test_rng_propagates_to_helpers` |
| AC-002 | Two `MatrixWindow(rng=random.Random(seed))` with same seed produce identical spawn sequences | `test_rng_determinism_seed` |
| AC-003 | Default `MatrixWindow()` (no rng) still constructs and spawns | `test_rng_default_path_runs` |
| AC-004 | Different seeds produce different sequences | `test_rng_different_seeds_diverge` |
| AC-005 | Break-it gate: bypassing `self.rng` collapses determinism | `test_rng_break_it_gate` |
| AC-006 | `MatrixWindow.__init__` accepts optional `rng` parameter | `test_matrixwindow_init_accepts_rng` |
| AC-007 | `__init__` docstring mentions `rng` | `test_matrixwindow_init_has_docstring` |
| AC-008 | Module imports `logging` stdlib | `test_logging_import_present` |
| AC-009 | Module-level `logger` assigned | `test_module_logger_assigned` |
| AC-010 | No stray `random.` calls outside `self.rng` | grep audit (0 hits) |

## Objectives

- [x] OBJ-001 — `MatrixWindow.__init__` accepts optional `rng` parameter
- [x] OBJ-002 — All randomness in `MatrixWindow` routed through `self.rng`
- [x] OBJ-003 — `CodeEffect` accepts and stores injected `rng`
- [x] OBJ-004 — `ExplosionParticle` accepts and stores injected `rng`
- [x] OBJ-005 — `MatrixSymbol` accepts and stores injected `rng`
- [x] OBJ-006 — Determinism test: same seed -> identical spawn sequences
- [x] OBJ-007 — Divergence test: different seeds -> different sequences
- [x] OBJ-008 — Default path (no rng) still works
- [x] OBJ-009 — Break-it gate proves determinism test is load-bearing
- [x] OBJ-010 — AST surface tests for `rng` parameter + docstring
- [x] OBJ-011 — `logging` stdlib import + module logger
- [x] OBJ-012 — `__init__` docstring >=50 chars, mentions `rng`

## Verification Gate

```bash
python3 -m py_compile MatrixDisplay.py   # OK
python3 -m pytest tests/ -v              # 23 passed
```

## Files

- `MatrixDisplay.py` — runtime (RNG injection surface on all 4 classes)
- `tests/test_rng_determinism.py` — behavioral + break-it gate
- `tests/test_rng_surface.py` — AST surface checks
- `tests/test_ast_smoke.py` — structural smoke tests
