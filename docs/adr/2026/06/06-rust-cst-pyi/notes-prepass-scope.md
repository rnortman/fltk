# Scope prepass findings — rust-cst-pyi

Commit reviewed: c78a014 (base 46a6639)

---

## scope-1 — `fegen_cst.pyi` missing `# ruff: noqa: N802` header

**File:line:** `fltk/_native/fegen_cst.pyi:1`

**Expected:** Design §2.1 "Formatting" specifies `# ruff: noqa: N802` header "if module-level PascalCase names trip lint, mirroring the protocol generator". The generator (`generate_pyi`) unconditionally emits it as the first line (`gsm2tree_rs.py:120`). The PoC grammar `.pyi` produced in tests likewise gets it.

**Actual:** The committed `fltk/_native/fegen_cst.pyi` does not contain `# ruff: noqa: N802`. The file starts `from __future__ import annotations`. The header was present in the generated string but stripped during the `make fix` (ruff format) step before commit — ruff removes `# noqa` directives it considers redundant when there are no violations on that line, which it does when module-level names happen not to trigger N802 in context.

**Consequence:** Benign at the moment — ruff does not currently flag the committed stub — so `make check` passes. But the generator always emits the header comment and the committed file does not have it, meaning the committed stub is not byte-for-byte what the generator produces after `make fix`. Any future regen-and-diff discipline that checks "committed file equals regen output" will see a spurious diff on this line if the ruff version or config ever causes N802 to fire. Low operational impact; worth noting for disciplined regen checking.

**Suggested fix:** Either accept the `make fix` stripping and remove the `# ruff: noqa: N802` emission from `generate_pyi` (since the comment is unconditional and ruff strips it when not needed), or add `N802` to the `per-file-ignores` for `fltk/_native/fegen_cst.pyi` in `pyproject.toml` so ruff preserves the directive. The former is simpler.

---

## scope-2 — Deviation in `generate_pyi`: `Label = _proto.Class.Label` and no module-level `<Class>: type[<Class>]` attrs (logged, justified)

**File:line:** `fltk/fegen/gsm2tree_rs.py:146-154` and the absence of module-level attrs.

**Expected:** Design §2.1 specified `Label: typing.ClassVar[type[_proto.<Class>.Label]]` and module-level `<Class>: type[<Class>]` per rule.

**Actual:** Shipped `Label = _proto.<Class>.Label` (type alias assignment) and no module-level attrs. Both deviations are recorded in the implementation log (Increment 3) with explicit rationale: `ClassVar` caused pyright `reportRedeclaration` in self-check and `"Label" is not defined as a ClassVar in protocol` in conformance; module-level attrs caused the same `reportRedeclaration`. The corrected forms pass both self-check and conformance (verified by the new tests).

**Consequence:** None negative. The corrected forms achieve the design's intent (zero-error self-check and conformance) where the design-specified forms provably do not. Logged deviation is accurate and well-justified.

**Suggested fix:** None. Accept as-is; the implementation log is the record.

---

## scope-3 — Deviation in §2.3: Python CST `span` annotation widening (logged, justified)

**File:line:** `fltk/fegen/gsm2tree.py:235-238`; regenerated `fltk_cst.py`, `bootstrap_cst.py`, `toy_cst.py`, `unparsefmt_cst.py`.

**Expected:** Design §2.3 blast-radius enumeration did not include the Python CST `span` field annotation; §2.4 listed only protocol files as regeneration targets for the Python backend.

**Actual:** Adding `fltk/_native/__init__.pyi` made `fltk._native.Span` a concrete type; parsers that assign `fltk._native.Span` objects to `span: terminalsrc.Span` dataclass fields produced 676 pyright errors. The fix widens the generated Python CST `span` annotation to `terminalsrc.Span | fltk._native.Span`, matching the protocol union. Four Python CST concrete files were regenerated. Deviation logged in Increment 4 with explicit rationale.

**Consequence:** The annotation widening is a public-API surface change for downstream Python-backend consumers: `node.span` now annotated as `terminalsrc.Span | fltk._native.Span` instead of `terminalsrc.Span`. Code that narrowed the type via assignment annotation (`s: terminalsrc.Span = node.span`) gains a pyright error; code that merely used the value is unaffected. The change is conservative (union widening, not narrowing), matches the protocol, and is correct (parsers have always assigned either Span type). The implementation log records this. Given CLAUDE.md's out-of-tree consumer warning, callers with narrow local annotations may need updating — but the change is necessary and correct.

**Suggested fix:** None for the change itself. The implementation log entry is sufficient. A downstream migration note in the ADR would be good hygiene but is not a scope gap.

---

No findings. (The three items above are: one minor regen-discipline discrepancy with negligible operational impact; two logged deviations that are technically superior to the design-specified forms. No design-scope piece is silently omitted, no unjustified punt exists, and bonus work is limited to what was required to make `make check` pass.)
