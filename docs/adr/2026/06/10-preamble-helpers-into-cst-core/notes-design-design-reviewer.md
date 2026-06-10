# Design review: preamble-helpers-into-cst-core

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Verified against source: `_preamble()` body (`fltk/fegen/gsm2tree_rs.py:244-326`), all three generated preambles (lines 1-77, items 8-75, byte-identical to the emitted string), body identifier counts (GILOnceCell 0/0/0; PyTypeError/PyValueError 56/78 in cst_fegen; PyList/PyTuple/PyType 92/28/28; `py.import("fltk._native")` 0 in all bodies; `type_object` 14; all three helpers called in all three bodies), `crates/fltk-cst-core/Cargo.toml` (rlib, pyo3 0.23), `lib.rs` (re-exports `Span` at crate root, so `use crate::Span;` resolves), `span.rs:12` precedent and `span.rs:148` TODO wording, fixture `Cargo.toml`s (both depend on `fltk-cst-core` with `default-features = false`), root `Cargo.toml:20`, Makefile `gencode`/`fix` targets, and every test named in §4 (`tests/test_gsm2tree_rs.py:171-330, 425-480`) — names, classes, and current assertions all match the design's descriptions, including the `<= 2` import-count check at line 325. §3's name-capture claim verified: module-scope items in generated files are PascalCase types plus `register_classes` only. Old-code-compat reasoning (§3 bullet 1) verified: inline helpers reference only `fltk_cst_core::Span` + pyo3, imports are non-glob. Requirements coverage is complete: every Direction item, constraint, and verification item in request.md maps to a design section. Two findings.

## design-1 — §2.2 / §3: "post-`make fix` (rustfmt-normalized) form" is ungrounded; no rustfmt exists in the flow

Quote (§2.2): "The emitted string must match the post-`make fix` (rustfmt-normalized) form so `make gencode` is diff-clean against committed files. Implementation step: emit, run `make fix`, copy the normalized `use` block back into `_preamble()` if rustfmt reordered anything." Repeated in §3: "rustfmt vs. generator drift on the `use` block … Handled in §2.2."

What's wrong: `make fix` (Makefile:29-31) runs `ruff check --fix` + `ruff format` — Python only. No `rustfmt`/`cargo fmt` invocation exists anywhere in the Makefile or `.github/` (grep: zero hits). The committed generated `.rs` files are byte-identical to raw `_preamble()` output today (request.md's MD5 `207fcd9f…` is of the *generator string*, including the non-rustfmt line layout of the `PyRuntimeError` closure at `src/cst_fegen.rs:70-72`). There is no "rustfmt-normalized form" to match; committed `.rs` = generator output, verbatim.

Consequence: an implementer following §2.2 literally will look for rustfmt changes that never happen (wasted loop), or — worse — infer rustfmt is supposed to run, execute `cargo fmt` manually on the regenerated files, and commit. Then the second `make gencode` overwrites with raw generator output and `git diff` is non-empty, failing the request's explicit verification "make gencode idempotent (`git diff` empty on second run)". The design's stated mechanism for satisfying that criterion is wrong.

Fix: replace the paragraph with the true invariant — no formatter touches generated `.rs`; committed `.rs` must equal `generate()` output byte-for-byte; the `use`-block ordering is whatever the generator emits (pick one, keep it stable); idempotency rests on generator determinism (already tested by `TestDeterministicOutput`) plus the §4 double-run check. `make fix` after `make gencode` is still needed, but only for the Python files gencode regenerates.

## design-2 — §4 gate item 4: `grep -rn 'preamble-helpers-into-cst-core'` returns nothing" is mechanically unsatisfiable

Quote (§4): "4. `grep -rn 'preamble-helpers-into-cst-core'` returns nothing." (Inherited verbatim from request.md Verification.)

What's wrong: the slug appears in committed historical ADR docs that this change cannot remove — `docs/adr/2026/06/06-fegen-cst-rs-single-source/dispositions-deep.md:2-3`, `judge-verdict-deep.md:10-11`, `docs/adr/2026/06/10-todo-burndown/triage.md` (4 hits), `docs/adr/2026/06/10-todo-burndown/README.md:28` — and in this task's own ADR dir (`request.md`, `design.md`, this file), whose directory name *is* the slug. CLAUDE.md: "Treat accepted ADRs as immutable." A repo-wide `grep -rn` can never return nothing.

Consequence: the verification gate fails on day one regardless of implementation correctness. An implementer either stalls on an unpassable check or "fixes" it by editing immutable ADR documents — both wrong. The design's job was to ground the request's verification against the repo; §5 claims "Open questions: None" while carrying an unexecutable gate.

Fix: scope the grep to the live join points the TODO system actually defines (CLAUDE.md TODO section): `grep -rn 'preamble-helpers-into-cst-core' --include='*.py' --include='*.rs' .` plus absence from `TODO.md` — i.e., code comments and the master list, excluding `docs/adr/`.
