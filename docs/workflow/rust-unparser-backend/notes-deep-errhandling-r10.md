## errhandling-1

**File:** `tests/rust_parser_fixture/src/native_tests.rs:1021-1023`

**Broken error path:** The `render_native!` macro's unparse-failure path loses its source-text context. When `Unparser::new().$unparse(&*guard)` returns `None`, the `.expect("native unparse must succeed")` fires with no indication of what input caused the failure. By contrast, the parse-failure arm one line above deliberately includes `{src:?}` and `parser.error_message()` in its panic.

**Why — where the error goes:** The test `native_unparse_simple_tokens` (line 1035) invokes the macro three times inside a single `#[test]` body with three distinct inputs ("123", "hello", "world") and three distinct unparse methods. If any of the three unparse calls returns `None`, the panic message "native unparse must succeed" gives no indication which input or which method triggered it. The rule name is similarly absent; the test function name identifies the scenario at a high level, but any future test that adds more corpus entries to the same body will face the same ambiguity.

**Consequence:** When an unparse regression surfaces here, the on-call path is: test name → look at test body → guess which of N calls fired → add tracing manually. The parse-failure arm already sets the right precedent; the unparse-failure arm does not follow it.

**What must change:** Replace `.expect("native unparse must succeed")` with `.unwrap_or_else(|| panic!("native unparse failed for {src:?} (method {}): returned None", stringify!($unparse)))`. This matches the information already captured for the parse-failure arm and eliminates the guessing step when the expect fires.

---

## errhandling-2

**File:** `tests/unparser_parity.py:26-34` (`assert_unparse_parity`)

**Broken error path:** When both the Python and Rust unparsers return `None` for a corpus entry, `assert_unparse_parity` exits normally. The only guard is:

```python
assert (py_str is None) == (rust_str is None), ...
if py_str is not None:
    assert py_str == rust_str, ...
```

`True == True` passes the first assert; the second branch is skipped. The calling test (`test_unparse_parity_fltkfmt`, `test_unparse_parity_default`) sees a green result.

**Why — where the error goes:** The corpus in `test_rust_unparser_parity_fixture.py` is explicitly constructed to be fully parseable and intended to be fully unparseable — the corpus comment says the entries are "chosen to exercise the `.fltkfmt` config paths … plus default-spacing rules, union labels, multibyte text, suppressed/included terms, sub-expression, and bounded-depth recursion." A corpus entry where both backends return `None` means neither backend handled a case that was supposed to be covered. That failure is invisible: the function returns, the test is green, and there is no log or structured error.

**Consequence:** A regression that silences both backends for a particular rule (e.g., both `unparse_arrow` methods return `None` after a generated-code change) would pass all parity tests. The signal the test is designed to provide — that both backends agree on a known-good corpus — is lost for the broken case. An on-call engineer looking at a green test run has no indication that the unparser silently dropped a rule. The CI note in the module docstring ("A CI lane where every test here is skipped is a failure signal") covers the skip case but not the mutual-None case.

**What must change:** After the success-agreement check, add an explicit assertion that unparse succeeded for all corpus entries:

```python
assert py_str is not None, (
    f"[rule={rule!r} text={text!r} w={max_width} i={indent_width}] "
    f"both backends returned None — unparse failed for a corpus entry that must succeed"
)
```

Alternatively, the function could accept an `expect_success: bool = True` parameter, but for the existing call sites (corpus entries chosen to succeed) the unconditional assert is correct and does not require any call-site change.

---

Commit reviewed: `fa22e182702d3ea1c1ec5e464345ab006941c9e9`
