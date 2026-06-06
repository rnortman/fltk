# CST Type Annotation Regression: Archaeology

Concise. Precise. Token-dense — no fluff, full information. No preamble. No padding. Audience: smart LLM/human.

---

## Summary

Two distinct annotation regressions exist in the repo. They are unrelated in mechanism.

1. **`fltk/fegen/fltk2gsm.py`** — CST-typed parameter annotations intentionally removed in commit `214dbe1` (2026-05-28) as part of the PyO3 Phase 4 DI refactor. This is a deliberate, documented design decision.

2. **`fltk/unparse/unparsefmt_cst.py` (and `*_parser.py`, `*_trivia_parser.py`)** — Style-level annotation degradation (single quotes, `typing.Optional[X]` instead of `X | None`, extraneous parens, long lines) caused by `ast.unparse()` re-emission in commit `7914e57` (2026-01-13). Not intentional; a known open issue tracked in `docs/adr/2026/05/25-make-check-fixes/exploration.md`.

---

## Regression 1 — `fltk2gsm.py`: intentional annotation removal

### Commit

`214dbe1` ("Phase 4: Selectable Python/Rust CST backends", 2026-05-28-16:31)

### What changed

`fltk/fegen/fltk2gsm.py`: every `visit_*` method lost its CST-typed parameter annotation. Diff:

```diff
-    def visit_grammar(self, grammar: cst.Grammar) -> gsm.Grammar:
+    def visit_grammar(self, grammar) -> gsm.Grammar:

-    def visit_rule(self, rule: cst.Rule) -> gsm.Rule:
+    def visit_rule(self, rule) -> gsm.Rule:

-    def visit_identifier(self, identifier: cst.Identifier) -> gsm.Identifier:
+    def visit_identifier(self, identifier) -> gsm.Identifier:

-    def visit_alternatives(self, alternatives: cst.Alternatives) -> list[gsm.Items]:
+    def visit_alternatives(self, alternatives) -> list[gsm.Items]:

-    def visit_items(self, items: cst.Items) -> gsm.Items:
+    def visit_items(self, items) -> gsm.Items:

-    def visit_item(self, item: cst.Item) -> gsm.Item:
+    def visit_item(self, item) -> gsm.Item:

-    def visit_term(self, term: cst.Term) -> gsm.Term:
+    def visit_term(self, term) -> gsm.Term:

-    def visit_disposition(self, disposition: cst.Disposition) -> gsm.Disposition:
+    def visit_disposition(self, disposition) -> gsm.Disposition:

-    def visit_quantifier(self, quantifier: cst.Quantifier) -> gsm.Quantifier:
+    def visit_quantifier(self, quantifier) -> gsm.Quantifier:

-    def visit_literal(self, literal: cst.Literal) -> gsm.Literal:
+    def visit_literal(self, literal) -> gsm.Literal:

-    def visit_regex(self, regex: cst.RawString) -> gsm.Regex:
+    def visit_regex(self, regex) -> gsm.Regex:
```

All affected lines: `fltk/fegen/fltk2gsm.py:14-132` (per implementation log).

### Why

`Cst2Gsm.__init__` gained a `cst: ModuleType = _default_cst` dependency-injection parameter. The class now dispatches through `self.cst` for all CST class references (`self.cst.Items.Label.*`, `self.cst.Item`, etc.) so that it can accept either the Python dataclass CST (`fltk_cst`) or a Rust-backed CST extension module. Because `cst` is a `ModuleType` parameter resolved at runtime, its classes are not statically typed — there is no type stub or protocol for the CST module. Consequently the parameter types `cst.Grammar`, `cst.Rule`, etc. were not reachable as annotations and were dropped.

The import `from fltk.fegen import fltk_cst as cst` was replaced with `from fltk.fegen import fltk_cst as _default_cst`. The annotation `cst.Foo` was thus no longer a valid name.

### ADR context

`docs/adr/2026/05/28-pyo3-phase4-runtime-integration/implementation-log.md:62`:
> `fltk2gsm.py:14-132`: all method signatures updated (type annotations removed for bare CST types); all `cst.Items.Label.*`, `cst.Disposition.Label.*`, `cst.Quantifier.Label.*`, and `isinstance(item, cst.Item)` references changed to `self.cst.*`.

The design decision is in `docs/adr/2026/05/28-pyo3-phase4-runtime-integration/design.md` (Increment 1: `Cst2Gsm` DI refactor). The `cst: ModuleType` injection was the accepted approach for dual Python/Rust CST support.

---

## Regression 2 — generated files: `ast.unparse()` re-emission with style degradation

### Commit

`7914e57` ("Add preserve_blanks directive and fix formatter comment handling", 2026-01-13)

### What changed

`fltk/unparse/unparsefmt_cst.py`, `unparsefmt_parser.py`, `unparsefmt_trivia_parser.py` were regenerated. The `Statement` class gained `PreserveBlanks` as a new union member (grammar change in `unparsefmt.fltkg`). Regeneration used `ast.unparse()` (via `genparser.py:108,183`), which emits compact single-line Python with:

- Single quotes instead of double quotes (from `repr()` in `fltk/iir/py/compiler.py:323`)
- `typing.Optional[X]` instead of `X | None` (hardcoded in `gsm2tree.py:128,140,148,154,226` and registered in `iir/context.py:87`)
- `extend(((label, child) for ...))` double-parens (gsm2tree.py:185)
- No trailing newline (`ast.unparse()` doesn't add one)
- Import groups not blank-line separated (`pygen.module()` emits bare `import X` with no grouping)

The previously clean state (double quotes, `Label | None`) in `unparsefmt_cst.py` was produced in commit `29b4dc1` (2025-07-22, "Add unparser/formatter support") which created the file fresh. The commit `d1d3452` (2026-05-25, "Reformat generated code") then ran `ruff format` to restore readable multi-line formatting while preserving the style bugs, and commit `9c5a865` set up `make check` which formally exposed the violations.

Key diff fragment from `7914e57`:

```diff
-    children: list[tuple[Label | None, typing.Union["Statement", "Trivia"]]] = ...
+    children: list[tuple[typing.Optional[Label], typing.Union['Statement', 'Trivia']]] = ...

-    def append(self, child: ..., label: Label | None = None) -> None:
+    def append(self, child: ..., label: typing.Optional[Label]=None) -> None:

-    def extend(...) -> None:
-        self.children.extend((label, child) for child in children)
+    def extend(...) -> None:
+        self.children.extend(((label, child) for child in children))
```

(`fltk/unparse/unparsefmt_cst.py` lines 47-48, 124-158 in the `7914e57` diff)

### Why

This was NOT intentional. `ast.unparse()` is the only serialization path (`genparser.py:108`, `genparser.py:183`). It was not designed to produce lint-compliant output; no post-processing step (ruff format, ruff check --fix) was ever added to the generator. The grammar changes in `7914e57` required regeneration; regeneration overwrote the manually-cleaned file.

### ADR context

`docs/adr/2026/05/25-make-check-fixes/exploration.md` (written 2026-05-25, after `7914e57` but before the recent branch work) documents all root causes:

- Root cause A (Q000): `compiler.py:323` uses `repr()` → single quotes
- Root cause B (UP045): `gsm2tree.py:128,140,148,154,226` hardcodes `typing.Optional[...]`; `iir/context.py:87` registers `iir.Maybe` as `typing.Optional`
- Root cause C (UP034): `gsm2tree.py:185` double-parens in `extend()`
- Root cause D (E501): `ast.unparse()` produces no line wrapping
- Root cause E (I001): `pygen.module()` / `genparser.py:83-88` emit no blank line between stdlib and first-party imports
- Root cause F (W292): `ast.unparse()` emits no trailing newline

The exploration note at `docs/adr/2026/05/25-make-check-fixes/exploration.md:130-134` explicitly identifies the regression:
> `fltk/unparse/unparsefmt_cst.py` was originally created in commit `29b4dc1` (2025-07-22) in a clean state (double quotes, `Label | None`). It was then **regenerated** in commit `7914e57` (2026-01-13, "Add preserve_blanks directive...") — that regeneration overwrote the clean version with raw `ast.unparse()` output, losing all manual formatting improvements.

---

## Code surface — generator files

| File | Role | Key line(s) |
|------|------|-------------|
| `fltk/fegen/gsm2tree.py:128,140,148,154,226` | Emits CST class method signatures; hardcodes `typing.Optional[...]` | annotation strings |
| `fltk/fegen/gsm2tree.py:85-93` | `py_annotation_for_model_types()` — builds `typing.Union[...]` annotation strings using double-quoted forward refs | annotation generator |
| `fltk/fegen/genparser.py:108,183` | Calls `ast.unparse(cst_mod)` / `ast.unparse(parser_mod)` — sole serialization path | emission |
| `fltk/iir/py/compiler.py:323` | `repr(expr.value)` → single-quoted string literals in generated code | Q000 root cause |
| `fltk/iir/context.py:87` | Registers `iir.Maybe` → `typing.Optional` | UP045 root cause |
| `fltk/fegen/fltk2gsm.py:10-12` | `Cst2Gsm.__init__(self, terminals, cst: ModuleType = _default_cst)` — DI param | intentional annotation removal |

---

## Current state of annotations

- **`fltk/fegen/fltk2gsm.py`**: all `visit_*` methods have no CST-type annotations on their primary parameter. Return types are present (e.g., `-> gsm.Grammar`). This is the post-`214dbe1` state and matches current HEAD (`f1e2a98`).

- **`fltk/unparse/unparsefmt_cst.py`**: post-`d1d3452` ruff-format pass, annotations are semantically present but style-wrong (`typing.Optional[Label]` not `Label | None`, single quotes). The reformatting in `d1d3452` restored multi-line readability but did not fix style violations. Current HEAD passes pyright (types are valid) but fails `ruff check` on UP045, Q000, etc.

- **`fltk/fegen/fltk_cst.py`** (the fegen grammar's own CST): was manually cleaned in commit `21fc688` (2025-07-03, "Fix linter errors in gencode") — `typing.Optional[Label]` → `Label | None`, double quotes, import grouping. It has not been regenerated since and currently passes lint. It serves as the reference for what the generator *should* emit.

---

## Open factual questions

- Whether `gsm2tree.py` and related generators are intended to be fixed to emit lint-compliant code (the `25-make-check-fixes` exploration documents the root causes but makes no decision on fixing the generator vs post-processing the output).
- Whether `Cst2Gsm` is intended to eventually gain a typed `Protocol` for the CST module (which would allow restoring parameter annotations on `visit_*`); no ADR or TODO entry was found for this.
