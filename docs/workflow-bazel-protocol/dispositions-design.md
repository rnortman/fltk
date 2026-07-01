# Dispositions: design review round 1

Design: [`design.md`](./design.md). Reviewer notes:
[`notes-design-design-reviewer.md`](./notes-design-design-reviewer.md).

All three findings fact-checked against `rust.bzl` and hold. design-1 and design-2
are resolved together by a single structural mechanism (the internal rule now
exposes an `OutputGroupInfo`), because a Bazel macro cannot address an individual
`declare_file` output by label — so the reviewer's literal suggestion for design-1
("add `<name>/cst.pyi` to `data`") was itself not implementable as worded, and the
correct fix routes outputs through named groups.

## design-1 — "Stub exposure" paragraph reads unconditional; must be gated on `protocol_module`

- **Disposition:** Fixed
- **Action:** §2 "Output routing" (new block) + rewritten "Stub exposure" bullet.
  The internal rule now returns `OutputGroupInfo(rust_srcs=..., stub_srcs=...)`.
  `stub_srcs` contains the `.pyi` package files only when `protocol_module` is
  non-empty and `cst_protocol.py` only when `protocol = True`; it is an empty
  depset otherwise. The macro adds `stub_srcs` (the group, not enumerated file
  labels) to `py_library.data`, so the `python_extension = True`,
  `protocol_module = ""` case adds nothing and references no undeclared file —
  self-gating rather than prose-conditional. Also fixes the deeper issue that the
  reviewer's suggested wording (cherry-picking `<name>/cst.pyi` by label) is not
  expressible in a Bazel macro; output groups are the implementable form.
- **Severity assessment:** As worded, an implementer following the paragraph
  literally would add non-existent file labels to `py_library.data` and break the
  design's own explicitly-valid `protocol_module = ""` case with a Bazel "no such
  target" analysis error. Correctness-blocking for a listed happy path.

## design-2 — Crate-assembly genrule newly receives `.pyi`/`.py` files; unmentioned in test plan

- **Disposition:** Fixed
- **Action:** §2 macro bullet now states crate assembly consumes **only the
  `rust_srcs` output group** of the internal target, so `.pyi`/`.py` never enter
  the flat crate root. New Edge-cases bullet ("Stub/protocol files must not reach
  crate assembly") records that feeding the whole target would copy undeclared
  files into the crate root, that Bazel discards them (likely harmless), and that
  the design deliberately does not rely on that. Test plan's Python-extension
  bullet now asserts the assembled crate root contains exactly
  `lib.rs`/`cst.rs`/`parser.rs`.
- **Severity assessment:** Almost certainly harmless in practice (Bazel discards
  undeclared genrule outputs), but a genuinely first-exercised interaction on the
  new `bootstrap_native` target; under a stricter execution strategy it could fail
  the smoke build. The `rust_srcs`-group fix removes the interaction entirely.

## design-3 — Stale `fltk_pyo3_cdylib` references in `rust.bzl` module/rule docstrings

- **Disposition:** Fixed
- **Action:** §3 now instructs updating the module docstring load example
  (`rust.bzl:13`) and the two `fltk_pyo3_cdylib` doc-string references
  (`rust.bzl:89`, `rust.bzl:251`) alongside removing the symbol from the public
  surface. Line references verified against source.
- **Severity assessment:** Doc hygiene only, no behavior change. Left unfixed, the
  file's own documented load example would advertise a removed symbol, misleading
  out-of-tree consumers reading the source.
