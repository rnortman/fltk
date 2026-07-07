# Deep test review — step3 M4 (defs/refs/namespace semantics)

Round base: 1ad3141. HEAD: 8966d8ee42840c5f7fbf26090b14ef20eafc28e0.
Design: docs/adr/2026/07/06-fltklsp-lsp-server/step3/design.md

Overall: the new test suites (`test_symbols.py`, `test_features.py` additions,
`test_classify_painter.py` additions, `test_lsp_resolve.py` additions,
`test_engine_analyze.py` additions) are substantive — they assert on concrete field values,
scope structure, resolution outcomes, and precedence, not just "didn't throw." Coverage of the
core extraction/resolution/paint/feature-translation logic is thorough and matches the design's
own test plan closely. The gaps below are concentrated in the rename safety machinery (the one
feature the design itself calls out as needing the strictest scrutiny, §2.6) and a couple of
self-identified edge cases in the design that never got a pinning test.

## test-1: No-op rename (new name == old name) is entirely untested

- File: `fltk/lsp/server.py` (`rename_document`, the `if new_name == _symbol.name:` branch);
  `fltk/lsp/features.py` (`rename_edits` with an empty `occurrences` list).
- Design §2.6 explicitly calls out this behavior: "A no-op rename (new name == old name)
  returns an empty edit." The server code has a dedicated early-return branch for it that
  skips both `_apply_edits` and the verify-reparse round trip entirely.
- No test in `test_server.py` or `test_features.py` ever calls rename/`rename_edits` with
  `new_name` equal to the target symbol's current name. `rename_edits` is only exercised with
  non-empty occurrence lists (`test_rename_edits_versioned_document_changes`,
  `test_rename_edits_plain_changes_fallback`).
- Consequence: a regression that (a) removed the shortcut and always went through
  verify-reparse, (b) crashed on rendering a `TextDocumentEdit`/`changes` payload with zero
  edits, or (c) accidentally applied the no-op branch when names merely *looked* equal after
  case-folding etc. would go unnoticed.
- Fix: add a unit test on `features.rename_edits` with an empty occurrence list (assert a
  well-formed edit with zero `TextEdit`s in both the `document_changes` and `changes` shapes),
  plus a `test_server.py` case that renames a symbol to its own current name and asserts an
  empty edit is returned without triggering a reparse (e.g. via a monkeypatched
  `engine.analyze` spy showing it's not called, or simply asserting `edit.edits == []`
  /`changes[uri] == []`).

## test-2: The rename version-race guard (§2.6) has no test exercising the race it exists for

- File: `fltk/lsp/server.py` (`rename_document`), specifically the
  `state.analyzed_version != version` check and the versioned `documentChanges` payload
  carrying the pre-verify-reparse `version`.
- Design §2.6 identifies this as the reason the feature is "the one M4 feature that edits the
  document" and gets the strictest policy: "the handler awaits the worker twice (analysis,
  then verify-reparse), and a `didChange` can be processed on the loop between those awaits
  ... the server returns `documentChanges` with a ... version, so a conforming client refuses
  a stale edit." This is presented as the load-bearing safety property of the whole feature.
- `test_rename_returns_versioned_document_changes` only exercises the happy path (no
  concurrent edit): it doesn't drive a `didChange` between the two awaits and check that the
  returned edit is still versioned against the *pre-race* version (so a stale-edit-refusing
  client would reject it). `test_rename_on_broken_document_errors` only exercises
  `analysis.error is not None`, never the `state.analyzed_version != version` branch on its
  own (e.g. a rename request whose captured `version` is already stale by the time
  `_ensure_analyzed` returns).
- Consequence: if the version threaded into `rename_edits` were accidentally taken from the
  *post*-reparse state instead of the pre-race captured `version` (or the stale-version guard
  were dropped or inverted), no test would catch it — exactly the corruption class this code
  exists to prevent would ship silently.
- Fix: add a test that opens a document, starts a rename, and before/while it resolves,
  injects a `didChange` bumping the version (pytest-lsp's client can send the notification
  concurrently, or the analyze/executor call can be monkeypatched to yield control); assert
  the returned edit's version still matches the version captured at the start of the rename
  request. Separately, a narrower unit test could stub `_ensure_analyzed`/`state` to return a
  mismatched `analyzed_version` and assert `rename_document` raises rather than proceeding.

## test-3: RecursionError-during-extraction is asserted in prose but not exercised

- File: `fltk/lsp/engine.py` (`analyze()` success path — `symbols.extract(...)` runs inside
  the same `try` as `parse_text`/`classify`).
- The implementation log states: "The `RecursionError` catch already wraps the whole success
  path and now also covers extraction," and design §4.6 relies on this to guarantee `symbols`
  degrades to `None` alongside `tree`/`tokens` on any recursion blowup.
- `test_analyze_recursion_error_reports_offset_none` (`test_engine_analyze.py`) monkeypatches
  `engine_module.plumbing.parse_text` to raise `RecursionError` — the failure happens *before*
  `symbols.extract` is ever reached, so it only proves the guard catches parse-time recursion,
  not extraction-time recursion. `symbols.extract`'s `_walk` is itself unbounded recursive over
  CST depth, which is exactly the kind of function a very deeply nested document could blow the
  stack on.
- Consequence: if a future change moved `symbols.extract` outside the `try`, or if extraction's
  own recursion has a different failure mode (e.g. it raises `RecursionError` at a point the
  `try` doesn't cover, or the exception surfaces as a different error class), nothing would
  catch the regression.
- Fix: add a test that monkeypatches `symbols.extract` (or `fltk.lsp.engine.symbols.extract`)
  to raise `RecursionError` and asserts `analyze()` returns the same structured
  `ParseErrorInfo(offset=None, ...)` shape as the parse-time case, with `tree`/`tokens`/
  `symbols` all `None`.

## test-4: Identical-span nested namespace chain (§4.3) has no pinning test

- File: `fltk/lsp/symbols.py` (`_walk`'s scope-opening check:
  `if rule.name in resolved.namespace_rules: child_scope = Scope(...)`).
- Design §4.3 explicitly calls out and reasons through this shape: "Identical-span parent/child
  namespace chains (rule `A := b` where both are namespace rules) nest inner-inside-outer by
  walk order; resolution semantics are unaffected because the outward walk visits both." This
  is presented as a deliberately-considered edge case, which is exactly the kind of claim that
  should carry a regression test.
- `test_symbols.py`'s namespace tests (`test_namespace_opens_a_nested_scope`,
  `test_namespace_name_hoists_and_members_stay_inside`, etc.) all use the `_MOD_GRAMMAR`'s
  `block` rule, whose namespace span differs from its parent/child rule spans — none construct
  a grammar where a namespace rule immediately wraps another namespace rule with an identical
  span (e.g. `outer := inner ;` where both `outer` and `inner` are namespace rules with no
  other content), so two scopes actually get created rather than one, and resolution still
  walks correctly from an offset inside to both enclosing scopes.
- Consequence: if the scope-opening check were changed to skip creating a scope when the
  child's span equals the parent's (a plausible "optimization" someone might make believing it
  redundant), nothing would fail today, silently changing shadowing semantics for chained
  single-child namespace rules.
- Fix: add a `test_symbols.py` case with a grammar like `outer := inner ;` / `inner := name:word
  ;` where both `outer` and `inner` are namespace rules (config: `rule outer { namespace; }`,
  `rule inner { namespace; def name: variable; }` or similar), assert `table.root.children`
  has one scope (outer) containing exactly one child scope (inner) with matching spans, and
  that a reference inside `inner` resolves through both scopes outward.

## Everything else: solid

- `test_symbols.py` covers symbol-field correctness (label/rule/literal anchors), union-anchor
  collapsing, repeated-item multiplicity, def-beats-ref, the full namespace hoist story
  (member-stays-inside, self-reference, hoisted-name-visible-outside), forward references,
  shadowing, unresolved-stays-None, duplicate-def document-order resolution, dotted-prefix
  kind matching (both directions), wildcard, kind-lists, and occurrence dedup over a genuine
  single-child-chain overlap — all asserting on concrete names/spans/resolution targets, not
  vacuous smoke checks.
- `test_classify_painter.py`'s ref-paint additions cover the real precedence matrix (scope
  beats ref, deeper-beats-shallower both directions via a purpose-built nesting grammar,
  `none` occlusion, out-of-legend/unresolved fallthrough) plus an explicit regression pin for
  the no-`symbol_table` path being byte-identical to round 2.
- `test_features.py`'s new functions are tested directly against hand-built `SymbolTable`s
  with the specific tricky shape called out in the design (name-child-trails-members range
  sort) and equal-range siblings — good, since this is exactly the kind of nesting-stack bug
  that a naive implementation gets wrong.
- `test_lsp_resolve.py`'s replacement of `test_ref_and_namespace_are_inert` correctly asserts
  the new tables' contents (kinds, tiers, union anchors, cross-block namespace accumulation)
  rather than just checking non-emptiness.
- `test_server.py`'s new integration tests exercise real encoding concerns (utf-16 vs utf-32
  over astral text for definition), both document-symbol capability branches, and the
  happy/error paths for rename (broken doc, parse-breaking new name) at the protocol level —
  good breadth for a pytest-lsp suite; the gaps above are specifically about the *unhappy*
  paths in the rename safety net that the design flags as the reason the feature needed a
  stricter policy in the first place.
