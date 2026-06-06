# Design: test-class-is-type-body

Concise. Precise. No padding. Audience: smart LLM/human.

## Root cause / context

`TestAllClassesImportable.test_class_is_type` (`tests/test_fegen_rust_cst.py:63-71`)
asserts `isinstance(cls, type)` once per generated class, parametrized over
`ALL_CLASSES` (14 entries, `tests/test_fegen_rust_cst.py:54`, derived from
`CLASS_LABEL_INFO` at lines 36-51).

The predicate `isinstance(cls, type)` is true for *every* class object. It
cannot distinguish a correct import from a misimported-but-still-a-class alias
(e.g. `Grammar` resolving to `Rule`). So beyond "the module-level import block
ran," it carries zero signal.

The two guarantees it nominally protects are already enforced elsewhere:

- **AC-7 importability** — enforced by the top-of-file import block
  (`tests/test_fegen_rust_cst.py:12-27`). A failed `from
  fltk._native.fegen_cst import (...)` raises at collection time and fails the
  entire module, so no `test_class_is_type` body is needed to surface an import
  failure.
- **AC-8 construction (`cls()`)** — covered for all 14 classes by
  `TestConstructionDefaultSpan.test_default_span_is_unknown`
  (`tests/test_fegen_rust_cst.py:80-84`), which calls `cls()` per class. Further
  AC-8 tests call `cls()` again (lines ~104, 140-141, 153-155, 178-180, 195,
  206-207, 219-221).

The `TODO(test-class-is-type-body)` comment (lines 67-70) and `TODO.md` entry
(`TODO.md:23-25`) record this redundancy and propose remove-or-replace.

This is test cleanup, not a behavior change. No generated public API is touched,
so the CLAUDE.md drop-in / no-annotation-churn constraints do not apply.

## Proposed approach

Delete the `test_class_is_type` method and its `TODO` comment from
`TestAllClassesImportable` (`tests/test_fegen_rust_cst.py:64-71`).

Outcome decisions:

- Do **not** replace it with a `cls()` check. Construction is already asserted
  by AC-8a for the identical `ALL_CLASSES` list; re-adding `cls()` here only
  re-duplicates AC-8a.
- Remove the now-empty `TestAllClassesImportable` class and its AC-7 section
  banner comment (`tests/test_fegen_rust_cst.py:58-60`) so no empty shell
  remains. Keep the module docstring's AC-7 mention
  (`tests/test_fegen_rust_cst.py:3`) — it already correctly attributes AC-7 to
  "14 classes compile," which the import block satisfies.
- Keep `ALL_CLASSES`, `ALL_CLASS_IDS`, and `CLASS_LABEL_INFO` intact — AC-8
  tests parametrize over them.
- Keep the import block (lines 12-27) intact — it is the real AC-7 enforcement.

Remove the tracking metadata:

- `TODO.md` entry `## test-class-is-type-body` (`TODO.md:23-25`).
- The `TODO(test-class-is-type-body)` comment (deleted with the method).

Files touched (tests/docs only):

- `tests/test_fegen_rust_cst.py` — delete method + comment (+ empty class +
  section banner).
- `TODO.md` — delete the slug entry.

## Edge cases / failure modes

- **Empty class left behind.** If only the method is deleted,
  `TestAllClassesImportable` becomes an empty class — a lint/clarity wart.
  Mitigation: remove the class and its section banner, per above.
- **`ALL_CLASSES` mistakenly removed.** Would break every AC-8 parametrization.
  Mitigation: the symbols are defined at module scope and shared; the change
  touches only the method body region (lines 58-71). Do not edit lines 36-55.
- **Import block mistakenly trimmed.** Would silently drop AC-7 enforcement.
  Mitigation: leave lines 12-27 untouched; verification step re-confirms all 14
  names still imported.
- **An import genuinely breaks later.** Still caught — module fails to collect.
  The deleted test added nothing here.

## Test plan

No new tests. After the change, the test suite must still:

- Import all 14 classes at module scope (`tests/test_fegen_rust_cst.py:12-27`).
- Exercise `cls()` for all 14 classes via AC-8a
  `test_default_span_is_unknown`.
- `uv run pytest tests/test_fegen_rust_cst.py` passes (the only behavioral
  change is one fewer parametrized test group, 14 fewer no-signal cases).

Verification checklist:

- `test_class_is_type` absent.
- `TODO(test-class-is-type-body)` comment absent.
- `TODO.md` slug entry absent.
- 14-name import block present.
- `ALL_CLASSES` / `ALL_CLASS_IDS` / `CLASS_LABEL_INFO` present.

## Open questions

None. The request fixes the shape (remove, do not replace) and the exploration
confirms no blockers.
