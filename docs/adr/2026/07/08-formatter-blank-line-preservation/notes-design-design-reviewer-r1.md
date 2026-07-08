# Design review notes — formatter blank-line preservation (r1)

Design: `docs/adr/2026/07/08-formatter-blank-line-preservation/design.md`
Reviewer: design-reviewer. All file:line citations below verified against the checkout at 1d1f1b6.

Verification summary: every citation in §1 checks out exactly — the clobbering in
`_process_trivia_preserve_statement` (`fltk/unparse/fmt_config.py:508`) vs. the in-place mutation
in `_process_preserve_blanks_statement` (`:524-527`), `TriviaConfig.preserve_blanks: int = 0`
(`:59`), `gear.fltkfmt:8-9` order (and it is the only committed `.fltkfmt` with that order),
the generation-time-constant reads (`gsm2unparser.py:1166-1171`, `:1351-1359`;
`gsm2unparser_rs.py:1553-1562`, branch call sites `:1254`, `:1348`), `_mutate_after_sep`
larger-blank-wins (`resolve_specs.py:368-374`), the existing-test coverage analysis
(`test_unparser.py:994-999`, `:1043`, `:1087`, `:1128`; `test_rust_unparser_generator.py:1819`,
`:1963`), and the minimal repro (re-executed; reproduces exactly). The config bug is real and the
proposed one-line fix for it is correct as far as it goes. However:

## design-1: The fix is incomplete — the pinned failing test stays red after implementing the design exactly

**Section/quote:** §2 "once the config is correct, the already-tested `preserve_blanks > 0`
codegen branches ... emit the blank-line detection as designed"; §5 item 6
"`test_formatting_preserves_blank_lines_between_items` — already committed and failing; becomes
the passing integration regression test."

**What's wrong:** I applied the design's exact fix (mutate-in-place in
`_process_trivia_preserve_statement`) to this checkout and ran
`uv run --extra lsp pytest fltk/lsp/test_gear_demo.py -q`:
**`test_formatting_preserves_blank_lines_between_items` still fails** (1 failed, 9 passed),
on its first assertion (`"\n\nshape Wheel {"` absent). The import path was verified to resolve
to the source tree (`fltk.unparse.fmt_config.__file__` → the edited file), and the parsed config
was verified as `TriviaConfig(preserve_node_names={'LineComment'}, preserve_blanks=1)` during the
run. (The temporary edit was reverted after testing; the tree is back to its prior state.)

**Why (root cause of the residual failure, verified by execution):** with the fix applied, the
generated gear unparser *does* contain the blank-line branch — the dumped
`unparse_use_stmt__alt0` ends with
`elif self._count_newlines_in_trivia(trivia_node) >= 2: ... SeparatorSpec(spacing=HARDLINE_BLANK, ...)`.
But at runtime `_count_newlines_in_trivia` returns **0** for gear's trivia. The generated method
(from `_gen_count_newlines_in_trivia_method`, `gsm2unparser.py:970-1063`) only counts newlines in
**direct span children** of the `Trivia` node:

```python
if fltk.unparse.pyrt.is_span(trivia.children[idx][1]):
    count = count + self._count_newlines(trivia.children[idx][1])
```

Gear defines its own trivia rule with a *named* whitespace rule
(`examples/gear/gear.fltkg:45-46`: `_trivia := ( ws | line_comment )+ ;` /
`ws := chars:/\s+/ ;`), so the inter-item blank line is a `Ws` **node** child of `Trivia`
(verified on the parsed sample: `Trivia.children == [(Label.WS, Ws(... Span(102,104) "\n\n"))]`),
not a direct span — `is_span` is false, count is 0, and the gap falls to the default-`NBSP` arm.
Every existing `preserve_blanks` test passes because it uses `fegen.fltkg`, whose trivia rule
(`fltk/fegen/fegen.fltkg:19`) captures whitespace via its WS separators as **unlabeled direct
`Span` children** (verified on a parsed fegen snippet: all `Trivia.children` are `(None, Span)`).
The exploration explicitly flagged this as unverified ("Whether this generalizes to grammars
where ... was not checked further — out of scope"), and its end-to-end Doc-tail probe was run
only with the *buggy* config; the design extrapolated the rest of the chain without running it.

**Consequence:** the primary acceptance criterion — the pinned test
`fltk/lsp/test_gear_demo.py::test_formatting_preserves_blank_lines_between_items` passing — is
not met by this design. An implementer following it exactly ships a half-fix: the config layer is
corrected, the codegen branches appear, and the gear formatter still collapses every blank line.

**Suggested fix:** the design needs a second component: make the generated
`_count_newlines_in_trivia` count newlines in trivia children that are nodes wrapping whitespace
spans (e.g. sum over span descendants of non-preserved trivia children), not only direct spans —
in **both** generators (`gsm2unparser.py:970-1063` and the Rust mirror,
`gsm2unparser_rs.py:1501-1520`, whose emitted method matches only `cst::TriviaChild::Span` per
`tests/test_rust_unparser_generator.py:1990-2004`). Care is needed not to count newlines inside
*preserved/comment* children (gear's `line_comment` ends with `nl:"\n"`, `gear.fltkg:47` —
naive full recursion would count comment terminators as blank-line evidence). Whatever the exact
shape, the design must state it and the fixed pipeline must be run end-to-end before sign-off.

## design-2: Test plan has no coverage for the nested-trivia (custom `ws`-rule) structure in either backend

**Section/quote:** §5 — engine-level tests 1-4 and Rust test 5.

**What's wrong:** every non-gear test in the plan runs on fegen or on the existing Rust-test toy
grammars, all of which produce direct-`Span` trivia children (see design-1). The only test
exercising node-wrapped whitespace (`Trivia → Ws → Span`) is the gear integration test. So even
after the full bug is fixed, nothing at the engine/generator level pins newline counting over
nested trivia children — for Python or Rust. The Rust mirror test proposed in §5 item 5 would go
green from the config fix alone while the Rust backend still has the nested-trivia counting gap,
i.e. it does not actually pin what §3 claims it pins ("that the shared-config fix reaches the
Rust generator" is true, but cross-backend *behavioral* equivalence for gear-shaped grammars is
untested).

**Consequence:** a regression (or a Python-only fix) in nested-trivia newline counting would pass
the entire engine suite and only surface in the gear demo test — and nothing at all would catch a
Rust-side divergence, contrary to the stated cross-backend equivalence goal.

**Suggested fix:** add engine-level tests (both `test_unparser.py`-style rendering and a Rust
generated-source/unit test) using a small grammar with a custom trivia rule whose whitespace is a
named rule (`_trivia := (ws | comment)+ ; ws := chars:/\s+/ ;`), asserting blank lines survive
with `preserve_blanks: 1` from parsed config text.

## design-3: §2/§3/§4 claims are contingent on the fix being config-only, which design-1 invalidates

**Section/quote:** §2 "**`fltk/unparse/gsm2unparser.py` / `gsm2unparser_rs.py` are untouched.**";
§3 "Fixing the shared layer therefore fixes both backends identically and by construction cannot
introduce divergence"; §6 "Open questions: None."

**What's wrong:** once the fix must touch the generated `_count_newlines_in_trivia` in both
generators (design-1), these statements are internally inconsistent with the delivered outcome:
the generators are *not* untouched, the "by construction" divergence argument no longer covers
the whole fix, and §4's impact analysis ("changes only which spacing branches get emitted ... per
the config") understates the behavioral surface — regenerated formatters for out-of-tree grammars
with custom trivia rules will change blank-line output even when their `.fltkfmt` never had the
clobbering statement order. That is still a bug fix delivering documented semantics, but §4
currently argues only the statement-order case.

**Consequence:** the ADR would record a decision rationale ("shared config layer only; generators
untouched by construction") that is false for the change actually required, and the out-of-tree
impact statement would omit an affected consumer class (custom-trivia-rule grammars with
`preserve_blanks > 0` and the non-clobbering order).

**Suggested fix:** rework §2-§4 around the two-part root cause: (a) config-layer clobbering
(order-dependent), (b) generated newline counting blind to node-wrapped whitespace
(grammar-shape-dependent); restate the cross-backend argument as "shared config layer + mirrored
generator change pinned by mirrored tests", and extend §4 to cover consumer class (b).
