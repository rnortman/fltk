# Design review findings: forged-abi-extract-span-uniformity

Verification summary (context for the judge): I checked every substantive claim against
source at the actual base (`c03a801`). The core technical story is **verified end-to-end**:

- Forge path is real: `get_span_type` resolves `fltk._native.Span` by mutable name lookup
  (`crates/fltk-cst-core/src/cross_cdylib.rs:464-466`) and validates only the two forgeable
  classattrs via `check_abi_pair` (`cross_cdylib.rs:185-260`); `extract_span`'s
  `is_instance` (`cross_cdylib.rs:433`) then trivially passes for instances of the cached
  forge, reaching `cast_unchecked` (`cross_cdylib.rs:443`). The superseded "no rejection
  power" claim is exactly where the design says (`TODO.md:15-22`, code marker
  `cross_cdylib.rs:417-421`, prior burndown
  `docs/adr/2026/06/14-rust-backend-assessment/burndown/fix-forged-abi-segfault/design.md:217-219`).
- `check_instance_layout` (`cross_cdylib.rs:292-339`) is generic over `T: PyClassImpl`,
  takes `type_label`, and its doc comment (line 285) explicitly anticipates reuse for
  `Span` — the "no changes needed" claim holds.
- Gate-ordering / cache-invariant precedent on the SourceText path is at
  `cross_cdylib.rs:56-65` as cited; the quoted `check_abi_pair::<Span>(...)` line matches
  `cross_cdylib.rs:474` exactly.
- No `cast_unchecked` in generated consumer code: zero hits in
  `crates/fegen-rust/src/cst.rs` and none emitted by `fltk/fegen/gsm2tree_rs.py`
  (child-enum extraction at `gsm2tree_rs.py:1000` also funnels through `extract_span`).
  `Grammar::new`'s `extract_span` call is at `cst.rs:572` exactly as cited; setter at 599.
- `Span` has no `subclass` flag (`span.rs:287-289`); classattr docs referencing the
  `get_span_type` gate exist (`span.rs:571-598`).
- Test-suite claims verified: `_run_script` at `tests/test_rust_span.py:17-25`;
  `fegen_rust_cst` module-level importorskip at line 13; `TestSpanPathAbiGate` pre-init
  reassignment tests at 528-599 (wrong-attrs only — no correct-attrs forge test exists);
  PyOnceLock error-not-cached note at 494-496; all referenced test names/classes exist
  (`TestForgedSourceTextRejected`:867, `test_padded_forge_passes_basicsize_gate_boundary`:941,
  `test_foreign_source_text_basicsize_matches_native_layout`:982,
  `test_metaclass_property_forge_raises_type_error`:1008, `TestSpanToPyobjectCaching`:761,
  `test_control_no_patch_passes`:504).
- Expected error-message substrings check out: the size-mismatch message contains both
  `__basicsize__` and "not a genuine Span allocation" for `type_label = "Span"`
  (`cross_cdylib.rs:331-336`); metaclass-guard message contains "metaclass"
  (`cross_cdylib.rs:305-309`); `check_abi_pair`'s layout message says "ABI layout
  mismatch" so the design's warning against a bare "layout" substring is correct.
- Requirements coverage: the request's directive (TDD subprocess forge test first, then
  `check_instance_layout` on the path; skipping overruled) maps to §4(a) + §2.1 + §3
  threat-model bullet. Scope is proportionate (one call + comments + TODO removal); the
  prior-ADR-immutability handling matches the CLAUDE.md ADR rule.

## design-1

- **Section**: header, "Base commit: `8fd5ecf`" (line 4), plus §1 "(`TODO.md:15-22` ...)".
- **What's wrong**: the declared base commit is inconsistent with the design's own
  citations and with the actual review base (`c03a801`). At `8fd5ecf` the
  `forged-abi-extract-span-uniformity` entry sat at `TODO.md:37-44` (exploration §1 cites
  exactly that); the design's `TODO.md:15-22` cite is only correct at `c03a801`
  (`git diff 8fd5ecf c03a801 -- TODO.md` removes 50 earlier lines). The design mixes
  coordinates from both commits (its `span.rs:290` cite is the exploration's
  8fd5ecf-era number; the real pyclass attr line is 287 at both commits — content
  unaffected since the span.rs diff between the commits touches only lines ~53-60).
- **Why**: `TODO.md` at HEAD (`c03a801`) lines 15-22 = the target entry; exploration.md §1
  says lines 37-44 at its base `8fd5ecf`. Both cannot be true at one commit.
- **Consequence**: an implementer who checks out the declared base `8fd5ecf` to verify or
  branch from it finds the TODO.md line cites wrong and — worse — a TODO.md missing the
  cleanup that `c03a801` already did, risking a merge that resurrects deleted entries.
  Purely a provenance/bookkeeping hazard; no design logic depends on it.
- **Suggested fix**: change line 4 to `Base commit: c03a801` (all other file/line cites
  already match that commit).

## design-2

- **Section**: §4, test (c) "`test_genuine_native_span_accepted_cross_cdylib` ...
  in-process (no forge, no UB risk)" and "succeeds after the gate".
- **What's wrong**: as an in-process pytest, (c) is not guaranteed to exercise the gate at
  all. `FLTK_NATIVE_SPAN_TYPE` in the phase4 cdylib is populated by whichever test first
  crosses a span boundary in that cdylib; several earlier in-file tests do so (e.g.
  `TestSpanToPyobjectCaching.test_repeated_span_reads_from_consumer_cdylib`,
  `tests/test_rust_span.py:772-780`). When (c) runs after them, `get_span_type` is a cache
  hit and the new `check_instance_layout` accept branch never executes in (c) — the test
  then pins only the (genuinely untested-today) extract_span slow path with a canonical
  `Span`, not "succeeds after the gate".
- **Why**: `get_or_try_init` runs the init closure once per process per cdylib
  (`cross_cdylib.rs:462-478`); pytest runs the file's tests in one process.
- **Consequence**: the no-false-rejection property is still covered in aggregate (the
  subprocess `test_control_no_patch_passes` and every earlier phase4 span read would fail
  if the gate rejected the genuine type), so nothing breaks — but test (c)'s stated
  purpose is order-dependent and can silently degrade to a cache-hit test if, e.g., the
  class is placed after other phase4 tests. A future false-rejection regression would
  surface in unrelated-looking tests rather than the one named for it.
- **Suggested fix**: either make (c) a subprocess test (fresh interpreter guarantees the
  gate runs on its boundary crossing), or state in the test docstring that first-init
  gate-accept coverage is deliberately delegated to `test_control_no_patch_passes` and
  (c) pins only the extract_span slow-path accept.

## design-3

- **Section**: §4, "Gates: `uv run --group dev maturin develop` then `uv run pytest ...`;
  full `uv run pytest`; `uv run ruff check . && uv run pyright` (test-file only for
  Python tooling; Rust change is comment + one call)".
- **What's wrong**: the gate list omits the Rust-side lint/test lanes that the project's
  precommit gate enforces. `make check` runs `cargo-clippy`, `cargo-test`,
  `cargo-test-python-features`, `cargo-test-no-python`, `cargo-clippy-no-python`, and
  `check-no-pyo3` (`Makefile:40-51,61`), and this change edits Rust source
  (`cross_cdylib.rs`, `span.rs` doc comments) in a crate covered by those lanes.
- **Why**: Makefile `check-common` step list (`Makefile:40`); CLAUDE.md names `make check`
  as the precommit gate.
- **Consequence**: a clippy lint on the new call/rewritten doc comments (doc-markdown,
  line-length, etc.) or a `--no-default-features` compile issue would be discovered at
  precommit instead of during the implement step, forcing a second revision cycle.
- **Suggested fix**: add `make check` (or at minimum `cargo clippy` over the workspace) to
  the design's gate list.

No other findings. The gate placement rationale (§2.1), the padded-forge/un-padded-subclass
residual analysis (§3), and the blast-radius disclosure (§3) are internally consistent and
source-backed; I found no requirement without design coverage and no unverifiable
substantive claim.
