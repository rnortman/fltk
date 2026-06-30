# Judge verdict — design gate (user decision #3)

Phase: design. Doc: `docs/adr/2026/06/30-codegen-protocol-pyi-outputs/design.md`. Round 1.
Inputs: `notes-design-user.md` item 3 (authoritative new decision); `dispositions-design-user2.md` (one
disposition: user-decision-3, Fixed).

Adjudication scope: does the revised design faithfully incorporate the new decision #3 (dogfood the
generated `__init__.pyi` via the generator/CLI path, regenerate the in-tree markers, leave
`_native/__init__.pyi` untouched) and stay internally consistent — with code as ground truth.

## Other findings walk

### user-decision-3 — Fixed

Decision (verbatim, item 3): dogfood the generated `__init__.pyi` rather than hand-authoring the in-tree
markers; route marker generation through the generator/CLI path (emit `__init__.pyi` alongside the
`cst.pyi`/`unparser.pyi` it already produces); have the Bazel rule use that same path instead of
`ctx.actions.write`; content is generator-derived (extension name + submodule list, informative
comments preserved); `make gencode` regenerates the two in-tree markers; `_native/__init__.pyi` out of
scope. Refines decision #1; supersedes the prior §2.7 "hand-authored / Bazel-only" plan.

Disposition: Fixed — design revised across header Change-2 bullet, §2.2 (new marker subsection), §2.5,
§2.6, §2.7, §3, §4, §5, §6.

Faithfulness — all seven sub-asks incorporated:
- Dogfood / not hand-authored → §2.7 retitled "dogfood the in-tree stub-package markers"; `make gencode`
  regenerates both. ✓
- Route through generator/CLI alongside existing `.pyi` → §2.2 adds `--init-pyi-output` /
  `--extension-name` / `--submodules` to *both* `gen-rust-cst` (writes `cst.pyi`) and `gen-rust-unparser`
  (writes `unparser.pyi`). ✓
- Bazel reuses that path, not `ctx.actions.write` → §2.5: same `gen-rust-cst` action gains
  `--init-pyi-output {name}/__init__.pyi ...` and declares `{name}/__init__.pyi` as a third output. ✓
- Generator-derived content → new `render_stub_package_init(extension_name, submodules)` in
  `gsm2lib_rs.py`, comment-only, names extension + submodules, preserves the informative explanation. ✓
- `make gencode` regenerates the two in-tree markers → §2.7 (fegen via `gen-rust-cst`; fixture via
  `gen-rust-unparser`). ✓
- Supersession recorded → header Change-2 bullet, §2.7, §6 item 1 (updated) + item 3 (new). ✓
- `_native/__init__.pyi` untouched → §2.7 final bullet, §6 item 3, §4. ✓

Source verification of the design's grounding claims:
- Markers are comment-only: `fltk/_stubs/fegen_rust_cst/__init__.pyi` (4 comment lines),
  `fltk/_stubs/rust_parser_fixture/__init__.pyi` (6 comment lines). Generator-rendered comment text is
  the correct mechanism; no symbol/annotation surface (CLAUDE.md constraint satisfied).
- fegen marker staleness is real: marker line 4 says "only submodules cst and parser" but
  `crates/fegen-rust/src/lib.rs:23-25` registers `cst`, `parser`, **and** `unparser`; the regenerated
  `--submodules cst,parser,unparser` fixes it.
- `gsm2lib_rs.py` is the right home: it owns `_validate_rust_ident` (`:19`), `Submodule` (`:27`),
  `LibSpec` (`:54`), and its docstring states it "does not consume grammar rules" — matching the
  marker's grammar-independent inputs.
- The `rust_parser_fixture` routing wrinkle is real: the fixture's `gen-rust-cst` Makefile call passes no
  `--protocol-module` (so no `cst.pyi`), while its `gen-rust-unparser` call passes
  `--protocol-module tests.rust_parser_fixture_cst_protocol --pyi-output .../unparser.pyi`; making the
  marker independent of `--protocol-module` is what lets it ride the unparser invocation. One invocation
  per package avoids the overwrite the §4 edge case calls out.
- `_native/__init__.pyi` is a substantive hand-written stub (`LineColPos`/`SourceText`/`Span`/
  `UnknownSpan`), correctly left out of scope.
- Test stays green: `tests/test_rust_unparser_pyi.py::test_committed_stub_artifacts_exist` asserts the
  marker file is *present* and asserts *content* of `unparser.pyi` (not the `__init__.pyi`), so the
  comment-text change keeps it green; its docstring already ties a missing marker to `make gencode` not
  being run.

Internal consistency:
- `rust.bzl` today has no `ctx.actions.write`, no `__init__.pyi`, and no `--protocol*`/`--pyi*` wiring
  (only `cst.rs`/`parser.rs` declared at `:116-117`, returned at `:149`). The design's "replacing
  `ctx.actions.write`" therefore supersedes the *prior design's* proposed approach, not existing code —
  and every one of the design's `ctx.actions.write` references (lines 228, 289, 405, 550, 570) is in the
  "**not** this / supersedes prior plan" framing. No leftover contradiction. Cited `rust.bzl` line ranges
  (116-117, 120-131, 149, 151-175) are accurate.
- Submodule lists are correctly parameterized per invocation, not contradictory: Bazel rule emits
  `cst,parser` (the only submodules `generate_rust_parser` produces); the in-tree fegen marker emits
  `cst,parser,unparser` (matches lib.rs, since the fegen extension is additionally built with an unparser
  via a separate call); the fixture marker emits the 6-tuple
  `cst,parser,unparser,unparser_default,collision_cst,collision_parser`, exactly matching the committed
  marker's body. Dogfooding holds at the shared renderer level; the submodule list is an input, so
  differing lists across invocations is correct, not a drift.
- Gating the Bazel marker on `protocol_module` being non-empty is coherent: the marker rides the same
  action that emits `cst.pyi`, and a marker with no accompanying `.pyi` would complete an empty stub
  package — the §2.5 table (`""/False` → none; `set/False` → `cst.pyi`+`__init__.pyi`) reflects this.
- Marker independence from `--protocol-module` (§2.2) is consistent with the fixture routing and with the
  validation design (`--init-pyi-output` requires `--extension-name`+`--submodules`; identifier checks),
  which mirrors the existing up-front `--pyi-output requires --protocol-module` /
  `_validate_protocol_module` pattern in `genparser.py`.

Assessment: the design incorporates every clause of decision #3 and stays internally consistent; all
grounding claims check out against source. The supersession of the prior §2.7/§6 plan is explicit and
recorded in the header, §2.7, and §6. CLAUDE.md's "comment text only, no symbol/annotation change"
constraint is satisfied. Fixed verified — accept.

## Approved

1 disposition: user-decision-3 (Fixed) verified — design faithfully and consistently incorporates the
new decision.

---

## Verdict: APPROVED

The revised design faithfully incorporates user decision #3 and remains internally consistent; every
grounding claim is source-backed.
