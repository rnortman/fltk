# Deep security review — rust-unparser-backend batch 7

Commit reviewed: 1fcae0bbe0063b83b1883eb439ababc9da6916d4 (base 72ea1e4252ddea2918b725418716b55e531254b8)

Scope: generator changes (`fltk/unparse/gsm2unparser_rs.py`: separator/trivia
processing, trivia helper methods, emitted PyO3 wrapper), Rust core additions
(`accumulator.rs` `last_was_trivia()` accessor, `doc.rs` `separator_spec`
constructor), and tests.

## No findings.

Checks performed and why each is clean:

- **Code-generation / injection (free-form strings).** Every free-form string that
  reaches the emitted Rust — literal text (`_gen_literal_term_body`,
  `_gen_suppressed_item_body`) and config `Text`/spacing (`_doc_to_rust_expr`) — is
  interpolated through `rust_str_lit`, which escapes backslash, double-quote, and
  control/DEL characters before it lands inside a `text("…")` Rust literal. No new
  unescaped free-form string interpolation was introduced in this batch.
  `HardLine.blank_lines` / `preserve_blanks` are interpolated as integers from a
  typed config field, not free text.

- **Code-generation (interpolated identifiers).** Rule names, class names, label
  variants (`snake_to_upper_camel`), and `preserve_node_names` entries are
  interpolated raw as Rust identifiers, but they are grammar/CST-derived names
  constrained by the grammar's lexical rules (and `preserve_node_names` is filtered
  against the trivia rule's real child-class names in
  `_gen_has_preservable_trivia_method`, so an unknown name is dropped rather than
  emitted). This is the same build-time, developer-controlled pattern already used by
  the CST/parser backends and is unchanged here; the grammar author is the build
  operator, so this is not a runtime trust boundary.

- **PyO3 / FFI boundary (emitted wrapper, `_gen_python_bindings`).** The wrapper
  accepts `node: PyRef<'_, cst::Py{CN}>` — pyo3 argument extraction rejects any
  Python object that is not exactly that pyclass, so a pure-Python CST cannot be
  passed in. `max_width`/`indent_width` are `usize` (negative Python ints are
  rejected at extraction). The body uses `node.shared().read()` (parking_lot
  read-lock, no poisoning/`Result`), contains no `unsafe`, and only forwards two
  caller-supplied integers into the in-process renderer. The two integers are the
  caller's own render config within the caller's own process — no attacker-controlled
  data crosses a privilege boundary, so the boundary is not security-relevant beyond
  robustness (any renderer behavior for `max_width == 0` is out of this diff's scope).

- **Runtime memory safety in generated trivia code.** Every `node.children()[pos]`
  index in the new separator/trivia branches is guarded by a preceding
  `pos < node.children().len()` bounds check; `pos` only ever increments. No unchecked
  indexing or `usize` underflow.

- **Rust core additions.** `DocAccumulator::last_was_trivia()` is a pure bool
  accessor; `doc::separator_spec` wraps `Option<Doc>` fields in `Rc`. No `unsafe`, no
  panic paths, no secrets.

- **Secrets.** None in the diff (generator, core, or tests).
