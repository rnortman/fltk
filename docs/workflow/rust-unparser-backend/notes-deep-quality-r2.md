# Quality review — rust-unparser-backend batch 2

Commit reviewed: e65e4f66bf2d466637df6f94744fa85abc7d239c

---

## quality-1

**File:line**: `fltk/unparse/gsm2unparser_rs.py:23`

`gsm2unparser_rs.py` imports `_rust_str_lit` — a private, single-underscore symbol — directly from `gsm2parser_rs` in production code:

```python
from fltk.fegen.gsm2parser_rs import _rust_str_lit
```

`gsm2parser_rs.py` is the parser-generator module, not a shared-utilities library. `_rust_str_lit` is its internal escaping helper; the underscore signals it is not part of the module's public surface. `docs/adr/2026/06/11-rust-naming-shared/design.md` §"Not changed" explicitly decided against creating a shared utility module for `_rust_str_lit`, but that decision was made when no production cross-module consumer existed. There is now one.

**Consequence**: `gsm2unparser_rs.py` is coupled to `gsm2parser_rs.py`'s private surface. If `_rust_str_lit` is renamed, moved, or refactored in the parser generator (reasonable as the module grows or is reorganised), `gsm2unparser_rs.py` will fail at import time with no compile-time signal. More importantly, every future Rust code-generation module that needs to emit string literals (PyO3 wrapper, CLI wiring, fixture generator) will face the same choice: import the same private symbol or copy the logic. Either branch propagates the problem — the import makes `gsm2parser_rs` an accidental utilities module; the copy creates N diverging implementations of 12 lines of escaping logic. The existing CST-import logic (`segments[-1] == "cst"` branch) is already copied verbatim into `_gen_header` with the comment "mirrors gsm2parser_rs._gen_header", showing the propagation is already underway.

**Fix**: Three options in ascending scope:

1. **Publicize in place**: Remove the leading underscore from `gsm2parser_rs.py` (rename `_rust_str_lit` → `rust_str_lit`); update the one existing test import (`fltk/fegen/test_gsm2parser_rs.py:8`) and the new production import. Cost: one-line rename, two import updates, zero behaviour change. This makes the dependency intentional and visible.

2. **Inline**: Define a module-private copy in `gsm2unparser_rs.py`. Twelve lines, self-contained, no new imports. Acceptable while only two consumers exist; creates a known duplication that can be extracted later.

3. **Extract**: Move `rust_str_lit` (and the CST-import branch logic) to a new `fltk/fegen/rs_codegen_util.py` and import from there in both generators. Correct long-term destination; appropriate once a third generator arrives.

Option 1 is the lowest-cost fix that unblocks the production use without incurring duplication.

---

## quality-2

**File:line**: `crates/fltk-unparser-core/src/render.rs:77–88`

`Output::append_content` guards its body with two separate `!text.is_empty()` checks, a direct port of the Python closure's two `if text:` guards (`renderer.py:64–72`):

```rust
fn append_content(&mut self, text: &str, indent: usize) {
    if !text.is_empty() && self.at_beginning_of_line {
        // emit indentation
        self.current_column = indent;
        self.at_beginning_of_line = false;
    }
    if !text.is_empty() {          // <— redundant guard
        self.result.push_str(text);
        self.current_column += text.chars().count();
    }
}
```

The Python form was natural (two separate `if text:` guards on two `nonlocal` mutation blocks in a closure). In Rust, the idiomatic form is an early return that makes the short-circuit unambiguous:

```rust
fn append_content(&mut self, text: &str, indent: usize) {
    if text.is_empty() {
        return;
    }
    if self.at_beginning_of_line {
        for _ in 0..indent { self.result.push(' '); }
        self.current_column = indent;
        self.at_beginning_of_line = false;
    }
    self.result.push_str(text);
    self.current_column += text.chars().count();
}
```

**Consequence**: A reader must mentally verify that the two guards are equivalent before understanding the function. As written, the second guard is dead work whenever `text` is empty (the first guard already returned via short-circuit or was skipped). If the function is extended — say, to track multi-line text or add a byte-count field — a developer following the existing pattern would add a third `if !text.is_empty()` block, compounding the redundancy.

**Fix**: Replace the two-guard form with a single early return on empty text, then handle indentation and content emission unconditionally.
