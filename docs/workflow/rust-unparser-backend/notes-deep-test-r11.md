# Test review — increment 31 (committed fixture `.pyi` + pyright consumer tests, OQ-3)

Commit range: 0494f31..fabdc5a

## Summary

The new pyright consumer tests (`tests/test_rust_unparser_pyi.py`) are substantive.
`test_consumer_misuse_is_type_error` is the key test and it genuinely proves the stub
constrains types rather than degrading to `Any` — passing `int` where `_proto.Num` is
required is a `reportArgumentType` error, which cannot occur under an `Any`-typed surface.
The fixture setup correctly mirrors the project's `extraPaths` configuration so the
committed stub is resolved as a downstream consumer would resolve it.

The updated assertions in `test_rust_unparser_generator.py` (replacing
`assert "import typing" in pyi` with `assert "import typing" not in pyi`, and updating
the `typing.Optional[...]` → `str | None` / `Doc | None` string checks) are correct and
match the generator change.

Two genuine gaps follow.

---

## Findings

### test-1

**File:line**: `tests/test_rust_unparser_pyi.py:53` (`_CONSUMER_OK`, used by
`test_consumer_pyright_clean`)

**What's wrong**: The consumer assigns the return value of `unparse_num` to a variable
annotated `str | None`:

```python
rendered: str | None = u.unparse_num(node, max_width=80, indent_width=4)
```

This assignment is valid whether the stub declares the return type as `str | None`, as
plain `str`, or even as `Any`; all three are assignable to `str | None`. As a result,
`test_consumer_pyright_clean` cannot detect a regression that strips `| None` from the
return type in the committed stub. The same holds for the `Doc | None` return of
`unparse_num_doc`: assigning to `doc: unp.Doc | None` would still type-check if the
stub returned bare `Doc`.

Generator unit tests (`test_generate_pyi_per_rule_methods`, etc.) guard generator
regressions via exact string matching, so a generator-level change would be caught.
But a manual edit to the committed `fltk/_stubs/rust_parser_fixture/unparser.pyi` —
e.g., narrowing every `-> str | None:` to `-> str:` — is invisible to both the
generator tests and the pyright consumer tests. `test_committed_stub_artifacts_exist`
does not check for the `| None` substring, and `make typecheck` would not flag a stub
returning `str` used in a `str | None` context.

**Consequence**: A silent regression in the committed stub's return-type annotations
(manual edit or future generator change) would not be caught by the consumer-facing
tests. Downstream consumers depending on the `| None` return to detect "could not
unparse" would get incorrect type information with no test catching it.

**Fix**: Add a second bad-consumer snippet that assigns `unparse_num`'s return directly
to a `str`-annotated variable (no `| None`) and expect a `reportAssignmentType` error
in `consumer_pyright_diagnostics`. Example:

```python
_CONSUMER_BAD_NARROWING = """\
from __future__ import annotations

import rust_parser_fixture.unparser as unp
import tests.rust_parser_fixture_cst_protocol as proto


def bad_narrow(node: proto.Num) -> None:
    u = unp.Unparser()
    result: str = u.unparse_num(node)  # should error: str | None not assignable to str
"""
```

Write this to `consumer_bad_narrowing.py` in the fixture tmpdir and add a test:

```python
def test_consumer_return_none_is_part_of_type(consumer_pyright_diagnostics):
    errors = _diags_for_file(consumer_pyright_diagnostics, "consumer_bad_narrowing.py")
    assert any(d.get("rule") in ("reportAssignmentType", "reportArgumentType") for d in errors), (
        "Expected a type error assigning str | None to str; "
        "stub may have dropped | None from unparse_num return type."
    )
```

---

### test-2

**File:line**: `tests/test_rust_unparser_pyi.py:55-56` (`_CONSUMER_OK`,
`doc.render(max_width=40)` call site)

**What's wrong**: In `_CONSUMER_OK`, `doc.render(max_width=40)` is returned from a
function typed `-> str | None`. If `Doc.render()` degraded to returning `Any` (e.g., a
future generator change or manual stub edit), `return Any` is still assignable to
`str | None` and pyright would emit no error, leaving `test_consumer_pyright_clean`
passing. `test_consumer_misuse_is_type_error` does not involve `render()` at all. No
test proves pyright sees `render()` as returning a constrained `str`, not `Any`.

**Consequence**: A regression in the committed stub where `Doc.render()` returns `Any`
or a wrong concrete type would not be caught. Downstream consumers who rely on `render()`
returning `str` (e.g., for type-safe string composition) would lose type safety without
any test alerting to the change.

**Fix**: Add a snippet that feeds `render()`'s return into a `str`-only context that
would fail if the return type were not `str`. The simplest approach is a function typed
`-> str` that returns `doc.render()` directly (making the `| None` case unreachable to
isolate the question):

```python
_CONSUMER_BAD_RENDER = """\
from __future__ import annotations

import rust_parser_fixture.unparser as unp
import tests.rust_parser_fixture_cst_protocol as proto


def bad_render(node: proto.Num) -> None:
    u = unp.Unparser()
    doc: unp.Doc | None = u.unparse_num_doc(node)
    if doc is not None:
        result: int = doc.render()  # should error: str not assignable to int
"""
```

This would be a pyright error if `render()` returns `str`, and would silently pass if
`render()` returned `Any`. So the test should assert an error is present, proving the
return type is genuinely constrained.
