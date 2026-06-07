# Correctness review — interim (rust-cst-native-span)

Base 6fd32e7 .. HEAD 767315f. Single pass. Mandate: does committed code do what it appears to do.
Scope: committed code only. Known/excluded gaps per prompt (do NOT relitigate): §2.5 parser
source-bearing-span migration (the `TypeError: expected fltk._native.Span, got Span` parse-path
regression), §2.6 fltk2gsm, §2.7 protocol widening, remaining §2.8 regeneration.

Concise. Precise. Complete. Unambiguous. No padding. (Repeated per authoring directive.)

## Build / test state observed

- `maturin develop` (root + both fixture crates) builds clean.
- Targeted suites pass: test_fegen_rust_cst, test_gsm2tree_rs, test_rust_cst_poc, test_span_protocol.
- Full suite: 28 failed + 9 errors. Root causes, all out of correctness scope:
  - Parse-path failures (`TypeError: expected fltk._native.Span, got Span`): the KNOWN §2.5 gap
    (parser still emits `terminalsrc.Span` into the now-strict native setter). Excluded by prompt.
  - test_phase4_rust_fixture AC2/AC5/AC7 `AttributeError: ... has no attribute 'Entry'/'Config'`:
    committed `tests/rust_cst_fixture/src/cst.rs` exposes only PoC-grammar classes
    (`Identifier`, `Items`, `Trivia`) — it was NOT regenerated from `phase4_roundtrip.fltkg`
    (expects `Config`/`Entry`/`Operator`/`Literal`). This is the un-started §2.8 fixture
    regeneration; not a generator logic defect. Verified by reading the committed cst.rs structs.
  These are gap artifacts, not new logic bugs introduced by the committed generator changes.

## Findings

### correctness-1 — generic `append`/`extend` silently drop a label on no-label nodes
File: fltk/fegen/gsm2tree_rs.py:589-607 (`_label_from_pyobject_match`), used by `_generic_append`
(569-587) and `_generic_extend` (609-636).

What: For a rule whose node has no labels, the label-conversion match is
`None => None, Some(_) => None  // no labels defined for this node`. A non-None Python label
argument is silently discarded; the child is stored with label `None`.

Why: The Python backend's `append(self, child, label=None)` stores the tuple `(label, child)`
verbatim (gsm2tree.py base, append_fn `self.children.append((label, child))`). The Rust path
discards a supplied label instead of storing or rejecting it. Cross-backend divergence on the
Python-visible `children` shape.

Consequence: Only reachable via consumer misuse — calling generic `append`/`extend` with a label
on a node type that defines no labels. In-tree generated parsers never do this (they use typed
`append_<label>` for labeled children and `label=None` otherwise; grep of fltk_parser.py confirms).
So no in-tree breakage. For an out-of-tree consumer doing this, the Python backend records the
label and the Rust backend silently loses it — a silent behavioral mismatch rather than a loud
error. Same for non-no-label nodes when an unrecognized/cross-cdylib label object is passed:
`extract::<{Label}>()` fails → silently `None` (gsm2tree_rs.py:600-604), again dropping the label
rather than raising. Low confidence on materiality given the misuse precondition; flagged because
the failure mode is silent.

Suggested fix: on a `Some(_)` label that cannot be converted to the node's native label enum (or
on any label for a no-label node), raise `TypeError` instead of coercing to `None` — matching the
loud-failure stance the design takes elsewhere (§3 "fail loudly, not store untyped").

### correctness-2 — `child_<label>` / `maybe_<label>` error message undercounts when >2 matches
File: fltk/fegen/gsm2tree_rs.py:749-813 (`_per_label_methods`, child_/maybe_ arms).

What: The match loop increments `count` and `break`s on the second match, so `count` caps at 2.
With 3+ matching children the error reads "Expected one <label> child but have 2" (child_) /
"...have at least 2" (maybe_) regardless of the true count.

Why: `count == 1 { found = ... } else { break; }` exits after the second hit. The Python backend
builds the full list (`children = list(self.children_<label>())`) and reports the exact `n`
(gsm2tree.py base, child_fn / maybe_fn). maybe_ already phrases it as "at least 2" so it is
accurate; child_ says a flat "2" which is wrong for 3+.

Consequence: The error is still raised correctly (control flow / which-branch is correct — count is
never 1 when there are 2+), so behavior (raise vs not) matches the Python backend. Only the
diagnostic integer in `child_<label>`'s message is inaccurate for 3+ matches. No functional
divergence. Cosmetic-adjacent; included because it is a copy-of-Python-semantics deviation in a
generated public-API error string.

Suggested fix: drop the early `break` and count all matches (or compute count before formatting),
so the message reports the true count as the Python backend does. Minor cost: full scan instead of
early exit.

## Verified clean (traced, no defect)

- `extend_children` (gsm2tree_rs.py:638-653) + gsm2parser.py:497,715 rewrite: parser now routes
  inline-to-parent mutation through the node method (`extend_children(other=...)`), not the
  rebuilt-list getter. Grep confirms NO remaining `.children.extend/.append` getter-mutation in any
  regenerated parser (fltk_parser, bootstrap_parser, trivia, unparse parsers). The
  rebuild-on-each-call `children` getter is therefore never used as a mutation handle in-tree. PyRef
  same-type extraction is sound: inline_to_parent merges a synthesized sub-rule result of the same
  node type into the parent (gsm2parser.py:454-505); no cross-type extend_children in-tree.
- Native `PartialEq`: node `eq` compares `span == other.span && children == other.children`
  (gsm2tree_rs.py:431-435); child enum `PartialEq` is structural with `_ => false` for variant
  mismatch (347-357); `Span` PartialEq is `(start,end)`-only (span.rs:80-84), so the sourceless
  sentinel equals a source-bearing span at equal offsets — matches the documented value semantics.
  `__eq__` returns `NotImplemented` for foreign types (817-829) → Python falls back to `False`, no
  spurious error; cross-backend nodes compare unequal not raise.
- `extract_span` fast/slow path (gsm2tree_rs.py:151-179): fast `extract::<Span>()` for same-cdylib;
  slow path isinstance-checks `fltk._native.Span` then `downcast_unchecked`. Sound given both
  cdylibs link the same `fltk-cst-core` Span layout (design §2.1 constraint). Non-Span → TypeError.
- `Span::text` / `text_or_raise` bounds + char-boundary + inverted-range + negative-index guards
  (span.rs:176-236): correct half-open `[start,end)` handling; `text` returns None and
  `text_or_raise` raises ValueError on the same conditions. `len()` clamps negative/ sentinel to 0;
  `is_empty` is `start >= end`. No off-by-one: `end > src.len()` (not `>=`) is correct for half-open.
- `coerce_source` (span.rs:141-148): `Arc::ptr_eq` mismatch → error; else prefers self's source else
  other's. merge/intersect use it; intersect returns `unknown()` when `s >= e` (disjoint). Correct.
- terminalsrc.SourceText / with_source (terminalsrc.py): `with_source` accepts `str | SourceText`,
  extracts `_text` for SourceText, raises TypeError otherwise — additive, backward compatible; the
  base `with_source(str)` callers still work. Selector (span.py) re-exports SourceText on both
  backends. test_span_protocol passes.
- `_new_method` native sentinel default via `Span::unknown()`; `UNKNOWN_SPAN_CACHE`/GILOnceCell for
  span default removed as designed. (`FLTK_NATIVE_SPAN_TYPE` GILOnceCell remains — that is the
  cross-cdylib type handle for the setter/getter, a different mechanism, intended.)
