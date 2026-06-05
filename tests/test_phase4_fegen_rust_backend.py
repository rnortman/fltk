"""Tier-2 Phase 4 tests: AC8 — real Cst2Gsm on the Rust fegen backend.

These tests require the fegen_rust_cst extension to be built.
They are skipped automatically when the module is not importable (run
`make build-fegen-rust-cst` first, or use CI which builds it before pytest).
A CI lane where every test here is skipped is a failure signal — the artifact
is not being built.

Test coverage:
  AC6 (partial) — make build-fegen-rust-cst produces an importable fegen_rust_cst module
  AC8 — the *real* fltk2gsm.Cst2Gsm runs against the Rust fegen backend via
         parse_grammar(rust_fegen_cst_module="fegen_rust_cst"); the resulting
         gsm.Grammar is equal to the Python-backend result on the same input.
         No hand-written substitute for Cst2Gsm.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import ClassVar

import pytest

# ---------------------------------------------------------------------------
# Module-level skip when fegen Rust CST extension not available
# ---------------------------------------------------------------------------

fegen_rust_cst = pytest.importorskip(
    "fegen_rust_cst",
    reason="fegen_rust_cst not built; run 'make build-fegen-rust-cst' first",
)

import fltk.fegen.fltk2gsm as fltk2gsm_mod  # noqa: E402
from fltk._native import fegen_cst as embedded_fegen_cst  # noqa: E402
from fltk.fegen import fltk2gsm, fltk_cst  # noqa: E402
from fltk.fegen.pyrt import terminalsrc as tsrc  # noqa: E402
from fltk.plumbing import parse_grammar, parse_grammar_file  # noqa: E402

# ── Shared test inputs ─────────────────────────────────────────────────────

_SIMPLE_GRAMMAR = 'test := "hello";'

_MULTI_RULE_GRAMMAR = """
thing := left , op , right ;
left := id ;
right := id ;
op := "+" | "-" ;
id := /[a-z]+/ ;
"""

_FEGEN_FLTKG_PATH = Path(__file__).parent.parent / "fltk" / "fegen" / "fegen.fltkg"


# ── AC8: real Cst2Gsm on Rust fegen backend ───────────────────────────────


class TestAC8RealCst2GsmRustBackend:
    """AC8 (binding): real fltk2gsm.Cst2Gsm runs against Rust fegen CST.

    parse_grammar(text, rust_fegen_cst_module="fegen_rust_cst") must produce
    a gsm.Grammar equal to parse_grammar(text) (Python backend) on the same input.
    No hand-written Cst2Gsm substitute.
    """

    def test_simple_grammar_rust_equals_python(self):
        """Simple single-rule grammar: Rust backend produces the same gsm.Grammar as Python."""
        python_result = parse_grammar(_SIMPLE_GRAMMAR)
        rust_result = parse_grammar(_SIMPLE_GRAMMAR, rust_fegen_cst_module="fegen_rust_cst")
        assert python_result == rust_result

    def test_multi_rule_grammar_rust_equals_python(self):
        """Multi-rule grammar with alternatives: Rust == Python backend."""
        python_result = parse_grammar(_MULTI_RULE_GRAMMAR)
        rust_result = parse_grammar(_MULTI_RULE_GRAMMAR, rust_fegen_cst_module="fegen_rust_cst")
        assert python_result == rust_result

    def test_fegen_grammar_itself_rust_equals_python(self):
        """Parse fegen.fltkg itself with both backends; results must be equal.

        This is the strongest AC8 check: the actual fegen grammar (used to parse
        all user grammars) produces the same gsm.Grammar regardless of CST backend.
        """
        python_result = parse_grammar_file(_FEGEN_FLTKG_PATH)
        rust_result = parse_grammar_file(_FEGEN_FLTKG_PATH, rust_fegen_cst_module="fegen_rust_cst")
        assert python_result == rust_result

    def test_rust_backend_uses_real_cst2gsm(self):
        """Verify the Rust path injects a cst_module into Cst2Gsm (not the default fltk_cst).

        Monkeypatches Cst2Gsm.__init__ to capture the cst argument.  Confirms
        the cst kwarg is not fltk_cst (the Python default), proving injection occurred.
        """
        captured: list[object] = []
        original_init = fltk2gsm_mod.Cst2Gsm.__init__

        def recording_init(self, terminals, cst=fltk_cst):
            captured.append(cst)
            return original_init(self, terminals, cst=cst)

        fltk2gsm_mod.Cst2Gsm.__init__ = recording_init
        try:
            parse_grammar(_SIMPLE_GRAMMAR, rust_fegen_cst_module="fegen_rust_cst")
        finally:
            fltk2gsm_mod.Cst2Gsm.__init__ = original_init

        assert len(captured) == 1, "Cst2Gsm.__init__ not called exactly once"
        injected_cst = captured[0]
        assert injected_cst is not fltk_cst, "Rust backend should inject the Rust CST module, not fltk_cst"


# TODO(rust-cst-child-span-test): add a focused test that calls child_name() / child_value()
# on a Rust-backed fegen node and asserts .start/.end are accessible and correct.
# The AC8 equality test exercises this indirectly but a focused test aids root-cause diagnosis.

# ── AC6 (partial): fegen_rust_cst is importable and has expected classes ──


class TestAC6FegenRustCstModule:
    """AC6 (partial): the fegen Rust CST module exposes the expected 14 grammar node classes."""

    _EXPECTED_CLASSES: ClassVar[list[str]] = [
        "Grammar",
        "Rule",
        "Alternatives",
        "Items",
        "Item",
        "Term",
        "Disposition",
        "Quantifier",
        "Identifier",
        "RawString",
        "Literal",
        "Trivia",
        "LineComment",
        "BlockComment",
    ]

    @pytest.mark.parametrize("class_name", _EXPECTED_CLASSES)
    def test_class_exposed(self, class_name: str):
        """fegen_rust_cst exposes each expected grammar node class."""
        assert hasattr(fegen_rust_cst, class_name), f"Missing class: {class_name}"
        assert isinstance(getattr(fegen_rust_cst, class_name), type)

    def test_module_is_standalone(self):
        """The fegen_rust_cst module is importable separately from fltk._native.fegen_cst."""
        mod = importlib.import_module("fegen_rust_cst")
        assert mod is not None
        # Verify it's distinct from the embedded fltk._native.fegen_cst submodule
        assert mod is not embedded_fegen_cst


# ── Injection seam: Cst2Gsm can be used with injected fegen_rust_cst namespace ──


class TestCst2GsmInjection:
    """Verify the DI seam: Cst2Gsm accepts the fegen_rust_cst module directly as cst=."""

    def test_cst2gsm_accepts_fegen_rust_cst_as_namespace(self):
        """Cst2Gsm(terminals, cst=fegen_rust_cst) doesn't crash on construction.

        Full execution is tested via AC8 (parse_grammar Rust path).  This test
        isolates the seam: DI of the Rust namespace into Cst2Gsm's constructor.
        """
        terminals_obj = tsrc.TerminalSource(_SIMPLE_GRAMMAR)
        # Construction only; actual visit requires Rust-backed nodes.
        cst2gsm_instance = fltk2gsm.Cst2Gsm(terminals_obj.terminals, cst=fegen_rust_cst)
        assert cst2gsm_instance.cst is fegen_rust_cst
