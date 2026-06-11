Style note: concise, precise, complete, unambiguous. No padding.

Commit reviewed: b107645

---

## quality-1

**File:line:** `tests/test_rust_parser_parity_fixture.py:126-133`

**Issue:** PARTIAL handling in the fixture parity test has a three-branch conditional with a silent fall-through. When `expected.pos != 0` AND `py_result is None`, the branch falls through to `None` — no assertion fires, no parity check, no failure. This means a corpus entry annotated `PARTIAL(5)` passes vacuously if the Python parser returns `None`. The fegen parity test (`test_rust_parser_parity_fegen.py:109-114`) does not have this hole: it asserts both parsers are non-`None` unconditionally.

**Consequence:** A parity regression where the Python parser fails on a PARTIAL-annotated input will go undetected. The parity suite's correctness guarantee quietly degrades on fixture inputs.

**Fix:** Replace the fixture PARTIAL branch with the same unconditional form used in the fegen test:
```python
elif isinstance(expected, PARTIAL):
    assert py_result is not None, "Python parser failed unexpectedly"
    assert rust_result is not None, "Rust parser failed unexpectedly"
    assert py_result.pos == expected.pos, ...
    assert rust_result.pos == expected.pos, ...
    assert_cst_equal(py_result.result, rust_result.result)
```
The special case `expected.pos == 0 and py_result is None` was likely defensive coding for an ambiguous case; if a corpus entry genuinely expects `pos=0` partial match, the design note §2.4 says FAIL is the right sentinel (not PARTIAL) — remove the special case and use FAIL instead, or assert both parsers return `None` explicitly (not silently skip).

---

## quality-2

**File:line:** `tests/parser_parity.py:71` — `_assert_messages_equiv` is underscore-prefixed (internal) but is imported and used directly by `tests/test_rust_parser_parity_fegen.py:25,342,352,361` for comparator self-tests.

**Issue:** The self-tests in `test_rust_parser_parity_fegen.py` reach into the internal `_assert_messages_equiv` because the public `assert_error_equiv` requires live parser objects and `terminals`, making it inconvenient for hand-built inputs. This creates a leaky abstraction: the comparator self-tests are coupled to the internal helper's exact signature. If `_assert_messages_equiv` is ever refactored (e.g., signature changes, intermediate representation changes), the external import breaks with no indication that it is part of the public surface.

**Consequence:** Every future refactor of `parser_parity.py`'s internals must check all external callers; the `_` prefix convention gives a false signal that the function has no external contract.

**Fix:** Either (a) export `_assert_messages_equiv` without the underscore prefix since it is in fact part of the public test-helper surface, or (b) add a public wrapper `assert_messages_equiv(msg_a: str, msg_b: str) -> None` that accepts raw message strings and calls `_assert_messages_equiv(*_parse_error_message(msg_a), *_parse_error_message(msg_b))`, removing the need for callers to know about the internal representation. Option (b) is cleaner: callers pass strings, implementation detail stays internal.

---

## quality-3

**File:line:** `Makefile:50` — `cargo-clippy` target adds `rust_cst_fegen` and `rust_parser_fixture` python-on clippy, but `cargo-check` at line 42-43 adds only `rust_parser_fixture --features python`. The `rust_cst_fegen` python-on compile check was already present via `cargo-check` (line 42 checks it with default features, which are python-on for that crate), but it is not explicit. Meanwhile the two new `cargo-clippy` lines for the test crates are a superset of `cargo-check` for those same crates, making the relationship between `cargo-check` and `cargo-clippy` asymmetric across the crates: workspace check, `rust_cst_fegen` default, `rust_parser_fixture` python-on in `cargo-check`; workspace clippy, `rust_cst_fegen` default, `rust_parser_fixture` python-on in `cargo-clippy`. This inconsistency is not wrong but will confuse future maintainers adding more crates — there is no obvious rule for which targets belong in `cargo-check` vs `cargo-clippy`.

**Consequence:** Low immediate impact, but adds cognitive overhead when extending the CI matrix in Phase 4. The pattern propagates: future crates will have unclear placement.

**Fix:** Add a short comment block above `cargo-check` and `cargo-clippy` explaining the policy (e.g., "cargo-check is fast compile; cargo-clippy implies cargo-check; test crates added to both"). Alternatively, consolidate: `cargo-check` drops test-crate lines and `cargo-clippy` runs them all (since clippy implies check). Pick one pattern and apply it consistently.

---

## quality-4

**File:line:** `fltk/fegen/gsm2parser_rs.py:65-151` — `_gen_python_bindings` builds the entire output by appending string literals to a list, one `lines.append("literal")` per line. This is the only method in the file that uses this style; every other generation method in `gsm2parser_rs.py` uses multi-line string templates with f-string interpolation (e.g., `_gen_struct`, `_gen_apply_fns`, `_gen_regex_compile_test`, etc.).

**Issue:** The structural boilerplate (the 30+ fixed lines of `PyApplyResult`, `PyParser` skeleton, `check_pos`, `register_classes`) is not parametric over the grammar — it is identical for every generated file. Writing it as 35 individual `lines.append("...")` calls instead of a single template string makes the structure harder to read, harder to diff against the design's code block, and inconsistent with every other method in the same file.

**Consequence:** Maintenance cost: any change to the boilerplate (e.g., adding a method to `PyParser`, changing the `check_pos` logic) requires editing ~10 individual `append` lines instead of a single template string. Future generators will follow the append pattern thinking it is the established style, eroding readability.

**Fix:** Split `_gen_python_bindings` into two parts: a fixed-template string for the invariant skeleton (from the `mod python_bindings {` opening through `check_pos`, the `#[pymethods] impl PyParser {` opening, and `register_classes` + closing) and a per-rule loop for only the `apply__parse_<rule>` methods — the only genuinely grammar-parametric part. Use a triple-quoted f-string or `.format()` for the skeleton, matching the existing style in the file.
