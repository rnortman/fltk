# Design: Phase 4 — Integration (Rust Parser Codegen)

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Requirements: controlling design `docs/adr/2026/06/10-rust-parser-codegen/design.md` (§6 Phase 4 entry; §5 items 4-5; §3.4) and `request.md` in that directory. Facts: `exploration.md` in this directory. This doc plans only Phase 4; Phases 1-3 are implemented and not redesigned here.

---

## 1. Context

Phase 4 is the final, smallest phase: consolidation, not construction. The controlling design defines it as (§6):

> Makefile/`make check` wiring, no-pyo3 checks, self-hosting test (items 4-5), ADR README recording the §2 decision.

After Phases 1-3 (exploration.md §2), most of §3.4's build wiring already exists: `fltk-parser-core` is a workspace member covered by `cargo-test`/`cargo-test-no-python`/`cargo-clippy-no-python` and by a `check-no-pyo3` stanza (Makefile:84-86); both fixture crates (`tests/rust_parser_fixture`, `tests/rust_cst_fegen`) have committed generated `parser.rs`, regen wiring in `make gencode` (Makefile:173-177), and python-on/python-off test+clippy lanes. The parity and binding-surface suites are committed and passing.

Exactly three gaps remain (exploration.md §3):

1. **`check-no-pyo3` does not cover the fixture parser crates.** §5 item 5 requires "no-pyo3 assertion ... for the fixture parser crate built `--no-default-features`"; Phase 3 explicitly deferred this ("The cargo tree assertion stays Phase 4").
2. **No self-hosting test for the Rust *parser*.** `tests/test_phase4_fegen_rust_backend.py` exercises Python-parser → Rust-CST → `Cst2Gsm`. §5 item 4 requires Rust-parser → Rust-CST → real `Cst2Gsm` over fegen.fltkg, equal to the Python path's GSM.
3. **No ADR README.** `docs/adr/2026/06/10-rust-parser-codegen/README.md` does not exist; §6 names it a deliverable recording the §2 direct-emission decision, and §3.1 requires it (plus the generator docstring) to document the regex-crate-subset restriction. The `gsm2parser_rs.py` module docstring currently does not mention the regex subset either.

No production Rust or generator-logic code changes. No TODO.md items are opened or closed (exploration.md §5).

---

## 2. Proposed approach

### 2.1 `check-no-pyo3` — two new stanzas (Makefile:76-87)

Extend the existing `check-no-pyo3` recipe, preserving its established pattern (positive control before negative assertion, `--edges normal,build`, single `set -e` shell block):

**Stanza A — `tests/rust_parser_fixture`, default features** (the §5 item 5 requirement). Default features are empty (Cargo.toml has `python`/`extension-module` but no `default`), so no `--features` flag *is* the python-off build:

```
fixture="$(cargo tree --manifest-path tests/rust_parser_fixture/Cargo.toml --edges normal,build)"
echo "$fixture" | grep -q fltk-parser-core || FAIL (check broken)
! echo "$fixture" | grep -q pyo3 || FAIL (pyo3 present)
```

Positive control is `fltk-parser-core` (a direct dependency, Cargo.toml:18), not `fltk-cst-core`, mirroring how each existing stanza controls on a crate guaranteed present in that graph.

**Stanza B — `tests/rust_cst_fegen --no-default-features`.** The exploration (§3.1) flags this as a Phase 4 judgment call: this crate's default features are python-on (`default = ["extension-module"]`), and `--no-default-features` is its pure-Rust consumer lane, already exercised by `cargo-test-no-python` and `cargo-clippy-no-python` but not asserted pyo3-free. Decision: **include it.** It is the fegen-grammar fixture parser crate — the in-tree template for "pure-Rust consumer of a generated parser" — and the assertion is one stanza:

```
fegen="$(cargo tree --manifest-path tests/rust_cst_fegen/Cargo.toml --no-default-features --edges normal,build)"
echo "$fegen" | grep -q fltk-parser-core || FAIL (check broken)
! echo "$fegen" | grep -q pyo3 || FAIL (pyo3 present)
```

Both crates are standalone workspaces (`[workspace]` stanza in each Cargo.toml), so `--manifest-path` resolves them independently of the root workspace — no feature unification can leak pyo3 in from `fltk-native`, and the assertion tests exactly what an out-of-tree consumer's graph would contain.

One adjacent comment edit: the recipe's explanatory comment (Makefile:73-75) currently says "Uses a positive control (fltk-cst-core present)", which becomes inaccurate once Stanzas A/B control on `fltk-parser-core`. Generalize it to "a positive control on a crate guaranteed present in that graph". No other Makefile changes: the `check` step list already includes `check-no-pyo3`, and the success message (Makefile:87, "pyo3 absent from python-off graphs") already describes the new stanzas accurately.

`tests/rust_cst_fixture` (CST-only fixture, no parser) is not added: the controlling design names only the parser crates, and its python-off coverage is out of Phase 4's scope.

### 2.2 Self-hosting test — new class in `tests/test_phase4_fegen_rust_backend.py`

New test class `TestRustParserSelfHosting` in the existing file (the controlling design says "extend the phase-4 pattern", not a new file or plumbing path — exploration.md §3.2). The module-level `pytest.importorskip("fegen_rust_cst")` already provides the build-gating/skip behavior.

Path under test, per fegen input text:

```python
parser = fegen_rust_cst.Parser(text, capture_trivia=False)  # matches the committed Python
                                                             # fltk_parser (non-trivia) variant
result = parser.apply__parse_grammar(0)
assert result is not None, parser.error_message()   # diagnostic on failure
assert result.pos == len(text), parser.error_message()  # partial consume is a failure too;
                                                         # len(str) = codepoints = Rust positions
gsm_rust = fltk2gsm.Cst2Gsm(text).visit_grammar(result.result)
gsm_python = plumbing.parse_grammar(text)           # pure-Python reference path
assert gsm_rust == gsm_python
```

Key facts grounding this:
- `Cst2Gsm.__init__` takes the raw terminals `str` (fltk2gsm.py:11-13); `parse_grammar` passes `terminals.terminals` which is that same string (plumbing.py:146).
- `result.result` is the canonical CST handle (`fegen_rust_cst.Grammar`); `Cst2Gsm.visit_grammar` consumes it through the same accessor surface (`children_rule()`, `child_name()`, ...) the existing AC8 tests already prove works on Rust nodes.
- `gsm.Grammar` equality is dataclass equality, already relied on by `TestAC8RealCst2GsmRustBackend`.
- The Python reference is `parse_grammar(text)` with **no** `rust_fegen_cst_module` — the fully-Python path, so the test compares Rust-parser→Rust-CST against Python-parser→Python-CST end to end.

Test cases (reusing the module's existing input constants):
1. `_SIMPLE_GRAMMAR` — minimal smoke.
2. `_MULTI_RULE_GRAMMAR` — alternatives, regex, multiple rules.
3. `fegen.fltkg` itself (`_FEGEN_FLTKG_PATH`) — the §5 item 4 requirement verbatim and the strongest check: the grammar that parses all user grammars, self-hosted through the Rust parser.

Shared logic goes in one helper function inside the class; the three tests differ only in input. No new fixtures, no plumbing.py changes (in-tree adoption is explicitly a follow-up — controlling design §3.4 and user answer A2).

### 2.3 ADR README — `docs/adr/2026/06/10-rust-parser-codegen/README.md`

New file following the repo ADR convention (context / decision / consequences; cf. `docs/adr/2026/05/25-rust-backend-exploration/README.md` for the directory-index style, CLAUDE.md ADR section for the record requirements). Contents:

- **Title + status**: Accepted, decision date 2026-06-10.
- **Context**: Rust CST codegen complete; goal of dual-target (pure-Rust / Python) generated parsers; pointer to `request.md` (verbatim user requirements) and `exploration.md`.
- **Decision**: direct Rust emission via `gsm2parser_rs.py`, *not* an IIR→Rust compiler backend — a condensed record of design.md §2 with the four load-bearing reasons (IIR encodes the Python CST API; Python-shaped ownership structure; RefType annotations wrong for Rust; constructs the IIR cannot represent) and the §2.6 commitment that a future unparser uses the same direct-emission path.
- **Regex subset**: grammar regexes must be in the common subset of Python `re` and the Rust `regex` crate (no lookaround/backreferences); enforcement is the generated `#[test]` that compiles every pattern, failing `cargo test` with the pattern named. Records user answer A1 (subset-only is the accepted permanent default; `fancy_regex` only if a need arises).
- **Consequences**: two generators that can drift, with parity tests as the contract (§2.7 mitigations); one codegen idiom in the codebase; parser API freedom (parsers don't cross the boundary) with the deliberate divergences listed (constructor shape, `error_message()`/`error_position()` instead of `error_tracker`).
- **Phases**: one-line-per-phase index linking the four phase design docs (`10-rust-parser-runtime-crate`, `10-rust-parser-generator`, `10-rust-parser-python-bindings`, `10-rust-parser-integration`).

The README condenses and points; it does not duplicate design.md prose at length. design.md remains in the directory as the full record.

### 2.4 Generator docstring — regex-subset note

Controlling design §3.1: the regex restriction is "Documented in the generator's docstring and ADR README." The README half is §2.3; the docstring half was not done in Phase 2 (`gsm2parser_rs.py` module docstring has no mention — verified). Add one short paragraph to the `gsm2parser_rs.py` module docstring stating the supported pattern subset and the generated compile-test enforcement. This edits generator *source* only (module docstring), not emitted code — `make gencode` output is unchanged.

### Files touched (complete list)

| File | Change |
|---|---|
| `Makefile` | Two stanzas in `check-no-pyo3` |
| `tests/test_phase4_fegen_rust_backend.py` | New `TestRustParserSelfHosting` class |
| `docs/adr/2026/06/10-rust-parser-codegen/README.md` | New ADR README |
| `fltk/fegen/gsm2parser_rs.py` | Docstring paragraph (regex subset) |

---

## 3. Edge cases / failure modes

- **`grep -q pyo3` over `cargo tree` output**: substring match would also catch hypothetical crates merely *named* `*pyo3*` — conservative in the right direction (false failure, never false pass). The positive control guards the real failure mode: `cargo tree` erroring or printing nothing under `set -e` quirks would otherwise vacuously pass the negative grep.
- **Feature drift in fixture Cargo.tomls**: if someone later adds `default = ["python"]` to `rust_parser_fixture`, Stanza A immediately fails — the assertion doubles as a regression guard on the crate's "pure-Rust by default" contract.
- **Self-hosting test passes on first run**: expected. Phase 4 adds no production code; the test is integration *verification* of already-landed phases through a previously unexercised composition. TDD's fail-first step does not apply (nothing to fix); the test's value is gating future regressions in any of the three layers it crosses.
- **Skip-not-fail when extension is unbuilt**: the new class inherits the module-level `importorskip`. The existing module docstring already records that an all-skipped CI lane is a failure signal; unchanged.
- **`result.pos == len(text)` codepoint semantics**: Python `len(str)` counts codepoints; Rust parser positions are codepoint indices by design (controlling design §3.1). The invariant holds for multibyte input, though fegen.fltkg is ASCII.
- **Parse failure in self-hosting test**: both failure modes — `result is None` and partial consume (`pos < len(text)`) — carry `parser.error_message()` as the assertion message, matching the Python reference's treatment of both as one failure class (plumbing.py:137-144). The error tracker holds the farthest failure recorded, so partial-consume failures surface a formatted error rather than a bare `assert 1234 == 5678`.
- **ADR immutability**: the README is written as an accepted ADR; per CLAUDE.md convention, future reversals supersede with a new ADR rather than editing it.

---

## 4. Test plan

After Phase 4:

1. **New**: `TestRustParserSelfHosting` (3 tests) in `tests/test_phase4_fegen_rust_backend.py` — Rust parser → Rust CST → real `Cst2Gsm`, GSM-equal to the Python path, over `_SIMPLE_GRAMMAR`, `_MULTI_RULE_GRAMMAR`, and fegen.fltkg (§5 item 4 satisfied).
2. **New assertions**: `make check-no-pyo3` covers `fltk-parser-core` (existing), `tests/rust_parser_fixture` default-features, and `tests/rust_cst_fegen --no-default-features` (§5 item 5 satisfied).
3. **Unchanged but gating**: full `make check` green (lint, format, typecheck, pytest including parity suites, cargo test/clippy both feature lanes, check-no-pyo3); `make gencode` produces no diff (Phase 4 changes no generator output).
4. Acceptance walk (exploration.md §6): `make gencode` → no diff; `make build-fegen-rust-cst` → `make test` → bindings, parity, AC8, and new self-hosting tests all pass; `make check` → all steps pass.

---

## 5. Open questions

None. The one judgment call the exploration surfaced (whether `check-no-pyo3` also covers `tests/rust_cst_fegen --no-default-features`) is decided in §2.1: yes.
