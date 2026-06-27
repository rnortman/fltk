# Deep correctness review — batch 6 (Rust unparser generator: quantified loops, dispositions, item anchors)

Commit reviewed: ae90f84671cf03d4b6e2aeed244bab3df1b1d633 (base 663b2734c2157f8f23ed5f2a9d178070c56afca0)
Scope: `fltk/unparse/gsm2unparser_rs.py` generator term-handling additions + tests.

No findings.

## What was traced (logic / control flow / data flow vs. Python `gsm2unparser.py`)

- Quantified loop (`_gen_quantified_loop_body`) vs `_gen_quantified_item_body` (:533):
  `current_pos`/`acc` threading, `acc.clone()`-per-attempt (last-successful preserved
  on failure), `let-else break` == Python success/failure split, `+` min-check
  (`match_count == 0 -> return None`, :611) vs `*` (no counter). `is_plus =
  min()==Arity.ONE` correctly distinguishes `+`/`*`; only `+`/`*` reach the method
  (gated by `is_multiple()`). Loop bound `current_pos < node.children().len()` matches
  Python. Faithful.
- `__inner` emission (`_gen_inner_methods`) + routing (`_item_routes_to_quantified_loop`,
  `_gen_item_method` quantified-branch-before-subexpr): a quantified sub-expression's
  `__alts` tree correctly hangs off `__inner`, not the item method; SUPPRESS excluded
  (reconstructed via `_gen_suppressed_item_body`, matching Python :462 ordering). Label
  boundary stop (inner label-mismatch -> None -> loop break) verified for mixed-label
  alternatives.
- Dispositions (`_item_disposition_success_lines`, `_gen_alternative_body`) vs
  `gen_alternative_unparser` (:1600/:1604/:1628/:1633/:1644): Normal merges + after-
  spacing; Omit discards (item still called to advance `pos`/validate, prior `acc`
  preserved via clone-in); RenderAs substitutes spacing, discards output, no after-
  spacing. Before-spacing gated on `is_normal` (== Python `not Omit|RenderAs`, :1604).
  Move-vs-clone of `acc` (Normal moves; Omit/RenderAs clone; optional always clones) is
  sound Rust and semantically equal to Python's immutable-accumulator threading.
  Omit-on-default-suppressed-literal path matches Python (grammar SUPPRESS vs formatter
  OMIT are distinct; both backends reconstruct-then-drop).
- Item anchors (`_item_anchor_config`, `_item_anchor_lines`) vs
  `_gen_anchor_operations_before_item`/`_after_item` (:1472/:1517): before/after selector
  asymmetry preserved (before: LABEL then LITERAL fallback; after: LABEL-only for
  labeled, LITERAL-only for unlabeled literal). SPACING skipped; GROUP/NEST/JOIN
  begin/end map to push/pop; `op.indent or 1`; JOIN_BEGIN separator routed through
  `_doc_to_rust_expr` (inherits Group/Nest/Join rejection) with missing-separator raise.
  Before-anchors precede before-spacing; after-anchors unconditional at outer (8-space)
  indent, outside the optional `if let` — matching Python `method.block` scope (:1656).

## Parity-preserving non-bugs (not flagged)

- Non-advancing inner in a quantified loop would infinite-loop; the Python backend has
  the identical hazard (`while current_pos < len`, inner returns unchanged pos+success),
  so this is parity, not a divergence introduced here.
- `_item_anchor_lines` raises on an unknown `OperationType` where `_gen_rule_entry`
  silently ignores it; Python silently ignores in both. No behavioral divergence for the
  current enum (all six begin/end ops + SPACING handled identically).
- Acknowledged-deferred `unused_mut`/`unused` warnings (all-Omit alternative; `node`
  unused in suppressed/INLINE bodies) are warning/quality concerns, resolved by the
  fixture-landing increment per the implementation log — not correctness, out of lane.
