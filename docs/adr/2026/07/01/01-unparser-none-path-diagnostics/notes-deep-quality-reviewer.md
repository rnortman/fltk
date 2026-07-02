# Quality review — unparser-none-path-diagnostics

Reviewed: `1d277ce..462cf1c` (single commit 462cf1c, "unparser: halt loudly on the two silent-None diagnostic paths").

Overall: the change is well-shaped — policy applied symmetrically to both backends, TODO fully retired (entry + both in-code comments), docstrings updated to describe current behavior rather than history, new runtime helper documented, and the new tests follow each file's established patterns (try/finally `sys.modules` cleanup in `test_unparser.py`, `#[should_panic]` in `native_parser_tests.rs`). Two findings.

## quality-1: fourth inline copy of the `fltk.unparse.pyrt` module reference instead of a `_get_pyrt_module()` helper

- **Location:** `fltk/unparse/gsm2unparser.py:1340-1346` (new `pyrt_module = iir.VarByName(name="fltk.unparse.pyrt", ...)` block).
- **Issue:** `UnparserGenerator` already encapsulates exactly this construction pattern for its other runtime modules — `_get_combinators_module()` (line 362) and `_get_accumulator_module()` (line 371) exist precisely so the 5-line `iir.VarByName(... cname="module" ...)` block isn't repeated. The `fltk.unparse.pyrt` reference, however, is built inline at three pre-existing sites (lines 388, 958, 1775), and this change adds a fourth identical copy rather than extracting the obvious `_get_pyrt_module()` sibling.
- **Consequence:** The copy count is now high enough that the next pyrt call site will copy it again (this change itself demonstrates the propagation). Any change to how module references are modeled — or a module rename — now touches four scattered sites instead of one helper, and the file carries two competing conventions (helper for combinators/accumulator, inline for pyrt) that a future author must guess between.
- **Fix:** Add `_get_pyrt_module()` next to `_get_combinators_module`/`_get_accumulator_module`, use it at the new site, and convert the three pre-existing inline copies (lines 388, 958, 1775) in the same commit — they are byte-identical, so this is mechanical.

## quality-2: identical multi-line panic-string assertion copy-pasted across five generator tests

- **Location:** `tests/test_rust_unparser_generator.py:801-805`, `:828-831`, `:855-858`, `:869-872`, `:1180-1183`.
- **Issue:** The same three-line expected-panic-literal assertion (`'panic!("unparse_r: cannot extract text for regex term label \`...\` at child position {}: span.text() returned None for {:?}", pos, span);'`) is pasted into five tests, varying only in the item descriptor (`label \`foo\``, `label \`bar\``, `(unlabeled)`, `label \`item\``-style). This is copy-paste with slight variation that a tiny helper, e.g. `_expected_span_text_panic(rule: str, item_desc: str) -> str`, would unify.
- **Consequence:** Any future rewording of the site-2 diagnostic (even punctuation) requires five coordinated edits in this file plus the runtime test; a partially updated set silently keeps testing stale wording only if the generator also half-changes, which is exactly the drift a single source of expected text prevents. The variation between copies also obscures the one thing each test actually varies (the item descriptor).
- **Fix:** Extract a module-level helper building the expected panic string from `(rule, item_desc)` and assert against it in all five tests; the analogous site-1 string appears only once (`:1935-1938`) and can stay literal.

## Checked and clean

- Comment hygiene: no references to the design doc or workflow artifacts in code; updated docstrings describe current behavior (the `pyrt.py:48` / cross-file line citations follow this generator file's pre-existing citation convention).
- No workarounds: both silent paths are fixed at the source in the generators, not papered over at call sites; the out-of-scope newline-count path is a deliberate, documented non-goal.
- Observability: site-2 panic carries rule, item descriptor, child position, and span `Debug` (including `has_source`), which the runtime test pins; site-1 message carries rule + position, matching the stated no-span-contents convention.
- No new parameters, state, or stringly-typed surfaces; `rust_str_lit` reuse for embedded names matches existing emission style.
