# Quality review — blank-line preservation fix (ef8f727..5864ae1) — r1

Reviewed commit: 5864ae1

## quality-1 — Design-doc terminology and changelog phrasing baked into test docstrings

Locations:
- `fltk/unparse/test_unparser.py:1176` ("so only defect 1a (config clobbering) is in play",
  "Fails before the config-layer fix"), `:1210` ("Pins component B behaviorally",
  "isolates defect 1b. Fails before the counting fix."), `:1241` ("Guards component B's
  whitespace-only rule")
- `tests/test_rust_unparser_generator.py:2044` ("This is the gear scenario that defect 1b
  regressed"), `:2058` ("Component A reaches the Rust generator", "the order that discarded
  ``preserve_blanks`` before the config-layer fix")
- `fltk/lsp/test_gear_demo.py:98` ("the two defects this fix addresses")

Issue: "defect 1a", "defect 1b", "component A", "component B" are labels defined only in
`docs/adr/2026/07/08-formatter-blank-line-preservation/design.md`. The docstrings do not
cite the doc, but the vocabulary is unintelligible without it. "Fails before the fix" /
"before the config-layer fix" is changelog phrasing — it describes the history of the change,
not what the test pins today.

Consequence: the code does not stand on its own. A maintainer reading these tests in a year
has to reverse-map "component B" to "whitespace-aware trivia newline counting" via an ADR
archaeology trip. This exact class of comment was just scrubbed in this repo (commits
`fe10193` "remove step3 workflow labels", `f38cdb3` "reword workflow-referencing comments to
stand alone") — reintroducing it means the cleanup has to keep happening.

Fix: replace the labels with the plain descriptions the docstrings already half-contain, e.g.
"only the config-clobbering path is in play (direct-span trivia keeps the newline counter out
of it)", "pins the whitespace-aware newline counting over node-wrapped whitespace". Replace
"Fails before the fix" with the invariant being pinned ("`preserve_blanks` listed before
`trivia_preserve` must survive parsing"). In `test_gear_demo.py`, drop "the two defects this
fix addresses" and state the two properties directly (clobbering statement order + node-wrapped
whitespace both exercised). Related minor instance: `fltk/unparse/pyrt.py:84`
("``count_span_newlines``, unchanged semantics") — "unchanged" is history-relative; say what
it does, not what it didn't change.

## quality-2 — Rust generator reverse-engineers Span-variant presence by arithmetic

Location: `fltk/unparse/gsm2unparser_rs.py:1518-1520`

```python
node_child_classes = self._cst.child_class_names_for_rule(gsm.TRIVIA_RULE_NAME)
num_variants = self._cst.num_child_variants(gsm.TRIVIA_RULE_NAME)
has_span = num_variants > len(node_child_classes)
```

Issue: whether the `TriviaChild` enum has a `Span` variant is a fact the CST generator already
computes directly (`gsm2tree_rs.py:307-317`, `_child_variants_for_rule` returns
`(child_classes, has_span)`), but the only public accessors are `num_child_variants` and
`child_class_names_for_rule`, so this call site infers `has_span` by subtraction. That encodes
an invariant of another module ("variant count = node classes + optionally one Span, nothing
else") at the consumer. The existing wrappers' own docstrings (`gsm2tree_rs.py:826-846`) say
they exist precisely so callers "need not duplicate the len(child_classes) + has_span
arithmetic" — this is the inverse duplication.

Consequence: if the child enum ever grows another variant kind (or the counting rule changes),
this inference silently miscomputes `has_span` and the generated match either gains a spurious
Span arm (compile error, best case) or drops one (silent behavior change, worst case). It also
invites copy-paste: the next consumer that needs `has_span` will repeat the subtraction.

Fix: add a `has_span_child(rule_name) -> bool` public wrapper on the CST generator next to
`child_class_names_for_rule` (one-line body over `_child_variants_for_rule`) and call it here.

## quality-3 — Generated Rust duplicates an identical 7-line match-arm body per node variant

Location: `fltk/unparse/gsm2unparser_rs.py:1537-1550` (generator loop); visible in committed
output at `crates/fegen-rust/src/unparser.rs:37-52`, where the `BlockComment` and `LineComment`
arms are byte-identical bodies.

Issue: every node-typed `TriviaChild` variant gets the same read-lock / span-text /
whitespace-check / count body. Two variants today in fegen; a consumer grammar with a richer
trivia rule (several comment forms + whitespace forms) gets N copies.

Consequence: the generated unparser is committed, reviewed, and diffed source in this repo and
in every downstream repo; N identical bodies bloat those diffs and mean a future tweak to the
whitespace rule (e.g. the comment-terminator semantics flagged as an open question in the
design) must be verified N times per grammar instead of once.

Fix: emit a single private helper once per unparser impl, e.g.
`fn _whitespace_node_newlines(t: Option<&str>) -> usize`, and have each node arm reduce to
`count += Self::_whitespace_node_newlines(node.read().span().text_str());`. The Python side
already has exactly this shape (`pyrt.count_whitespace_newlines`); this restores the symmetry
the parity comments claim.

## quality-4 — Gear test copy-pastes the format-pipeline setup from the idempotency test

Location: `fltk/lsp/test_gear_demo.py:102-112` vs `:74-85`

Issue: `test_formatting_preserves_blank_lines_between_items` duplicates the six-line
engine/config/parser/unparser/renderer setup and the parse→unparse→render sequence that
`test_formatting_is_idempotent` already has (the latter as its local `render` closure).

Consequence: this is the second copy; the formatting suite for gear will keep growing (the
design itself anticipates more formatting behaviors), and each new test re-pastes the pipeline.
Beyond drift risk, each copy regenerates a full parser + unparser, which is the expensive part
of this module's runtime.

Fix: extract a module-level `_format(text: str) -> str` helper (or a fixture returning the
`render` callable) built once from `_engine()` + `parse_format_config_file(_FMT)`, and use it
from both tests.
