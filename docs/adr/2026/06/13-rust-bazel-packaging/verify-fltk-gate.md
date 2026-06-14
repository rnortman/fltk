# FLTK Gate Verification — pyo3 fully-qualified-path generator change

**Verdict: GREEN**

The generator change (`gsm2tree_rs.py` / `gsm2parser_rs.py` now emit fully-qualified
`pyo3::types::PyList` / `pyo3::types::PyModule` instead of `use`-imports) is fully
consistent with FLTK's committed in-tree generated artifacts and passes the entire
canonical gate. Nothing is broken. No regen/`make fix`/recommit is needed — it was
already done in the same commits that changed the generators (3267fa0, aba376a).

Context:
- HEAD = `11d8460`. Generator change landed across `aba376a` (PyList) and `3267fa0`
  (PyModule). Each commit regenerated all fixtures and updated the tests in lockstep.

## Per-command results

### 1. Build — `uv run --group dev maturin develop`
PASS. Clean debug build, `🛠 Installed fltk-0.1.1`. No errors/warnings.

### 2a. Generator tests — `uv run pytest tests/test_gsm2tree_rs.py`
**206 passed, 0 failed.** (Note: the file lives at `tests/test_gsm2tree_rs.py`, not
`fltk/fegen/test_gsm2tree_rs.py`.) Includes the new positive test that a grammar rule
named `module` is accepted, and the PyList/PyModule collision-avoidance assertions.

### 2b. Full suite — `uv run pytest`
**1662 passed, 0 failed.** No failures of any kind.

### 2c. Generated-code drift — `make gencode` then `git diff --stat`
**Zero drift.** Regenerating every grammar's output from scratch (`make gencode`, which
runs the generators then `ruff` normalization) produces **no** changes to any committed
file. The committed generated artifacts (`src/cst_fegen.rs`, `src/cst_generated.rs`,
`crates/fltk-cst-spike/src/cst.rs`, all `tests/rust_cst_*/` and
`tests/rust_parser_fixture/` `.rs` files) are exactly what the current generators emit.
This is the decisive evidence that no in-tree generated artifact is stale.

### 3a. Type check — `uv run pyright` (canonical gate scope)
**0 errors, 0 warnings, 0 informations.** (Only a cosmetic "new pyright version
available" notice.)

### 3b. Lint — `uv run ruff check .`
**All checks passed.**

### 3c. Format — `uv run ruff format --check`
**Clean** (exit 0).

## The IDE-flagged pyright errors in test_gsm2tree_rs.py

The IDE reports 5 errors in `tests/test_gsm2tree_rs.py`:
- `:762` (and `:740`-ish): `Grammar` not assignable to protocol `Grammar`
  (`fltk_cst.Grammar.Label` vs `fltk_cst_protocol.Grammar.Label`) — `reportArgumentType`.
- `:1660`, `:1789`, `:1817`: `Operator "+" not supported for types "Sequence[Rule]"
  and "Sequence[Rule]"` — `reportOperatorIssue`.

These are **real** when pyright is pointed directly at the file
(`uv run pyright tests/test_gsm2tree_rs.py` → 5 errors), but they are:

1. **Out of gate scope.** `pyproject.toml` `[tool.pyright] include = ["fltk", "*.py"]`
   does **not** include `tests/`. The canonical `make check` pyright step therefore never
   sees this file. The IDE flags it only because IDE pyright type-checks the open file
   regardless of project `include`. Hence the gate is GREEN while the IDE shows red.

2. **Pre-existing and unrelated to the generator change.** The `+` operator lines are
   plain test-helper code that concatenates `gsm.Grammar.rules` (a `Sequence[Rule]`,
   which has no `+`). They exist **verbatim** at base `fafa6d7` (lines 1629 / 1758 / 1786
   there: `rules=g_a.rules + g_b.rules`, etc.). They originate from commit `108ee61`
   (`rust-generated-ident-collisions`), which predates and is unrelated to the
   PyList/PyModule fix. The protocol-mismatch error at `:762` is likewise pre-existing
   helper-typing noise (concrete `fltk_cst.Grammar` passed where the protocol type is
   expected). **None** of these were introduced or touched by the generator change.

## What (if anything) is broken — and attribution

| Item | State | Attributable to generator change? |
|------|-------|-----------------------------------|
| Rust build | PASS | n/a |
| pytest (full + generator) | PASS | n/a |
| pyright (gate scope) | PASS | n/a |
| ruff check / format | PASS | n/a |
| committed generated-code freshness | IN SYNC (zero drift) | n/a |
| IDE pyright errors in test_gsm2tree_rs.py | pre-existing, out of gate scope | **NO** — predate the change, present at base `fafa6d7` |

**Nothing is broken by the generator change.** The only red surface is IDE-only pyright
noise in a test file that (a) the gate does not check and (b) predates this work.

(Per instructions: nothing was fixed. Diagnosis only.)
