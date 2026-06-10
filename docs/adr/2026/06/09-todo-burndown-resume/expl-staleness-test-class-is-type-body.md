# Staleness check: design for TODO(test-class-is-type-body)

Concise. Precise. No padding. Audience: smart LLM/human.

Checked against HEAD af6e6f3. Design written at commit of 2026-06-06; commit 4c8f0ad reworked Rust CST between then and now.

## Design claims vs. current working tree

### Line citations — shifted

The design and exploration cite specific line numbers that have shifted since writing.

| Symbol | Design cite | Actual line (HEAD) |
|---|---|---|
| `CLASS_LABEL_INFO` definition | exploration: lines 36-55 | line 43 (definition), entries through line 61 |
| `ALL_CLASSES` derivation | design: "line 54" | line 64 |
| `ALL_CLASS_IDS` | design: line 54 area | line 65 |
| `TestAllClassesImportable` class | design: lines 63-71 | lines 73-81 |
| `test_class_is_type` method | design: lines 64-71 | lines 74-81 |
| `TODO(test-class-is-type-body)` comment | design/exploration: lines 67-70 | lines 77-80 |
| `assert isinstance(cls, type)` | exploration: line 71, request: line 71 | line 81 |
| AC-7 section banner comment | design: lines 58-60 | lines 68-70 |
| `TestConstructionDefaultSpan` class | design/exploration: lines 80-84 | lines 89-94 |
| `test_default_span_is_unknown` | exploration: line 83 | line 91-94 |
| Import block | design: lines 12-27 | lines 12-27 (unchanged) |

The `CLASS_LABEL_INFO` tuple shape also changed: it is now a 4-tuple `(class, label_for_Label_access, label_for_roundtrip, child_factory)` (line 44), whereas the design/exploration describe a 3-tuple. The derivation of `ALL_CLASSES` reflects this: `[cls for cls, _, _, _ in CLASS_LABEL_INFO]` (line 64) not `[cls for cls, _, _ in CLASS_LABEL_INFO]`. This is a post-design addition.

### Structural claims — still accurate

- `TestAllClassesImportable` class with `test_class_is_type` method: present at lines 73-81.
- `TODO(test-class-is-type-body)` comment: present at lines 77-80 (`tests/test_fegen_rust_cst.py`).
- `assert isinstance(cls, type)` assertion: present at line 81.
- Import block at lines 12-27 importing all 14 classes: intact and unchanged.
- `ALL_CLASSES` and `ALL_CLASS_IDS` defined at module scope (lines 64-65): present.
- `TestConstructionDefaultSpan.test_default_span_is_unknown` calling `cls()` for all 14 classes via `ALL_CLASSES`: present at lines 89-94.
- 14-entry `CLASS_LABEL_INFO`: still 14 entries (lines 43-61).

### TODO.md entry — still live

`TODO.md` entry `## test-class-is-type-body` is present at lines 19-21:

> Strengthen or remove the `isinstance(cls, type)` assertion in `TestAllClassesImportable.test_class_is_type`. The assertion passes for any imported object including a misimported alias; import success is the real AC-7 check. Option: replace with `cls()` construction (already covered by AC-8a tests). Location: `tests/test_fegen_rust_cst.py:67`.

The location cite in `TODO.md` (`tests/test_fegen_rust_cst.py:67`) is stale — current line is 77 — but the entry is live and refers to the correct target.

### Impact on design applicability

The design's proposed changes are still applicable. The code to be deleted is still present:
- `TestAllClassesImportable` class (lines 73-81)
- `TODO(test-class-is-type-body)` comment (lines 77-80)
- `assert isinstance(cls, type)` (line 81)
- AC-7 section banner (lines 68-70)

The design's "do not edit lines 36-55" guard on `CLASS_LABEL_INFO` is stale as a literal line range; current `CLASS_LABEL_INFO` spans lines 43-61. The guard's intent (do not remove `CLASS_LABEL_INFO`/`ALL_CLASSES`/`ALL_CLASS_IDS`) is still valid.

The design's proposed deletion region is lines 64-71 (old numbering), which corresponds to approximately lines 68-81 in the current file (the AC-7 banner plus `TestAllClassesImportable`).

All logical claims about what the code does and why the change is safe remain accurate. Line numbers in the design and exploration are stale by approximately +9 lines for symbols after the `CLASS_LABEL_INFO` block.

## Commit 4c8f0ad impact

Commit 4c8f0ad ("Rust CST holds native Span and children — no Python objects") reworked the Rust CST internals and added the 4th element to `CLASS_LABEL_INFO` tuples (the `child_factory` column) and new AC-8d/8e test classes. This is what caused the line-number shifts. The commit did not change the import block (lines 12-27), `TestAllClassesImportable`, or the `TODO(test-class-is-type-body)` comment — the target of the design is untouched by that commit.

## Summary

Design is **applicable as written** with the caveat that all line-number citations inside the design and exploration are stale. The logical structure, proposed deletion, and rationale are all still correct. Executor must use current line numbers (above) rather than those in the design documents.
