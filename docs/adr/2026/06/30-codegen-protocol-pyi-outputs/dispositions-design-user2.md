# Dispositions: user design decision #3 (respond round 2)

Design: `design.md` (this directory). Inputs: `notes-design-user.md` item 3 (user decision,
authoritative — revises the design). Prior round: `dispositions-design-user.md` (items 1 & 2).

User decision #3 was fact-checked against source before applying, then folded into `design.md`. It
**supersedes** the prior §2.7/§6 decision (recorded in `dispositions-design-user.md` user-decision-1)
that the in-tree `__init__.pyi` markers stay hand-authored and that generation is Bazel-scoped via
`ctx.actions.write`. Substantial design edits were made, so `review-chain:cleanup-editor` was re-run.

---

user-decision-3 (notes-design-user.md item 3: dogfood the generated `__init__.pyi` — route marker
generation through the generator/CLI path with generator-derived content; have the Bazel rule reuse that
same path; `make gencode` regenerates the two in-tree markers):

- Disposition: Fixed
- Action: Revised `design.md` to make stub-package `__init__.pyi` marker generation a shared
  generator/CLI capability with generator-derived content, dogfooded in-tree. Specifically:
  - **Header Change-2 bullet** — "generated" → "generator-derived" stub-package `__init__.pyi`, produced
    through the same generator/CLI path as the other stubs (not a Bazel-local fixed body), dogfooded by
    the two in-tree markers (§2.2, §2.5–§2.7; item 3).
  - **§2.2 (new `#### Stub-package __init__.pyi marker` subsection)** — adds the shared CLI surface on
    `gen-rust-cst` and `gen-rust-unparser`: `--init-pyi-output PATH`, `--extension-name NAME`,
    `--submodules CSV`, with up-front validation (`--init-pyi-output` requires the other two; identifier
    checks). New grammar-independent helper `render_stub_package_init(extension_name, submodules) -> str`
    in `gsm2lib_rs.py` renders comment-only, ruff-stable marker text. The marker is independent of
    `--protocol-module`, so it attaches to whichever invocation already writes a `.pyi` for the package.
  - **§2.5 (Bazel `generate_rust_parser`)** — the same `gen-rust-cst` action that emits `cst.pyi` now
    also gets `--init-pyi-output {name}/__init__.pyi --extension-name {name} --submodules cst,parser` and
    declares `{name}/__init__.pyi` as a third output of that one action, replacing `ctx.actions.write`.
    Outputs table unchanged in shape (still `cst.pyi` + `__init__.pyi`).
  - **§2.6** — the "resolved" paragraph rewritten: marker produced via the shared `--init-pyi-output`
    generator/CLI path (not a Bazel-local fixed body); content generator-derived from the extension name
    + submodule list (`cst,parser`); carries no grammar-derived rule data.
  - **§2.7 (Makefile)** — retitled "dogfood the in-tree stub-package markers"; supersedes the prior
    "hand-authored / Bazel-only" decision. `make gencode` appends marker flags to the `fegen`
    `gen-rust-cst` call (`Makefile:284-285`, emits `fltk/_stubs/fegen_rust_cst/__init__.pyi` with
    `--submodules cst,parser,unparser`) and to the fixture `gen-rust-unparser` call (`Makefile:306-307`,
    emits `fltk/_stubs/rust_parser_fixture/__init__.pyi`). Records the regen → `make fix` → commit /
    drift-check coverage and leaves `fltk/_native/__init__.pyi` untouched (out of scope).
  - **§3** — added `gsm2lib_rs.py` (`render_stub_package_init`), the new `gen_rust_cst` /
    `gen_rust_unparser` options + validation, updated the `rust.bzl` and `Makefile` bullets, added
    `test_gsm2lib_rs.py`, and noted the `__init__.pyi` markers change in comment text only (no
    symbol/annotation surface — CLAUDE.md constraint satisfied).
  - **§4 (edge cases)** — added: `--init-pyi-output` without `--extension-name`/`--submodules` rejected
    up front; the unparser-path-not-CST-path routing (the `rust_parser_fixture` wrinkle, no new
    `cst.pyi`, one invocation per package to avoid overwrite); ruff/`make fix` byte-stability.
  - **§5 (test plan)** — added CLI marker tests (gen-rust-cst and gen-rust-unparser), the
    `render_stub_package_init` unit test, and a `make gencode` drift paragraph noting the existing
    `tests/test_rust_unparser_pyi.py::test_committed_stub_artifacts_exist` (`:134-146`) stays green
    (asserts marker presence, not content). Rewrote the Bazel paragraph: the marker now has
    generator-level behavior covered by the CLI/helper tests (no longer "static `ctx.actions.write`, no
    behavior to test").
  - **§6** — item 1 updated (marker via dogfooded generator/CLI path, not `ctx.actions.write`); new
    item 3 records the dogfooding resolution and the explicit supersession of the prior decision.
- Severity assessment: This is a deliberate design change, not a bug fix; leaving the prior
  `ctx.actions.write`/hand-authored-marker design in place would directly contradict the user's
  authoritative decision and ship un-dogfooded markers that drift from generator output over time.
- Grounding:
  - The two in-tree markers are comment-only stub-package markers (`fltk/_stubs/fegen_rust_cst/__init__.pyi`
    4 lines; `fltk/_stubs/rust_parser_fixture/__init__.pyi` 6 lines), so generator-rendered comment text
    is the correct mechanism and carries no API surface.
  - `gsm2lib_rs.py` is the correct home for the renderer: it already owns module-layout/submodule
    templating (`LibSpec`/`Submodule`), `_validate_rust_ident`, and has no grammar dependency — matching
    the marker's inputs (extension name + submodule list).
  - The `rust_parser_fixture` wrinkle is real and verified: `Makefile:296` runs `gen-rust-cst` for the
    fixture with no `--protocol-module`, so no `cst.pyi` exists (`ls fltk/_stubs/rust_parser_fixture/`
    shows only `__init__.pyi` + `unparser.pyi`). Routing its marker through the `gen-rust-unparser`
    invocation (`Makefile:306-307`, which already writes `unparser.pyi` via `--protocol-module
    tests.rust_parser_fixture_cst_protocol`) avoids introducing a new `cst.pyi`. Making the marker
    independent of `--protocol-module` is what enables this routing.
  - The `fegen` marker staleness is real: `fltk/_stubs/fegen_rust_cst/__init__.pyi` says "only submodules
    cst and parser", but `crates/fegen-rust/src/lib.rs` registers `cst`, `parser`, and `unparser`; the
    regenerated marker (`--submodules cst,parser,unparser`) fixes this.
  - `fltk/_native/__init__.pyi` is a 2977-byte substantive hand-written stub (`Span`/`SourceText`/
    `UnknownSpan`), not a marker, and no `gencode` step generates it — left untouched per the note.
  - `tests/test_rust_unparser_pyi.py:134-146` asserts the fixture marker file is present (not its
    content), so the comment-text change keeps it green; its docstring already says a missing marker means
    `make gencode` was not run — consistent with wiring the marker into `gencode`.
