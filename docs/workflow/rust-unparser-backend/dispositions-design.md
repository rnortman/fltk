# Dispositions: Rust Unparser Backend design review (round 1)

Reviewer notes: `notes-design-design-reviewer.md`. All three findings fact-checked
against source (`gsm2unparser.py`, `fmt_config.py`, `plumbing.py`); all three confirmed.

design-1:
- Disposition: Fixed
- Action: Resolved the design's internal contradiction (string-return decided in
  §2.4 while open question 2 re-opened "is string sufficient"). §2.3 last paragraph now
  names two deliberate, documented Python-surface divergences (constructor + per-rule
  method contract). §2.4 rewritten to declare the PyO3 `unparse_{rule}` rendered-string
  return as a deliberate, called-out divergence parallel to the constructor change, with
  rationale (Doc/UnparseResult are pure-Rust with no PyO3 bindings; cross-backend contract
  is rendered-string parity), plus a bounded migration note for out-of-tree consumers.
  Open question 2 reframed to the genuinely-open additive part only (whether to *also*
  expose the intermediate Doc to Python), no longer re-asking the settled string question.
  Verified Python `unparse_{rule}` returns `Optional[UnparseResult]` at gsm2unparser.py:198-210
  and callers chain resolve+render at plumbing.py:302-347.
- Severity assessment: Medium. Without the fix the design simultaneously decided and
  re-opened the same public-API question, and the per-method return-type divergence from
  the Python backend was undeclared — exactly the kind of call-site change CLAUDE.md says
  must be deliberate, not incidental.

design-2:
- Disposition: Fixed
- Action: §2.2 "Anchors / spacing / dispositions" bullet rewritten so `_doc_to_rust_expr`
  mirrors `_doc_to_combinator_expr`'s domain **exactly** — covers Nil/Nbsp/Line/SoftLine/
  HardLine/Text/Concat and raises the same `ValueError` on everything else, including
  Group/Nest/Join. Documented that a `join … by group(…)/nest(…)/join(…)` separator yields
  a Group/Nest/Join Doc that the Python backend already rejects at generation time, so the
  Rust helper must reject identically; extending separator support is called out as a
  deliberate both-backends change, not a Rust-only superset. Verified the raise at
  gsm2unparser.py:424-426, the join-separator path fmt_config.py:_doc_literal_cst_to_doc
  (408-419) via _process_join_statement (708-718), and the JOIN_BEGIN feed points at
  gsm2unparser.py:240, :1512, :1556.
- Severity assessment: Low likelihood (exotic config) but a latent silent cross-backend
  inconsistency: Python errors at gen time, Rust would generate and format. The fix is
  cheap and restores exact parity.

design-3:
- Disposition: Fixed
- Action: Added a new §2.2 "Item-level anchor operations" bullet mapping
  `_gen_anchor_operations_before_item`/`_after_item` GROUP/NEST/JOIN begin/end to
  accumulator `push_group/push_nest/push_join` and `pop_*`, parallel to the rule-level
  RULE_START/RULE_END bullet, noting these are accumulator state transitions (not Doc
  results) and that they implement `group/nest/join from … to …`. §2.6 fixture updated to
  require at least one item-level (label-/literal-anchored) range op in the `.fltkfmt` so
  the parity test exercises this path. Verified the helpers at gsm2unparser.py:1472-1559
  and their invocation from gen_alternative_unparser at :1602/:1656; confirmed runtime
  push/pop support is already listed in §2.1 accumulator.rs.
- Severity assessment: Medium. An implementer following the per-construct mapping literally
  would have omitted mid-rule group/nest/join, dropping grouping/nesting/joining on the
  Rust backend for grammars whose `.fltkfmt` uses item-level ranges — a real cross-backend
  divergence that the fixture, as previously specified, might not have caught.
