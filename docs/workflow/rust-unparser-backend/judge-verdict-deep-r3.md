# Judge verdict — deep review (rust-unparser-backend)

Phase: deep. Base d622ff7..HEAD 342fabb (fix commit; reviewers reviewed e6a682c, fixes landed in HEAD). Round 1.
Notes: 7 reviewer files; 9 findings (security + efficiency: no findings).

## Added TODOs walk

No TODO dispositions in this round. The diff (e6a682c..342fabb) adds no `TODO(slug)`
comments; design open question 1 (`TODO(unparser-deep-tree)`) was settled by the user
("leaving resolve_spacing_specs recursive is fine for now") and is not part of this diff.
Nothing to walk.

## Other findings walk

### correctness-1 — Fixed
Claim: `_doc_to_rust_expr` emitted `Doc::text(...)`/`Doc::concat(...)`; `text`/`concat`
are free module functions, not associated fns on `Doc` (only `impl Doc` is `Drop`), so
`Doc::text`/`Doc::concat` fail to resolve (E0599) → any Text/Concat separator (e.g.
`join … by ","`) emits uncompilable Rust + breaks cross-backend parity. Severity: blocker
(correctness; latent until a join-separator fixture lands, but real).
Evidence: HEAD `gsm2unparser_rs.py:345,348` now emit `fltk_unparser_core::text("…")` and
`fltk_unparser_core::concat(vec![…])`. Verified the targets resolve: `pub fn text(s: impl
Into<String>) -> Doc` (doc.rs:134) and `pub fn concat(docs: Vec<Doc>) -> Doc` (doc.rs:200)
are free functions, both `pub use`-re-exported at crate root (lib.rs:22-24). Crate-qualified
path resolves regardless of the header `use` set; `&str` literal satisfies `impl Into<String>`;
`vec![Doc…]` satisfies `Vec<Doc>`. Three string-asserting tests updated and pass.
Assessment: fix addresses the E0599 at both named lines; resolution confirmed against the
crate. Responder chose crate-qualified emission over the reviewer's "add to `use` + emit
unqualified" suggestion — equally valid, and avoids unused-import warnings in separator-free
files. Accept.

### errhandling-3 — Fixed
Claim: JOIN_BEGIN `_doc_to_rust_expr(op.separator)` ValueError propagates without naming the
offending rule. Severity: low (diagnostic only).
Evidence: HEAD `gsm2unparser_rs.py:203-207` wraps the call in `try/except ValueError`,
re-raising `f"Rule {rule_name!r} JOIN_BEGIN separator uses unsupported Doc type: {exc}"`
with `from exc`. `test_join_begin_unsupported_separator_reports_rule_context` covers it (passes).
Purely additive — both backends still reject the same configs with a ValueError, so no parity
change. Accept.

### test-1 — Fixed
Claim: rule-level JOIN_BEGIN/JOIN_END path and its `RuntimeError` None-separator guard untested.
Severity: should-fix (only explicit raise in the increment was invisible).
Evidence: `test_rule_level_join_anchor_emits_push_pop` asserts
`push_join(fltk_unparser_core::text(","))` + `pop_join()` (matches rule-entry emission at
:208/:228); `test_join_begin_without_separator_raises` asserts the `RuntimeError` at :200-202.
Both pass. Accept.

### test-2 — Fixed
Claim: empty-alternative pass-through branch in `_gen_alternative_body` untested.
Severity: should-fix (most-divergent branch).
Evidence: `test_empty_alternative_body_is_passthrough` calls `_gen_alternative_body("r","R",0,
gsm.Items(items=[], sep_after=[]))` — signature matches (:253) — and asserts the
`Some(UnparseResult::new(acc, pos))` return with no `let mut pos`/`let mut acc` preamble,
matching the branch at :269-273. Passes. Accept.

### test-3 — Fixed
Claim: NEST_BEGIN `op.indent or 1` fallback (indent=None) untested. Severity: low.
Evidence: `test_nest_begin_without_indent_defaults_to_one` constructs
`FormatOperation(NEST_BEGIN)` and asserts `push_nest(1)`, exercising the `op.indent or 1`
fallback at :198. Passes. Accept.

### reuse-1 — Fixed
Claim: `_class_name` reached through `self._cst._py_gen.class_name_for_rule_node` instead of
the public `class_name_for_rule` wrapper; hardcodes the private delegation path. Severity: low
(maintainability).
Evidence: HEAD `gsm2unparser_rs.py:141` now calls `self._cst.class_name_for_rule(rule_name)`;
`class_name_for_rule` exists as a public wrapper at `gsm2tree_rs.py:779` delegating to the same
`class_name_for_rule_node`, so output is byte-identical. Accept.

### quality-1 — Fixed (in-scope) + Won't-Do (out-of-scope sub-part)
Claim: same bypass as reuse-1, plus a request to also fix the pre-existing
`RustParserGenerator._class_name` (gsm2parser_rs.py:231) and its use at :171. Consequence:
workaround propagates across generator classes. Severity: low.
Evidence: the new-code part is fixed (same change as reuse-1), so propagation into this third
callsite is stopped. Responder declined the parser-backend cleanup as out-of-scope: those lines
are pre-existing parser-backend code untouched by this design (§2 "the parser backend… is not
touched"), and the copy works — it bypasses the wrapper but is correctness-neutral.
Assessment: declining unrelated pre-existing cleanup is a legitimate scope boundary; the
reviewer's actual consequence (further propagation) is addressed for the subject code, and the
pre-existing copy causes no active harm. Accept.

### errhandling-1 — Won't-Do
Claim: RULE_START/RULE_END `if/elif/elif` chains have no `else`, so an unexpected OperationType
(e.g. SPACING misrouted to a rule-start anchor) is silently dropped — wrong output, no
diagnostic. Reviewer concedes this is unreachable via the normal `.fltkfmt` path; only reachable
via hand-constructed FormatterConfig. Severity: low.
Rationale (Won't-Do): the Python backend has the byte-identical no-`else` chains
(`gsm2unparser.py:222-243`) and drops unexpected types identically; design §2.2 forbids
Rust-only divergence, and CLAUDE.md mandates cross-backend behavioral equivalence. A Rust-only
`raise` would make the same config error in Rust but succeed-with-silent-drop in Python.
Evidence: verified `gsm2unparser.py:222-243` — GROUP_BEGIN/NEST_BEGIN/JOIN_BEGIN (and the
RULE_END pop chain) with no `else`. Parity claim holds.
Assessment: the fix would itself create a forbidden cross-backend divergence (active harm under
the project's equivalence invariant); the correct remedy is a deliberate both-backends change,
explicitly out of scope. Finding is a low-severity defensive nit reachable only off the normal
path. Won't-Do meets the bar. Accept.

### errhandling-2 — Won't-Do
Claim: `op.indent or 1` maps `indent=0` to `push_nest(1)` — wrong value, no diagnostic, for a
direct `FormatOperation(indent=0)`. Severity: low (`nest(0)` is semantically degenerate;
unreachable via normal `.fltkfmt`).
Rationale (Won't-Do): Python uses the identical `op.indent or 1` (`gsm2unparser.py:233`);
changing only Rust would make `nest(0)` emit `push_nest(0)` in Rust vs `push_nest(1)` in Python
from one input — forbidden divergence.
Evidence: verified `gsm2unparser.py:233` uses `op.indent or 1`. Parity claim holds.
Assessment: same parity reasoning as errhandling-1; honoring `indent=0` is a both-backends
change, out of scope. Accept.

## Disputed items

None.

## Approved

9 findings: 6 Fixed verified (correctness-1, errhandling-3, test-1, test-2, test-3, reuse-1),
1 Fixed-in-scope with sound out-of-scope decline (quality-1), 2 Won't-Do sound (errhandling-1,
errhandling-2). Generator test suite: 27 passed.

---

## Verdict: APPROVED

All dispositions acceptable. Fixes verified against HEAD source and the runtime crate;
both Won't-Do parity arguments confirmed against the Python backend at the cited lines;
generator tests pass.
