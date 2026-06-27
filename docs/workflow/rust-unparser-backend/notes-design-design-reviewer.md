# Design review: Rust Unparser Backend

Scope note: I verified the design's load-bearing claims against source. The factual
grounding is strong — cited line numbers, API signatures (`children()`@1143,
`span()`@1130, `shared()`@1207, `Py{CN}`@1195, child enum@796, `Span::text()->Option<String>`
@span.rs:421, the static naming helpers, `RustCstGenerator.__init__` doing
`classify_trivia_rules(add_trivia_rule_to_grammar(...))`@gsm2tree_rs.py:176,
`plumbing.parse_format_config_file`@plumbing.py:234, `_rust_str_lit`@gsm2parser_rs.py:59,
`_CST_MOD_PATH_RE`@genparser.py:370, the fixture grammar uses only required-suppressed
*literals* so a Python unparser baseline is generable) all check out. The three-stage
pipeline requirement (Doc / resolve / render in Rust, not direct string emission) is
honored. Findings below are the substantive gaps.

## design-1: PyO3 `unparse_{rule}` returns a rendered `str`, but the Python backend's `Unparser.unparse_{rule}` returns `UnparseResult` — undeclared public-API call-site divergence

Section: §2.3 (PyO3 wrapper, `fn unparse_{rule}(...) -> PyResult<Option<String>>`) and §2.4
("Parity ... is at the rendered-string level"), vs open question 2.

What's wrong: The Python generated `Unparser.unparse_{rule}(self, node) -> Optional[UnparseResult]`
(gsm2unparser.py:198-210, return type `maybe_unparse_result_type`) does NOT render. The
caller separately runs `resolve_spacing_specs(...)` + `Renderer.render(...)`
(plumbing.unparse_cst@plumbing.py:302-333, render_doc@:336). The design's Rust PyO3
`unparse_{rule}(node, max_width, indent_width)` runs the *entire* pipeline and returns a
`str`. So the same-named public method has a different return type and a different
contract (one-shot string vs. Doc-bearing result the caller must render).

Why / grounding: CLAUDE.md states the Rust backend's explicit goal is "a near-drop-in
replacement ... consumers may need to update import statements, but must not be forced to
edit their ... call sites wholesale," and exploration §"Out-of-Tree Consumer API" lists
`unparse_{rule_name}(node)` as public API. The design itself signals this is unsettled:
§2.3/§2.4 present string-return as the design, while open question 2 asks "is a
string-returning surface sufficient?" — i.e. the same decision is simultaneously made and
left open.

Consequence: An out-of-tree Python consumer migrating from the Python unparser to the Rust
unparser cannot keep their call sites: code that today does `r = unp.unparse_x(node);
doc = resolve_spacing_specs(r.accumulator.doc); render_doc(doc, cfg)` must be rewritten to
`unp.unparse_x(node, max_width, indent_width)`. That is exactly the "call sites wholesale"
churn CLAUDE.md says must not be an incidental side effect. Secondarily, because parity
(§4) is asserted only at the final-string level, the per-rule *method* contract divergence
is never tested. This needs an explicit, requirements-blessed decision (like the
already-blessed `Unparser()` vs `Unparser(terminals)` constructor change), not an open
question presented as settled.

Suggested fix: Either (a) get explicit sign-off that string-return is the intended Rust
Python surface and fold open-Q2 into a stated decision, or (b) mirror the Python contract
more closely (return a Doc/UnparseResult handle plus a separate render call) if drop-in
call-site compatibility is required.

## design-2: `_doc_to_rust_expr` is specified to handle `Group`/`Nest`/`Join`, but its declared Python analog `_doc_to_combinator_expr` raises on those — silent cross-backend divergence

Section: §2.2, "Anchors / spacing / dispositions" bullet: "Their Doc results are emitted as
Rust Doc constructor expressions by a `_doc_to_rust_expr(doc)` helper, the analog of
`_doc_to_combinator_expr` (:396); it covers `Nil`, `Nbsp`, `Line`, `SoftLine`,
`HardLine{blank_lines}`, `Text`, `Concat`, and (for join separators) `Group`/`Nest`/`Join`."

What's wrong: The reference `_doc_to_combinator_expr` (gsm2unparser.py:396-426) handles only
NIL/NBSP/LINE/SOFTLINE/HARDLINE, `HardLine`, `Text`, and `Concat`; anything else (including
`Group`, `Nest`, `Join`) hits the `else` and raises `ValueError(f"Unknown Doc type: {doc}")`.
A `.fltkfmt` `join ... by group(...)` / `nest(...)` / `join(...)` separator IS reachable —
`_process_join_statement`@fmt_config.py:708 builds the separator via
`_doc_literal_cst_to_doc`, which can return `group`/`nest`/`join` (fmt_config.py:408-419,
398-406). So such a config makes the **Python** unparser fail at generation time, while the
design's Rust `_doc_to_rust_expr` would accept it and emit a `Doc::Group/Nest/Join`.

Why / grounding: source comparison above. The design calls the helper "the analog of
`_doc_to_combinator_expr`" but specifies a strict superset of that function's domain.

Consequence: For a format config using a group/nest/join-valued separator, the two backends
are no longer equivalent: Python errors out (no unparser generated), Rust silently
generates and formats. That contradicts requirements' cross-backend behavioral-equivalence
goal and the design's own "faithful re-expression ... control structure is identical"
framing. Low likelihood (exotic config) but a latent, silent inconsistency.

Suggested fix: Make `_doc_to_rust_expr` match `_doc_to_combinator_expr`'s domain exactly
(raise on Group/Nest/Join), OR, if extending separator support is intended, extend the
Python helper too and call it out as a deliberate, both-backends change rather than an
incidental superset.

## design-3: Per-construct mapping covers RULE_START/RULE_END anchors but omits item-level (before/after-item) GROUP/NEST/JOIN begin-end operations

Section: §2.2 — "Rule entry" bullet explicitly maps RULE_START/RULE_END anchor ops to
`push_group/nest/join` and `pop_*`; the "Anchors / spacing / dispositions" bullet then
describes anchor configs only as Doc results emitted via `_doc_to_rust_expr`.

What's wrong: The Python unparser also emits accumulator push/pop at *item* granularity for
LABEL/LITERAL-selected anchors via `_gen_anchor_operations_before_item`
(gsm2unparser.py:1472-1516) and `_gen_anchor_operations_after_item` (:1517-1559), invoked
from `gen_alternative_unparser` (:1602, :1656). These translate GROUP_BEGIN / NEST_BEGIN /
GROUP_END / NEST_END / JOIN_BEGIN / JOIN_END into `push_group()/pop_group()/push_nest()/
pop_nest()/push_join()/pop_join()` mid-alternative. These are accumulator state transitions,
NOT Doc results — so the "emit Doc results via `_doc_to_rust_expr`" framing does not cover
them, and the explicit push/pop mapping is given only for the rule-level RULE_START/RULE_END
case. This is a distinct, non-trivial code path (it is what implements
`group from label:X to label:Y`, `nest from ... to ...`, `join from ... to ...`).

Why / grounding: source path above; the runtime support is present (§2.1 accumulator.rs
lists push/pop group/nest/join), so the gap is purely in the per-construct spec, which the
design otherwise presents as the implementation blueprint (it bothered to enumerate the
rule-level anchors).

Consequence: If the implementer follows the per-construct mapping literally, mid-rule
group/nest/join directives would not be ported — grammars whose `.fltkfmt` uses item-level
range operations would lose grouping/nesting/joining on the Rust backend and format
differently from Python, another cross-backend divergence. The fixture `.fltkfmt` (§2.6)
should also explicitly exercise an item-level (label/literal-anchored) group/nest/join so
the parity test actually catches this path, not just rule-wide and default spacing.

Suggested fix: Add an explicit per-construct line mapping `_gen_anchor_operations_before_item`
/ `_after_item` GROUP/NEST/JOIN begin/end to the accumulator push/pop calls, parallel to the
RULE_START/RULE_END bullet, and ensure the fixture format config covers one.
