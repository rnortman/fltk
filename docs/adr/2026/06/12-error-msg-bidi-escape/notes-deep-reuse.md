Style: concise, precise, complete, unambiguous. No padding, no preamble.

## reuse-1

**File:line:** `crates/fltk-parser-core/src/errors.rs:424-432` (test `format_error_message_no_raw_extended_set_in_output`)

**What's duplicated:** The `is_escaped_set` inline predicate in the Rust test body re-implements the full escape-set membership check (C0 except TAB/LF, DEL, C1, ALM, ZWSP–RLM, LS–RLO, WJ, LRI–PDI, BOM) — 9 conditions, identical to `needs_escape` in `crates/fltk-cst-core/src/escape.rs:36-61`.

**Existing function:** `needs_escape` — `crates/fltk-cst-core/src/escape.rs:36` — private (`fn`, not `pub fn`); the test lives in a different crate (`fltk-parser-core`), so it cannot call it directly. It could be made `pub(crate)` or `#[cfg(test)] pub` in `escape.rs`, or the test could be moved to `escape.rs`'s own `#[cfg(test)]` block where `needs_escape` is already in scope (and where the analogous escape-unit tests already live).

**Consequence:** The inline predicate will drift from `needs_escape` if the escape set is extended again — a future maintainer adding a codepoint to `needs_escape` must remember to update the test assertion independently, with no compiler or lint check to enforce the sync. The same drift hazard already bit `escape_control_chars_for_msg` (the bug this commit fixes); this is a smaller-scale repeat of the same pattern.

---

## reuse-2

**File:line:** `tests/test_pyrt_errors.py:198-208` (test `test_format_error_message_no_raw_extended_set_in_output`)

**What's duplicated:** The `is_escaped_set` inline predicate in the Python test re-implements the same membership check as `_needs_escape` in `fltk/fegen/pyrt/errors.py:69-99` (9 conditions, same logic). `_needs_escape` is module-private (leading underscore) but is importable in the test file via `from fltk.fegen.pyrt.errors import _needs_escape` — Python does not enforce the convention.

**Existing function:** `_needs_escape` — `fltk/fegen/pyrt/errors.py:69`.

**Consequence:** Same drift hazard as reuse-1. The two predicates (`is_escaped_set` inline and `_needs_escape`) must be manually kept in sync across every future escape-set extension; no automated check enforces it.
