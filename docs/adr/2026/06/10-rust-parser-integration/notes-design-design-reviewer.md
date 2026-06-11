# Design review findings — Phase 4 (integration)

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Verification summary (all source-checked at HEAD 8b3e92b, which matches the stated base commit):

- Makefile claims: `check-no-pyo3` recipe at lines 76-87, fltk-parser-core stanza at 84-86, success message at line 87 reading "pyo3 absent from python-off graphs", `check` step list (line 10) already includes `check-no-pyo3`, gencode regen wiring at lines 173-177 — all confirmed.
- `tests/rust_parser_fixture/Cargo.toml`: `[workspace]` stanza (line 1), no `default` feature (lines 12-14), `fltk-parser-core` direct dep at line 18 (design's citation "Cargo.toml:18" is exact; the exploration's "Cargo.toml:8" was off, the design corrected it) — confirmed. With empty default features, no-flag build = python-off; `--no-default-features` is a no-op for this crate, so Stanza A satisfies §5 item 5's literal wording.
- `tests/rust_cst_fegen/Cargo.toml`: `default = ["extension-module"]` (line 15), `[workspace]` (line 3), non-optional `fltk-parser-core` dep (line 22, so Stanza B's positive control is present under `--no-default-features`) — confirmed.
- `tests/test_phase4_fegen_rust_backend.py`: module-level `pytest.importorskip("fegen_rust_cst")` (line 29), constants `_SIMPLE_GRAMMAR`/`_MULTI_RULE_GRAMMAR`/`_FEGEN_FLTKG_PATH` (lines 44-54), `TestAC8RealCst2GsmRustBackend` relying on `gsm.Grammar ==` — confirmed.
- `fltk2gsm.py:11-13`: `Cst2Gsm.__init__(self, terminals)` takes the raw str — confirmed. `plumbing.py:146`: `Cst2Gsm(terminals.terminals)` — confirmed. `parse_grammar(text)` with no `rust_fegen_cst_module` is the fully-Python path using committed `fltk_parser` (non-trivia variant, plumbing.py:132-148) — confirmed, so `capture_trivia=False` is the matching Rust-side setting.
- `gsm2parser_rs.py` module docstring (4 lines) contains no regex-subset mention — confirmed; §2.4's gap claim is accurate.
- `docs/adr/2026/06/10-rust-parser-codegen/README.md` does not exist; `docs/adr/2026/05/25-rust-backend-exploration/README.md` exists as the style reference — confirmed.
- Phase 3 design deferral quote "The cargo tree assertion stays Phase 4" — confirmed (10-rust-parser-python-bindings/design.md:220, also line 134).

Coverage map (controlling design §6 Phase 4 entry + §5 items 4-5 + §3.4): Makefile/`make check` wiring → §2.1 (plus accurate inventory of already-landed wiring); no-pyo3 checks → §2.1 Stanzas A+B (covers both plausible readings of "the fixture parser crate built `--no-default-features`"); self-hosting test item 4 → §2.2 (fegen.fltkg included verbatim); item 5's "make check green incl. regenerated artifacts" → test plan items 3-4; ADR README → §2.3; controlling §3.1's docstring half → §2.4 (a controlling-design requirement Phase 2 missed; in scope, minimal). No uncovered deliverable. Stanza B and the two extra self-hosting inputs are the only additions beyond the literal Phase 4 entry; both are explicitly justified, one-stanza/one-helper sized, and Stanza B resolves the judgment call the exploration assigned to Phase 4 — not scope creep. No contradictions found.

---

## design-1

- **Section**: §2.1, "No other Makefile changes: ... the success message (Makefile:87 ...) already describes the new stanzas accurately."
- **What's wrong**: The recipe's explanatory comment (Makefile:73-75) says "Uses a positive control (fltk-cst-core present) before the negative assertion." Stanzas A and B control on `fltk-parser-core`, making the comment inaccurate after the change, and the design explicitly forecloses updating it ("No other Makefile changes").
- **Why**: Makefile:73-75 verbatim; design §2.1 proposes `grep -q fltk-parser-core` as the control for both new stanzas.
- **Consequence**: A stale maintainer-facing comment that misdescribes the check's structure; a future editor following the comment could "fix" a new stanza to control on `fltk-cst-core`, which is absent-by-design from neither graph here but is the wrong template for crates whose guaranteed-present dep differs. Documentation drift only — no functional breakage.
- **Suggested fix**: Generalize the comment ("a positive control on a crate guaranteed present in that graph") as part of the same edit; one-line change.

## design-2

- **Section**: §2.2 test snippet (`assert result.pos == len(text)`) vs §3 bullet "Parse failure in self-hosting test: `assert result is not None, parser.error_message()` surfaces the Rust-side formatted error."
- **What's wrong**: The diagnostic-on-failure claim covers only the `result is None` case. A partial-consume failure (`result` non-None, `pos < len(text)`) hits the bare `assert result.pos == len(text)` with no message. The Python reference path treats both cases identically (`if not result or result.pos != len(...)`: raise with formatted error — plumbing.py:137-144, 164-171); the design's snippet diverges from the pattern it cites.
- **Why**: plumbing.py:137 shows partial consume is a first-class failure mode of this exact grammar/parser pairing; the design's edge-case section claims debuggability that the snippet as written does not deliver for it.
- **Consequence**: If a future generator change makes the Rust parser stop short on fegen.fltkg, the test fails with `assert 1234 == 5678` and no error context — exactly the regression-debugging scenario §3 says the test is built for. Test still fails correctly; only the failure signal is degraded.
- **Suggested fix**: `assert result.pos == len(text), parser.error_message()` (the tracker holds the farthest failure recorded during the partial parse), or fold both checks into the shared helper with one diagnostic.
