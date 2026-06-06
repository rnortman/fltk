# Exploration: TODO(test-class-is-type-body) Verification

Concise. Precise. No fluff. Audience: smart LLM/human.

## Claimed location and text

TODO.md slug `test-class-is-type-body` points to
`tests/test_fegen_rust_cst.py:67`.

**Actual code at that location** (`tests/test_fegen_rust_cst.py:63-71`):

```python
class TestAllClassesImportable:
    @pytest.mark.parametrize("cls", ALL_CLASSES, ids=ALL_CLASS_IDS)
    def test_class_is_type(self, cls: type) -> None:
        """AC-7: Each class is a real Python type (importable and callable)."""
        # TODO(test-class-is-type-body): `isinstance(cls, type)` passes for any
        # imported class including a misimported alias. Import success is the real
        # AC-7 check; a construction test (cls()) would be stronger. The AC-8a
        # tests already cover construction for all 14 classes.
        assert isinstance(cls, type)
```

Line 67 is the first `# TODO(...)` comment line. Line 71 is `assert isinstance(cls, type)`. Citation is accurate.

## Is the assertion as described?

Yes. `assert isinstance(cls, type)` at line 71. This is a single assertion. The parametrize list (`ALL_CLASSES`, derived from `CLASS_LABEL_INFO` at lines 36-55) contains 14 class objects imported at module scope (lines 12-27). The assertion fires once per class.

The claim that `isinstance(cls, type)` passes for any imported object including a misimported alias is **correct with nuance**: it passes for any real Python `type` (i.e., any class), but would fail for a non-class object (e.g., an integer or None). A misimported alias that is itself a class would still pass. The assertion does not verify the specific identity of each class (e.g., it would pass if `Grammar` accidentally resolved to `Rule`).

## Is `cls()` construction already covered by AC-8a tests?

Yes. `TestConstructionDefaultSpan.test_default_span_is_unknown` at lines 80-84:

```python
@pytest.mark.parametrize("cls", ALL_CLASSES, ids=ALL_CLASS_IDS)
def test_default_span_is_unknown(self, cls: type) -> None:
    """AC-8: Each class constructs with default span == UnknownSpan."""
    node = cls()
    assert node.span == UnknownSpan
```

`ALL_CLASSES` is the same 14-element list (line 54: `ALL_CLASSES = [cls for cls, _, _ in CLASS_LABEL_INFO]`). So `cls()` is called for all 14 classes in AC-8a. Multiple other AC-8 tests also call `cls()` at lines 104, 140, 141, 153-155, 178-180, 195, 206-207, 219-221.

If any class fails to construct, AC-8a `test_default_span_is_unknown` catches it before `test_class_is_type` would even be relevant.

## Is the proposed fix shape feasible?

The two options stated in TODO.md:

1. **Replace `isinstance(cls, type)` with `cls()`**: Feasible. `cls()` is already called in AC-8a for all 14 classes; adding it here would be redundant but not harmful. It would be a stronger identity check in the sense that it exercises construction, but it still does not verify that `Grammar` is specifically `Grammar` rather than another class.

2. **Remove the assertion entirely**: Feasible. Import success (the `from fltk._native.fegen_cst import ...` block at lines 12-27) is the actual AC-7 check — if an import fails, the module fails to load and all tests in the file fail. The `isinstance(cls, type)` assertion adds no new signal for correctly imported classes.

## Are there blockers?

None identified. The test file has no cross-test dependencies. Removing or replacing the assertion in `test_class_is_type` does not affect any other test.

## Is this papering over a deeper problem?

No deeper problem detected. The structure is sound:
- AC-7 (importability) is enforced by module-level imports at lines 12-27.
- AC-8a (construction) covers `cls()` for all 14 classes at lines 80-84.
- The `isinstance(cls, type)` assertion is genuinely redundant given the above two mechanisms.

The TODO accurately characterizes the situation. No hidden failure mode is masked by keeping the assertion. Removing it (or replacing it with `cls()`) is a cleanup, not a fix.

## Summary of verified facts

| Claim | Verdict |
|---|---|
| File and line cited correctly | Yes — TODO comment at line 67, assertion at line 71 |
| Assertion is `isinstance(cls, type)` | Yes |
| All 14 classes parametrized | Yes — `ALL_CLASSES` from `CLASS_LABEL_INFO` (line 54) |
| `cls()` covered by AC-8a | Yes — `test_default_span_is_unknown` calls `cls()` for all 14 (line 83) |
| Fix shape feasible (remove or replace) | Yes — no blockers |
| Papering over a deeper problem | No |
