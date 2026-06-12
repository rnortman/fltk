# Design review findings: rust-cst-eq-depth

Reviewed `design.md` against `request.md`, `exploration.md`, and source at base b02cb8f.

Verified accurate (spot-checked against source): root-cause chain (`gsm2tree_rs.py:798-803` → `:577-588` → `shared.rs:98-109`); Drop/Debug prior art (`:748-755`, `:764-788`, `_drop_block`); `into_drop_item` emission condition (`:601`) matches the claimed condition for `eq_shallow_enqueue`; wildcard-arm guard (`:576`, `:584`); `_child_class_union` (`:267-278`); `generate()` (`:280-302`); struct doc line `:729`; label type `Option<LabelEnum>`/`Option<()>` (`:708`); handle `__eq__` delegation; `make gencode` exists and covers exactly the listed outputs incl. the spike `cp` (Makefile gencode target); `TODO.md:23` entry; all five cited regression tests (`tests/rust_cst_fixture/src/native_tests.rs:110,119,128,183,190`) and the Drop/Debug depth tests (`tests/rust_parser_fixture/src/native_tests.rs:14,39,59,118,150`) exist as described. Requirements coverage is complete: pair worklist, no mutation, per-pair ptr_eq preserved, `Shared<T>` generic/unchanged, Python backend untouched, no scope expansion, regen+TODO-removal bookkeeping, full-suite gates. Lock-footprint argument (max two guard pairs: root pair in `Shared::eq` + current item's pair) checks out; cycle/DAG rows consistent with shared.rs docs.

## design-1: Test 6 does not exercise the arm it claims to pin

Section 5, test 6: "`test_eq_variant_mismatch_unequal` — shallow: `Expr` with `lhs:Expr` child vs. `Expr` with `atom:Atom` child at the same position → unequal (pins the wildcard arm of `eq_shallow_enqueue`)."

What's wrong: in the designed driver (§2.2d), the per-child check is `if la != lb || !ca.eq_shallow_enqueue(cb, &mut worklist)`. `lhs` vs `atom` are *different labels*, so `la != lb` short-circuits to `false` before `eq_shallow_enqueue` is ever called. The wildcard variant-mismatch arm (`_ => false`, §2.2c) is never reached by this construction.

Why (source-backed): label comparison precedes child comparison both in the design's own driver code (§2.2d, line `if la != lb || !ca.eq_shallow_enqueue(...)`) and in today's tuple eq. The grammar's `expr` rule binds `lhs` only to `Expr` and `atom` only to `Atom`, so reaching variant-mismatch via natural labels is impossible for `expr`.

Consequence: the test passes for the wrong reason; the wildcard arm of `eq_shallow_enqueue` ships untested. A generator bug in that arm (e.g. returning `true`, or an unreachable-pattern miscount) would not be caught, and variant-mismatch trees could compare equal.

Suggested fix: construct same-label/different-variant children. Two options in the existing fixture grammar: (a) `push_child` performs no type checking (`gsm2tree_rs.py:840-845` doc), so `push_child(Some(ExprLabel::Lhs), ExprChild::Expr(..))` vs `push_child(Some(ExprLabel::Lhs), ExprChild::Atom(..))`; or (b) the union-label `val` rule (`item:num | item:name | item:/.../`, see `tests/rust_parser_fixture/src/native_tests.rs:757-803`) naturally yields `ValChild::Num` vs `ValChild::Name` under the same `item` label.

## design-2: Unused `worklist` parameter in `eq_shallow_enqueue` for span-only union members → `-D warnings` failure

Section 2.2c: `eq_shallow_enqueue` is emitted "under the same emission condition (`child_classes` non-empty OR `class_name in child_union`)" with the uniform signature `fn eq_shallow_enqueue(&self, other: &Self, worklist: &mut Vec<EqWorklistItem>) -> bool`.

What's wrong: for span-only union members (`child_classes` empty, class in `child_union` — e.g. `Num`, `Name`, `Trivia` in rust_parser_fixture; `Identifier`, `Literal` in rust_cst_fixture), the emitted body has only the Span arm (`(Self::Span(a), Self::Span(b)) => a == b`) and possibly a wildcard. No arm touches `worklist`, so the parameter is unused → `unused_variables` warning → hard failure under the `-D warnings` clippy gates that `make check` runs on every fixture crate (Makefile lines 53-54, 67-71). The design does not address this, while the generator has an established conditional-underscore convention for exactly this problem (`py_param = "py" if ... else "_py"` at `gsm2tree_rs.py:624`, and `extract_py_param`/`_span_type` at `:646-652`). The Drop analog has no such issue because `into_drop_item` takes only `self`.

Consequence: regenerated `cst.rs` for every in-tree grammar containing span-only union members (all of them) fails `make check`; implementer discovers it as a late compile break instead of a designed-for case.

Suggested fix: emit the parameter as `_worklist` when `child_classes` is empty (or bind `let _ = worklist;`), mirroring the existing `_py`/`_span_type` convention.

## design-3: Stale base citation — late-file gsm2tree_rs.py line numbers off by 8 at the actual base

Section header: "Repo HEAD: 5d94733." The implementation base is b02cb8f (child of 5d94733), which deleted 8 comment lines from `gsm2tree_rs.py` (two TODO blocks, old lines ~1230 and ~1314 — verified via `git diff 5d94733..b02cb8f`).

What's wrong: every design citation at or below those deletions is shifted by 8 at b02cb8f: `_eq_method` cited 1867-1888 → actual 1859-1880; `_emit_drain_arm` cited 1915-1932 → actual 1907-1924; `_drop_block` cited 1934-1972 → actual 1926-1964. All citations above line ~1230 (267-278, 280-302, 577-588, 591-613, 729, 764-788, 790-803) verified exact at b02cb8f.

Consequence: minor — an implementer following the late line numbers lands in the wrong function; recoverable by symbol name. No design logic depends on the offsets.

Suggested fix: note the base as b02cb8f and treat function names as authoritative over line numbers.
