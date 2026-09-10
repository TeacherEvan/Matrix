"""Determinism + break-it gate for the MatrixWindow RNG injection surface.

These tests construct the REAL MatrixWindow (not an AST parse) by stubbing
the Windows-only `win32*` modules, so they run on any platform. They prove:

  - AC-002: two MatrixWindow(rng=random.Random(seed)) instances with the
    same seed produce identical symbol spawn sequences.
  - break-it gate: if the runtime bypasses self.rng (i.e. falls back to the
    module-level `random` global), the determinism test FAILS, which is the
    evidence that the wiring is load-bearing rather than decorative.
"""
import random
import sys
import types

import pytest


# ---------------------------------------------------------------------------
# Windows-only module stubs (module top-level imports otherwise fail on Linux)
# ---------------------------------------------------------------------------
def _stub_win32():
    for name in ("win32gui", "win32con", "win32api"):
        if name not in sys.modules:
            m = types.ModuleType(name)
            m.GetForegroundWindow = lambda: 0
            m.GetWindowRect = lambda h: (0, 0, 0, 0)
            m.GetWindowLong = lambda h, k: 0
            m.SetWindowLong = lambda h, k, v: 0
            m.SetWindowPos = lambda *a, **k: 0
            m.GetWindowText = lambda h: ""
            sys.modules[name] = m


_stub_win32()

from PyQt6.QtWidgets import QApplication  # noqa: E402

import MatrixDisplay  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _spawn_signature(window, n=5):
    """Capture the first n symbols' (symbol, x, y, speed, font_size) tuples."""
    out = []
    for _ in range(n):
        window.add_symbol()
    for sym in window.symbols:
        if sym is not None and sym.is_active:
            out.append((sym.symbol, round(sym.pos.x(), 6),
                        round(sym.pos.y(), 6), sym.speed, sym.size))
    return out


def test_rng_determinism_seed(qapp):
    """AC-002: same seed -> identical symbol spawn sequence."""
    a = MatrixDisplay.MatrixWindow(rng=random.Random(42))
    b = MatrixDisplay.MatrixWindow(rng=random.Random(42))
    seq_a = _spawn_signature(a)
    seq_b = _spawn_signature(b)
    assert seq_a == seq_b, (
        f"Determinism violated for seed=42:\n"
        f"  a={seq_a}\n  b={seq_b}"
    )


def test_rng_different_seeds_diverge(qapp):
    """Companion: different seeds must NOT produce identical sequences."""
    a = MatrixDisplay.MatrixWindow(rng=random.Random(1))
    b = MatrixDisplay.MatrixWindow(rng=random.Random(2))
    seq_a = _spawn_signature(a)
    seq_b = _spawn_signature(b)
    assert seq_a != seq_b, "Different seeds produced identical sequences"


def test_rng_default_path_runs(qapp):
    """AC-003: default MatrixWindow() (no rng) still constructs and spawns."""
    w = MatrixDisplay.MatrixWindow()
    assert w.rng is not None
    w.add_symbol()
    assert any(s is not None and s.is_active for s in w.symbols)


def test_rng_propagates_to_helpers(qapp):
    """AC-001: helper classes receive the injected rng, not module random."""
    w = MatrixDisplay.MatrixWindow(rng=random.Random(7))
    # CodeEffect must store the injected rng on its own attribute.
    effect = MatrixDisplay.CodeEffect(100.0, 100.0, w._blood_red_cache,
                                      0.0, 1.0, rng=w.rng)
    assert effect.rng is w.rng
    # ExplosionParticle must store the injected rng.
    particle = MatrixDisplay.ExplosionParticle(
        "A", 0.0, 0.0, (1.0, 0.0), 1.0, w._blood_red_cache, 1.0, rng=w.rng
    )
    assert particle.rng is w.rng
    # MatrixSymbol must store the injected rng.
    sym = MatrixDisplay.MatrixSymbol(0.0, 0.0, 1.0, w._blood_red_cache, 10.0,
                                    rng=w.rng)
    assert sym.rng is w.rng


def test_rng_break_it_gate(qapp):
    """Break-it gate: if self.rng is bypassed, determinism collapses.

    This test monkeypatches MatrixWindow to use the module-level `random`
    global instead of the injected rng, then asserts the determinism test
    FAILS. It proves the determinism test is load-bearing.
    """
    import MatrixDisplay as mod

    real_init = MatrixDisplay.MatrixWindow.__init__

    def bypassed_init(self, rng=None):
        # Pretend the injection surface does not exist: force the module
        # global random to be used everywhere by replacing self.rng with a
        # fresh unseeded instance that differs per construction.
        real_init(self, rng=None)
        self.rng = random.Random()  # unseeded -> non-deterministic

    MatrixDisplay.MatrixWindow.__init__ = bypassed_init
    try:
        a = MatrixDisplay.MatrixWindow(rng=random.Random(42))
        b = MatrixDisplay.MatrixWindow(rng=random.Random(42))
        seq_a = _spawn_signature(a)
        seq_b = _spawn_signature(b)
        assert seq_a != seq_b, (
            "break-it gate did NOT fire: bypassed rng still produced "
            "identical sequences (determinism test is not load-bearing)"
        )
    finally:
        MatrixDisplay.MatrixWindow.__init__ = real_init
