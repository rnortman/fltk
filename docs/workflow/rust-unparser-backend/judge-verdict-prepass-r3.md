# Judge verdict — prepass (round 3)

Phase: prepass (code). Base d622ff7..HEAD e6a682c. Round 1.
Notes: 2 reviewer files (slop: 3 findings; scope: none). 3 findings total.

## Added TODOs walk

No TODO comments added in the diff (gsm2unparser_rs.py, test_rust_unparser_generator.py, implementation-log.md). Nothing to score.

## Other findings walk

### slop-1 — Fixed
Claim: generated Rust output carried a development-schedule comment
`// Term handling (extract/validate child + dispatch) is emitted later.` in
`_gen_item_method`; consequence is scaffolding prose shipping in the public `.rs`
artifact that becomes a lie once the term body lands.
Diff at `gsm2unparser_rs.py` `_gen_item_method`: the emitted body is now a single
`lines.append("        Some(UnparseResult::new(acc, pos))")` with no comment line.
The generated item method is therefore a bare pass-through; the scaffold nature is
evident from the method name + body.
Assessment: fix removes the comment exactly as the finding asked. Accept.

### slop-2 — Fixed
Claim: `_gen_item_method` docstring narrated the dev schedule ("is emitted by a later
increment", "Until then …") rather than the contract; consequence is the docstring
becomes a false claim once the next increment fills the body.
Diff: docstring rewritten to "The signature matches design §2.2: the accumulator is
threaded by value and the position by `usize`. The emitted body returns the
accumulator and position unchanged (a pass-through); child extraction/validation,
term dispatch, and quantified-loop/suppressed-item handling are not emitted in this
method." Drops "later increment"/"until then"; states the method's current contract.
This is precisely the reviewer's suggested remedy ("describe the function's invariant
contract … drop all references to 'later increment' and 'until then'"). The remaining
text describes this method's own current responsibilities, which co-locate with any
future body edit — not the survives-forever schedule narration the finding targeted.
Assessment: fix matches the finding's own suggested fix. Accept.
(Noted in passing, not a flagged finding: sibling generator docstrings
`_gen_rule_methods` / `_gen_alternative` / `_gen_alternative_body` still carry similar
"later increment" narration; the slop reviewer scoped slop-2 to `_gen_item_method`
only, so it is outside this adjudication.)

### slop-3 — Won't-Do
Claim: the RULE_START / RULE_END loops have no `else: raise` for unrecognized
`OperationType`, so a misconfigured or future-extended anchor silently drops an
operation; consequence is the Rust unparser ignores part of its formatting config,
diverging from Python.
Rationale (Won't-Do): (1) Python backend has identical silent-skip; a Rust-only raise
creates cross-backend divergence (active harm). (2) Branch unreachable by construction.
(3) Hardening against a future OperationType is a deliberate both-backends change, out
of scope.
Source verification:
- Parity (1): `gsm2unparser.py:222-243` (RULE_START) emits exactly GROUP_BEGIN /
  NEST_BEGIN / JOIN_BEGIN with the same JOIN_BEGIN `raise` and no `else`;
  `:767-779` (RULE_END) emits NEST_END / GROUP_END / JOIN_END, no `else`. The Rust
  loops mirror these one-for-one. Design §2 mandates "The control structure is
  identical; only the target API changes," so a Rust-only `else: raise` would be the
  divergence — adding it, not omitting it, breaks parity. The reviewer's "discrepancy
  between backends" consequence is inverted.
- Unreachability (2): `OperationType` = SPACING + six BEGIN/END (`fmt_config.py:98-107`).
  SPACING ops attach only to LABEL/LITERAL anchor keys (`_process_after_statement` :540,
  `_process_before_statement` :580). The `before:rule_start:` / `after:rule_end:` keys
  are populated solely by `_process_range_operation` — :629-634 appends only a BEGIN op
  to rule_start, :664-670 inserts only an END op to rule_end. `get_anchor_config`
  merges per-key (`:186-204`), so it cannot relocate a SPACING/END op into the
  rule_start key. Every op reaching the loops is one of the three handled variants;
  nothing is dropped by any live `.fltkfmt`.
- Locus (3): consistent with design §2.2, which frames robustness extensions (the
  group/nest/join separator-rejection) as deliberate both-backends changes, "not an
  incidental Rust-only superset."
Assessment: this-iteration code, but Won't-Do is a rejection-of-defect, not a silent
deferral — the behavior is the design-mandated parity, and the rationale argues active
harm (divergence) plus a verified false-premise (unreachable). The finding is a
robustness nit describing an unreachable state; the responder is right. Accept.

## Approved

3 findings: 2 Fixed verified, 1 Won't-Do sound. Scope reviewer: no findings.

---

## Verdict: APPROVED

All three dispositions acceptable. slop-1/slop-2 fixes match the findings' own
suggested remedies; slop-3 Won't-Do is verified against the Python backend and
fmt_config as design-mandated cross-backend parity over an unreachable branch.
