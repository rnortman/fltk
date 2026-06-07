# Judge verdict — deep review, Rust CST native span (round 2)

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Phase: deep. Base f8fdb53..HEAD be44bd5. Round 2 — APPROVED or ESCALATE only.
Rework commit: be44bd5 (single disputed item from round 1: quality-4).
Round-1 verdict: REWORK on quality-4 only; all other 18 dispositions accepted (`judge-verdict-deep.md`).

## Disputed item re-walk

### quality-4 — now Fixed (was phantom TODO + wrong rubric outcome)

Round-1 fault: dispositioned `TODO(span-make-span-expr-registry)` — a phantom defer (no `TODO.md` entry, no code comment) for a fix the rubric scored as do-now (Q2 fails: mechanical, single-file, in-scope).

Rework verified:
- **Real generator change.** `git diff 99e276a..be44bd5 -- fltk/fegen/gsm2parser.py`: `_make_span_expr` now computes `span_class_name = self.context.python_type_registry.lookup(self.TerminalSpanType).import_name()` and passes it to `VarByName(name=span_class_name, ...)`, replacing the hardcoded `"fltk.fegen.pyrt.span.Span"` string. Path derived from the registry's `TypeInfo`, exactly the round-1 prescribed fix (a) — a future module rename only updates the registry entry.
- **Derivation is correct.** `TypeInfo.import_name()` (`fltk/iir/py/reg.py:26-29`) returns `".".join(module.import_path + [name])`; for the registered `TerminalSpanType` (module `fltk.fegen.pyrt.span`, name `Span`) this is exactly `"fltk.fegen.pyrt.span.Span"` — identical to the prior literal. So generated output is byte-identical: `fltk_parser.py:83/93/115/...` still emit `fltk.fegen.pyrt.span.Span.with_source(...)`. Regen is a no-op on generated files (rework commit touched only `gsm2parser.py` + `dispositions-deep.md`; zero `.rs`/generated-`.py` changes — confirmed via `git diff 99e276a..be44bd5 --stat`).
- **No phantom TODO remains.** Disposition is now plain "Fixed" (`dispositions-deep.md:149-156`). `grep span-make-span-expr-registry` across `*.py`/`*.md`/`Makefile`: zero hits outside the historical note at `dispositions-deep.md:162` explaining the prior error. No `TODO.md` entry, no `TODO(...)` comment — correct, since the work was done, not deferred.
- **`make check` exits 0.** 939 Python tests pass; `cargo check` clean; `cargo clippy -- -D warnings` clean; `cargo test` ok. No working-tree regen drift (only untracked review artifacts dirty).

Assessment: disposition now accurate and the fix is genuine — registry-derived path, no behavioral change to generated code, no phantom defer. Accept.

## Approved

All 19 dispositions acceptable. 18 carried from round 1 (`judge-verdict-deep.md`: 11 Fixed verified, 3 Won't-Do sound, 2 TODOs — gencode-poc-fltkg, span-source-as-py-crosscdylib — acceptable); quality-4 now verified Fixed this round. Not re-walked beyond the per-item evidence above.

---

## Verdict: APPROVED

Round-1's sole REWORK item (quality-4) is genuinely fixed: `_make_span_expr` derives the Span module path from the type registry (`import_name()`), generated output is unchanged, the phantom `TODO(span-make-span-expr-registry)` is gone, and `make check` passes (939 py + cargo check/clippy/test). HEAD be44bd5.
