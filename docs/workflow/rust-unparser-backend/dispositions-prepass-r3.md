# Dispositions — prepass round 3

Notes reviewed:
- `notes-prepass-slop-r3.md` (slop-1, slop-2, slop-3)
- `notes-prepass-scope-r3.md` (no findings)

Fix commit: `e6a682cb883db43d6df2cc7215cb982121934254`

---

## slop-1

- Disposition: Fixed
- Action: Removed the generated-output comment
  `// Term handling (extract/validate child + dispatch) is emitted later.` from
  `_gen_item_method` (`fltk/unparse/gsm2unparser_rs.py`, formerly line 304). The emitted
  body is now just the bare pass-through `Some(UnparseResult::new(acc, pos))`, which is
  self-evidently a scaffold from the method name and body.
- Severity assessment: Minor. A development-schedule comment ("is emitted later") was
  leaking into the public generated `.rs` artifact, where it is meaningless to downstream
  consumers and would become a falsehood once the term-handling body lands. No runtime or
  correctness impact; cleanliness of generated output only.

## slop-2

- Disposition: Fixed
- Action: Rewrote the `_gen_item_method` docstring (`fltk/unparse/gsm2unparser_rs.py:~291`)
  to describe the method's invariant emitted contract — signature per design §2.2
  (accumulator threaded by value, `pos: usize`) and the pass-through body it currently
  emits — dropping the "is emitted by a later increment" / "Until then" schedule narration.
  The new text states a fact about the code as-is, so it will not silently become a lie.
- Severity assessment: Minor. The docstring narrated the implementation schedule rather
  than the contract; it would have become stale/false once a later increment filled in
  term handling. Documentation accuracy only; no behavioral effect.

## slop-3

- Disposition: Won't-Do
- Action: No change. The RULE_START loop (`gsm2unparser_rs.py:194-204`) and RULE_END loop
  (`:209-216`) intentionally have no `else: raise` for unrecognized operation types.
- Severity assessment: No real defect. The "silently dropped operation" the finding
  describes is unreachable from any `.fltkfmt` config, and adding a Rust-only raise would
  introduce a cross-backend divergence — the more harmful outcome.
- Rationale (Won't-Do):
  1. **Faithful parity with the authoritative Python backend.** The Python
     `UnparserGenerator` these generators mirror has the *identical* silent-skip in both
     loops — RULE_START at `fltk/unparse/gsm2unparser.py:224-243` and RULE_END at
     `:770-779` — with no `else: raise`. The JOIN_BEGIN-missing-separator raise the finding
     points to as the "pattern" exists in *both* backends (`gsm2unparser.py:237-239` /
     `gsm2unparser_rs.py:200-202`); the asymmetry (that raise, but no else-raise) is
     therefore deliberate cross-backend parity, not a Rust-side oversight. Design §2
     mandates "The control structure is identical; only the target API changes," and
     CLAUDE.md requires cross-backend behavioral equivalence. A Rust-only raise would
     violate both: a config (or future op) that the Python backend silently skips would
     crash the Rust generator.
  2. **The branch is unreachable by construction.** `OperationType` has exactly SPACING
     plus the six BEGIN/END variants (`fmt_config.py:98-107`). SPACING ops are only ever
     attached to LABEL/LITERAL anchor keys (`_process_after_statement` `fmt_config.py:540`,
     `_process_before_statement` `:580`), never to `before:rule_start:` / `after:rule_end:`.
     The rule_start/rule_end anchors are populated solely by `_process_range_operation`
     (`fmt_config.py:629-634`, `:664-670`), which appends only BEGIN ops to rule_start and
     only END ops to rule_end. `get_anchor_config`'s merge is per-key, so it cannot move a
     SPACING or END op into the rule_start key (`fmt_config.py:206-236`). Thus every
     operation reaching these loops is already handled; there is no live config that the
     missing `else` would silently drop.
  3. **Right locus is a deliberate both-backends change, out of scope.** Hardening against
     a *future* `OperationType` (the finding's hypothetical) is a robustness change that
     must land in both backends together, exactly as design §2.2 frames the group/nest/join
     separator-rejection as "a deliberate both-backends change, not an incidental Rust-only
     superset." Adding it to the Rust generator alone in respond mode would be precisely the
     incidental Rust-only divergence the design warns against.
