# Reuse Review: rust-parser-generator (490bccf..b95f772)

## reuse-1

**File:line:** `fltk/fegen/gsm2parser_rs.py:21–40`

**What's duplicated:** `_rust_str_lit(s)` — module-level function that escapes a Python string into a Rust string literal (handles backslash, double-quote, control characters, DEL).

**Existing function/utility:** None in `gsm2tree_rs.py` today, but `gsm2parser_rs.py` imports from `gsm2tree_rs` and already accesses `RustCstGenerator` internals. The natural home would be a shared module-level helper in `gsm2tree_rs.py` (which already handles all Rust name derivation) or a new `rust_codegen_utils.py`. The function is currently duplicated in spirit: `gsm2tree_rs.py` emits Rust string literals (`"NodeKind.{class_name.upper()}"`, regex patterns embedded in preamble strings, etc.) using Python f-strings directly without a centralised escape helper, meaning those call sites are just lucky that current inputs contain no characters requiring escaping.

**Consequence:** If the escaping rules ever change (e.g. to handle Unicode above U+007F, or non-BMP characters in grammar rule names), only `gsm2parser_rs.py` would be updated; `gsm2tree_rs.py` literal-embedding sites would silently produce malformed Rust. Rule names and labels flow through `gsm2tree_rs.py`'s emitted string literals without going through `_rust_str_lit`, so the gap is already live.

---

## reuse-2

**File:line:** `fltk/fegen/gsm2parser_rs.py:154–162`

**What's duplicated:** `_child_enum_name(rule_name)` and `_label_enum_name(rule_name)` on `RustParserGenerator`. Both delegate to `self._cst._py_gen.class_name_for_rule_node(rule_name)` and append a suffix — the same naming conventions encoded in `RustCstGenerator._label_enum_rust_name` (line 400, `gsm2tree_rs.py`) and in `_child_enum_block` (where `f"{class_name}Child"` is used inline, e.g. line 497 of `gsm2tree_rs.py`).

**Existing function/utility:**
- `RustCstGenerator._label_enum_rust_name(class_name)` — `gsm2tree_rs.py:400`
- Child enum name is `f"{class_name}Child"` computed inline in `_child_enum_block` — `gsm2tree_rs.py:497`

`RustParserGenerator` already holds a `RustCstGenerator` as `self._cst`; it could call `self._cst._label_enum_rust_name(class_name)` (currently private static) instead of re-encoding the `+ "Label"` suffix, and could derive child enum names via the same class rather than repeating the `+ "Child"` pattern.

**Consequence:** If the enum naming convention changes (e.g. to avoid a collision, or to add a prefix), it must be updated in at least three places: `gsm2tree_rs._label_enum_rust_name`, `gsm2parser_rs._label_enum_name`, and the inline `f"{class_name}Child"` usage. A mismatch would produce parser code referencing enum names that don't exist in the generated CST, causing a compile error only caught downstream in cargo.
