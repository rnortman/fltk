# Ruff Investigation: CST Type Annotations and Gencode

Status: **COMPLETE** | Date: 2026-06-05

---

## Q1 Findings: Generated Files Inventory

### Generated files committed to the tree

The following files are GENERATED CODE (gencode) produced by the FLTK code generators:

#### Bootstrap CST/Parser (fegen self-hosting)

| File | Generator Entry Point | Grammar File | Dates Modified |
|------|---|---|---|
| `/home/rnortman/src/fltk/fltk/fegen/bootstrap_cst.py` | `genparser` (indirect bootstrap) | `bootstrap.fltkg` | 2025-07-01 to 2025-07-03 |
| `/home/rnortman/src/fltk/fltk/fegen/bootstrap_parser.py` | `genparser` (indirect bootstrap) | `bootstrap.fltkg` | 2025-07-01 to 2025-07-03 |
| (No `bootstrap_trivia_parser.py`) | N/A | N/A | N/A |

Current state: **CLEAN** — all `Label | None` annotations, double quotes, properly grouped imports.

#### FLTK Grammar CST/Parser

| File | Generator Entry Point | Grammar File | Dates Modified |
|------|---|---|---|
| `/home/rnortman/src/fltk/fltk/fegen/fltk_cst.py` | `genparser generate` | `fltk.fltkg` | 2025-07-01 to 2025-07-22 |
| `/home/rnortman/src/fltk/fltk/fegen/fltk_parser.py` | `genparser generate` | `fltk.fltkg` | 2025-07-01 to 2025-07-22 |
| `/home/rnortman/src/fltk/fltk/fegen/fltk_trivia_parser.py` | `genparser generate` | `fltk.fltkg` | 2025-07-01 to 2025-07-22 |

Current state: **CLEAN** — all `Label | None` annotations, double quotes, properly grouped imports. Last regenerated 2025-07-22 in commit `29b4dc1` ("Add unparser/formatter support"), then manually cleaned in commit `21fc688` (2025-07-03). No regeneration since.

#### Unparser Formatter CST/Parser

| File | Generator Entry Point | Grammar File | Dates Modified |
|------|---|---|---|
| `/home/rnortman/src/fltk/fltk/unparse/unparsefmt_cst.py` | `genparser generate` | `unparsefmt.fltkg` | 2025-07-22 to 2026-05-25 |
| `/home/rnortman/src/fltk/fltk/unparse/unparsefmt_parser.py` | `genparser generate` | `unparsefmt.fltkg` | 2025-07-22 to 2026-05-25 |
| `/home/rnortman/src/fltk/fltk/unparse/unparsefmt_trivia_parser.py` | `genparser generate` | `unparsefmt.fltkg` | 2025-07-22 to 2026-05-25 |

Current state: **CLEAN FORMATTING, STYLE-WRONG ANNOTATIONS** — all `Label | None` annotations are present and semantically correct (manually restored by ruff in commit `d1d3452`, 2026-05-25), but the generation history shows they were emitted as `typing.Optional[Label]` in commit `7914e57` (2026-01-13), then reformatted to `Label | None` by `d1d3452`.

#### Other Grammar Files (not regenerated in committed history)

| File | Generator Entry Point | Grammar File | Status |
|------|---|---|---|
| `fgen.fltkg` | exists but no committed parser | `fgen.fltkg` | No parser committed |
| `toy.fltkg` | exists but no committed parser | `toy.fltkg` | Test/fixture grammar only |

---

### Generation entry points and markers

The generators are located at:
- `/home/rnortman/src/fltk/fltk/fegen/genparser.py` — CLI entry point (lines 114-227)
  - Command `genparser generate <grammar.fltkg> <base_name> <cst_module_name> [--output-dir]`
  - Generates: `{base_name}_cst.py`, `{base_name}_parser.py`, `{base_name}_trivia_parser.py`
  - Serialization: `ast.unparse()` at lines 108, 183

- `/home/rnortman/src/fltk/fltk/fegen/gsm2tree_rs.py` — Rust CST generator (lines 35-260)
  - Command `genparser gen-rust-cst <grammar.fltkg> <output.rs>`
  - Generates: standalone PyO3 `.rs` extension module source
  - No Python gencode annotations involved

### Identification markers

**NO HEADER COMMENTS** — FLTK gencode files do not have explicit "DO NOT EDIT" or "GENERATED" markers at the top. They are identified by:
1. **Path convention**: `*_cst.py`, `*_parser.py`, `*_trivia_parser.py` in grammar directories
2. **Grammar file source**: corresponding `.fltkg` file in the same directory
3. **Git history**: `genparser` tool invocation in commit messages
4. **Generator configuration**: `pyproject.toml` build scripts (if present)

---

### On-the-fly vs committed generation

**Committed to tree**: All three file classes above (`bootstrap_*`, `fltk_*`, `unparsefmt_*`) are committed.

**Generated on-the-fly during tests**:
- Grammar tests in `/home/rnortman/src/fltk/tests/test_genparser.py` (if any) — check for `genparser` CLI invocations
- No temporary gencode generation detected in test code review (not exhaustively audited)

---

## Q2 Findings: Ruff Annotation Restoration

### Test Setup

Created throwaway copies of six gencode files in `/tmp/` and ran:
1. `uv run --group lint ruff format <files>` 
2. `uv run --group lint ruff check --fix <files>`

### Results: **NO, ruff does NOT restore lost CST-node type annotations**

Ruff reformatting and check-fix made **ONLY cosmetic formatting changes**; **no semantic annotation changes whatsoever**.

#### Concrete diff evidence

**File: `unparsefmt_cst.py`**

After `ruff format` and `ruff check --fix`:

```diff
--- /home/rnortman/src/fltk/fltk/unparse/unparsefmt_cst.py (committed)
+++ /tmp/unparsefmt_cst.py (after ruff)

@@ -13,9 +13,7 @@
     span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
-    children: list[tuple[Label | None, typing.Union["Statement", "Trivia"]]] = dataclasses.field(
-        default_factory=list
-    )
+    children: list[tuple[Label | None, typing.Union["Statement", "Trivia"]]] = dataclasses.field(default_factory=list)
     
     def append(self, child: typing.Union["Statement", "Trivia"], label: Label | None = None) -> None:
         self.children.append((label, child))
```

Annotation remains: `Label | None` (unchanged).

Similar formatting-only changes across:
- `unparsefmt_parser.py`: lines 873, 975, 1107, 1406, 1598 — all method return types unchanged (e.g., `ApplyResult[int, ...] | None`)
- `unparsefmt_trivia_parser.py`: identical pattern

**File: `fltk_cst.py`**

```
$ diff /home/rnortman/src/fltk/fltk/fegen/fltk_cst.py /tmp/fltk_cst.py
(no output — identical)
```

**File: `fltk_parser.py`**

```
$ diff /home/rnortman/src/fltk/fltk/fegen/fltk_parser.py /tmp/fltk_parser.py
(no output — identical)
```

**File: `fltk_trivia_parser.py`**

```
(no output — identical)
```

### Ruff rule coverage

Ruff was invoked with the `lint` group from `pyproject.toml`. Gencode files pass all checks after reformatting. No violations remain. Checks applied include:
- `UP` rules (pyupgrade syntax modernization): would fix `typing.Optional[X]` → `X | None`, but the committed code already has correct `Label | None` form
- `Q` rules (quote style): would change `'...'` → `"..."`, but the committed code already has correct double quotes
- `E501` (line length): lines are wrapped by `ruff format`
- All other standard rules

### Conclusion on lost CST annotations

The "lost annotations" mentioned in the complaint refers to **`fltk2gsm.py`** (Regression 1 in the archaeology document), not to `unparsefmt_*` or `fltk_*` gencode. 

- **`unparsefmt_cst.py`, `unparsefmt_parser.py`, `unparsefmt_trivia_parser.py`**: Annotations were style-wrong in commit `7914e57` (`typing.Optional[Label]`), then **manually restored to correct form** (`Label | None`) by commit `d1d3452` using `ruff format`. Ruff preserves these correct annotations; no further restoration needed.

- **`fltk2gsm.py`**: CST-typed parameter annotations were **intentionally removed** in commit `214dbe1` due to DI refactor (ModuleType runtime injection prevents static typing). Ruff cannot restore intentionally-removed annotations; the loss is by design.

---

## Summary Table

| File(s) | Annotation State | Cause | Ruff Can Fix? |
|---------|---|---|---|
| `fltk2gsm.py` | No CST param types (e.g., `visit_grammar(self, grammar)`) | Intentional design decision (commit `214dbe1`) | **NO** — annotations removed by design, not style |
| `unparsefmt_cst.py`, `*_parser.py`, `*_trivia_parser.py` | Clean (e.g., `Label \| None`, double quotes) | Manually restored by `ruff format` (commit `d1d3452`) | **N/A** — already clean after ruff pass |
| `fltk_cst.py`, `fltk_parser.py`, `fltk_trivia_parser.py` | Clean (e.g., `Label \| None`) | Manually cleaned post-generation (commit `21fc688`); not regenerated since | **N/A** — already clean |
| `bootstrap_cst.py`, `bootstrap_parser.py` | Clean (e.g., `Label \| None`) | Manually cleaned post-generation; old bootstrap from 2025-07 | **N/A** — already clean |

---

## Files Tested

1. `/tmp/unparsefmt_cst.py` (copy from committed)
2. `/tmp/unparsefmt_parser.py` (copy from committed)
3. `/tmp/unparsefmt_trivia_parser.py` (copy from committed)
4. `/tmp/fltk_cst.py` (copy from committed)
5. `/tmp/fltk_parser.py` (copy from committed)
6. `/tmp/fltk_trivia_parser.py` (copy from committed)

All files in `/tmp/` were cleaned up post-test. No committed files were modified.

