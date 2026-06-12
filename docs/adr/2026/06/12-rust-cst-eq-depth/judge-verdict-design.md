# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/06/12-rust-cst-eq-depth/design.md`. Round 1.
Notes: 1 reviewer file; 3 findings. All dispositioned Fixed.

Style: concise, precise, complete, unambiguous. No padding.

## Findings walk

### design-1 — Fixed
Claim: §5 test 6 (`test_eq_variant_mismatch_unequal`) used `lhs:Expr` vs `atom:Atom` — different labels, so the driver's `la != lb ||` short-circuit (§2.2d) returns before `eq_shallow_enqueue`; the wildcard variant-mismatch arm ships untested. Consequence: generator bug in that arm (mismatched trees comparing equal) uncaught.
Design now (§5 test 6): rewritten to same-label/different-variant via the union-label `val` rule — `item:num` (`ValChild::Num`) vs `item:name` (`ValChild::Name`) under the same `item` label, with type-unchecked `push_child` as alternative.
Verification: fixture rule `val := item:num | item:name | item:/[!@#$]+/` confirmed at `tests/rust_parser_fixture/src/native_tests.rs:757-803` (`ValChild::Num`/`Name`/`Span` all under label `item`); `push_child` no-type-check doc confirmed at `fltk/fegen/gsm2tree_rs.py:840-845`. Same label → `la != lb` is false → `eq_shallow_enqueue` reached → `(Num, Name)` falls to the wildcard (3 variants, so the `>1 variant` guard emits it). Fix reaches the arm the test claims to pin.
Assessment: fix addresses the consequence. Accept.

### design-2 — Fixed
Claim: uniform `eq_shallow_enqueue` signature leaves `worklist` unused for span-only union members (only a Span arm) → `unused_variables` under the `-D warnings` clippy gates → every regenerated in-tree grammar fails `make check`.
Design now (§2.2c, final paragraph): span-only union members (`child_classes` empty, class in `child_union` — `Num`, `Name`, `Trivia`) emit the parameter as `_worklist`, citing the existing conditional-underscore convention.
Verification: Makefile clippy lanes run `-D warnings` on all fixture crates (cargo-clippy at ~53-55, cargo-clippy-no-python at ~67-72); convention confirmed at `fltk/fegen/gsm2tree_rs.py:624` (`py_param = "py" if ... else "_py"`) and `:646-652` (`extract_py_param`/`_span_type`). The Drop analog is unaffected (`into_drop_item` takes only `self`), matching the design's claim.
Assessment: designed-for case now; mirrors established convention. Accept.

### design-3 — Fixed
Claim: design header cited HEAD 5d94733 while the implementation base is b02cb8f, which deleted 8 lines from `gsm2tree_rs.py`, shifting all late-file citations by 8.
Design now: header (line 3) states base b02cb8f with function names authoritative over line numbers; corrected citations `_eq_method` 1859-1880, `_emit_drain_arm` 1907-1924, `_drop_block` 1926-1964.
Verification: `git diff --stat 5d94733..b02cb8f -- fltk/fegen/gsm2tree_rs.py` = 8 deletions; at current checkout (b02cb8f) `_eq_method` starts at 1859, `_emit_drain_arm` at 1907, `_drop_block` at 1926 and ends ~1964. All three corrected citations land on the named functions.
Assessment: corrected. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified.

---

## Verdict: APPROVED

All dispositions acceptable. Round 1.
