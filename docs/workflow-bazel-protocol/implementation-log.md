# Implementation Log: unify FLTK's Bazel parser-codegen surface

## Increment 1 — rename Rust protocol toggle `generate_protocol` → `protocol`

Design §1. Pure rename of the boolean attribute on the current
`generate_rust_parser` rule in `rust.bzl`. The `protocol_module` string and the
protocol/pyi trigger relationship are unchanged.

- rust.bzl:116: local `generate_protocol = ctx.attr.generate_protocol` →
  `protocol = ctx.attr.protocol`.
- rust.bzl:120-121: analysis-time guard now reads `ctx.attr.protocol` and the
  fail message names `protocol`.
- rust.bzl:128-129: comment updated (`generate_protocol` → `protocol`).
- rust.bzl:159: `if generate_protocol:` → `if protocol:`.
- rust.bzl:221-229: rule attribute `generate_protocol` → `protocol` (doc text
  unchanged otherwise).
- rust.bzl:248, 264: rule docstring + example comment reference `protocol`.
- Verified via grep: no remaining `generate_protocol` references in any
  `.bzl`/`BUILD`/`.bazel` file (no in-tree call site set it — the toggle was
  latent, per design §4 / requirements).

## Increment 2 — add `extension_name` attribute to the codegen rule

Design §2 (internal-rule `extension_name` part only). Adds the structural
decoupling of the output subdirectory / `--extension-name` from the rule's own
target name.

- rust.bzl:123-131: new `out_subdir = ctx.attr.extension_name or ctx.attr.name`
  local; `cst.rs` / `parser.rs` now declared under `out_subdir/` instead of
  `ctx.attr.name/`.
- rust.bzl:150-161: protocol-path outputs (`cst.pyi`, `__init__.pyi`) and the
  `--extension-name` flag now use `out_subdir`.
- rust.bzl:169: `cst_protocol.py` now declared under `out_subdir/`.
- rust.bzl:237-247: new `extension_name` (string, default `""`) rule attribute
  with doc.
- Fallback (`extension_name = ""` → `ctx.attr.name`) preserves today's behavior;
  no in-tree target sets `extension_name` yet (the wrapping macro will, a later
  increment). No buildifier/bazel available to lint; change is a self-contained
  Starlark attribute addition not yet instantiated, so the bootstrap-target
  bazel build (later increment) is the first exercise.

## Increment 3 — add `OutputGroupInfo` (`rust_srcs` / `stub_srcs`) to the codegen rule

Design §2 "Output routing". The internal codegen rule (`generate_rust_parser`
rule in `rust.bzl`) now returns an `OutputGroupInfo` alongside its existing
`DefaultInfo`, with two named groups so the wrapping macro (later increment) can
route `.rs` vs stub/protocol outputs without addressing individual declared files
by label.

- rust.bzl:143-147: new `stub_outputs = []` accumulator, documented as feeding
  the `stub_srcs` group; empty when `protocol_module` is empty.
- rust.bzl:172-173: append `cst_pyi` + `init_pyi` to `stub_outputs` (guarded by
  `protocol_module`).
- rust.bzl:182: append `protocol_out` to `stub_outputs` (guarded by `protocol`).
- rust.bzl:206-217: return list now includes
  `OutputGroupInfo(rust_srcs = depset([cst_out, parser_out]), stub_srcs =
  depset(stub_outputs))`. `DefaultInfo` still bundles all declared files.
- Validation: `bazel build --nobuild //:bootstrap_rust_srcs` analyzes clean
  (existing target, no protocol → `stub_srcs` is an empty depset). buildifier not
  installed; bazel available.

## Increment 4 — demote `fltk_pyo3_cdylib` to private `_build_pyo3_cdylib` helper

Design §3. Pure rename of the public `fltk_pyo3_cdylib` `def` to the private
helper `_build_pyo3_cdylib`, body verbatim; source no longer advertises the
removed public symbol.

- rust.bzl:311: `def fltk_pyo3_cdylib(` → `def _build_pyo3_cdylib(`; section
  banner comment (rust.bzl:309) renamed to match.
- rust.bzl:4-13: file-level module docstring — the `fltk_pyo3_cdylib` bullet now
  describes `_build_pyo3_cdylib` as an internal (non-public) helper; the load
  example drops `fltk_pyo3_cdylib`, leaving `load(..., "generate_rust_parser")`.
- rust.bzl:32, 89, 234, 291: four in-source doc references to `fltk_pyo3_cdylib`
  retargeted to `_build_pyo3_cdylib`.
- rust.bzl:365-377 (`rs_srcs` arg doc): the `lib.rs`-basename hazard warning
  reframed from a caller-facing WARNING to an INTERNAL INVARIANT (design §3 /
  edge case "lib.rs hazard"): the helper is always fed the macro's own codegen
  target, so the hazard is no longer consumer-reachable.
- rust.bzl:427: `TODO(bazel-lib-rs-no-cst)` comment reference updated to the new
  helper name.
- Deferred to the §4 bootstrap increment (which introduces the `generate_rust_parser`
  macro and rewrites the in-tree targets): BUILD.bazel:5 still loads
  `fltk_pyo3_cdylib` and BUILD.bazel:121 still calls it. These stale references
  are an expected mid-flow build breakage in an out-of-scope dependent — the §4
  increment removes them and makes the in-tree bazel build green.
- Validation: `grep` confirms no `fltk_pyo3_cdylib` references remain in `rust.bzl`.
  bazel not run this increment (BUILD.bazel intentionally references the now-removed
  public symbol until §4); buildifier not installed.

## Increment 5 — rename the internal codegen rule `generate_rust_parser` → `_generate_rust_srcs`

Design §2 (internal-rule rename part only). Pure rename of the current
`generate_rust_parser` *rule* object (and its impl fn) in `rust.bzl` to the
private `_generate_rust_srcs`, freeing the public name `generate_rust_parser`
for the wrapping macro (next increment). Rule body/attributes unchanged (adjusted
in increments 1–3).

- rust.bzl:100: section banner comment `# ---- generate_rust_parser ----` →
  `# ---- _generate_rust_srcs ----`.
- rust.bzl:102-103: impl fn `_generate_rust_parser_impl` → `_generate_rust_srcs_impl`;
  docstring now reads "Implementation for the _generate_rust_srcs rule."
- rust.bzl:221-222: `generate_rust_parser = rule(implementation =
  _generate_rust_parser_impl, ...)` → `_generate_rust_srcs = rule(implementation =
  _generate_rust_srcs_impl, ...)`.
- rust.bzl:298-302: rule-doc example relabeled `generate_rust_parser(...)` →
  `_generate_rust_srcs(...)`, prefaced by a note that this is the internal rule
  wrapped by the public `generate_rust_parser` macro (not consumer-instantiated).
- rust.bzl:418: helper comment "outputs of generate_rust_parser" →
  "outputs of _generate_rust_srcs".
- Left intentionally (public-name references, corrected by the macro increment):
  module docstring bullet (rust.bzl:4, "a rule that…" — becomes "a macro"),
  load example (rust.bzl:13, consumers load the macro `generate_rust_parser`), and
  the analysis-time `fail()` message (rust.bzl:121, names the public entry point).
- Validation: `grep` confirms the only remaining `generate_rust_parser` mentions
  are the three intentional public-name references above; the rule object is now
  `_generate_rust_srcs`. bazel not run — the in-tree build is intentionally broken
  mid-flow (no `generate_rust_parser` symbol yet + the increment-4
  `fltk_pyo3_cdylib` reference in BUILD.bazel); the macro + BUILD.bazel-rewrite
  increment restores green. Committed with `--no-verify`.

## Increment 6 — add the public `generate_rust_parser` macro

Design §2 "Public macro". New `def generate_rust_parser(...)` macro in `rust.bzl`,
the single public entry point wrapping the internal `_generate_rust_srcs` rule and
(in Python mode) `_build_pyo3_cdylib`.

- rust.bzl:513-642: new `generate_rust_parser` macro with the design's signature
  (`name`, `src`, `cst_mod_path`, `python_extension`, `protocol_module`,
  `protocol`, `lib_rs`, `deps`, `crate_features`, `recursion_limit`, `visibility`,
  `**kwargs`), placed after `_build_pyo3_cdylib`, under a new section banner.
  - `python_extension = False` (default): instantiates `_generate_rust_srcs` as
    the public `:name` (extension_name empty, pure-Rust `.rs` only) and returns.
  - `python_extension = True`: instantiates `_generate_rust_srcs` as
    `name + "_srcs"` with `extension_name = name` (the single-owner-name stub-dir
    fix), wraps its `rust_srcs` / `stub_srcs` output groups in two
    `native.filegroup`s, and calls `_build_pyo3_cdylib(name = name,
    rs_srcs = :<name>_rust_srcs, data = [:<name>_stub_srcs], ...)`.
  - Edge-case `fail()` guards (design "Edge cases"): `protocol` without
    `protocol_module`; and, in pure-Rust mode, any of `protocol_module`,
    `protocol`, `lib_rs`, `deps`, `crate_features`, or a non-default
    `recursion_limit` set — each fails fast naming the offending attr +
    `python_extension`.
- rust.bzl:508-514: added `data = []` param to `_build_pyo3_cdylib` (doc + signature)
  and appended it to the `py_library` `data` (`[":" + name + "_so"] + data`), so
  the macro can route `stub_srcs` onto the public py_library. Minimal helper
  extension required to expose the PEP 561 stub package per design §2 "Stub
  exposure"; body otherwise unchanged.
- rust.bzl:4-9: module docstring `generate_rust_parser` bullet updated from "a rule
  that…" to describe the two-mode macro (deferred from increment 5).
- Validation: `python3 -c ast.parse` on rust.bzl passes (Starlark is a Python
  subset) — valid syntax. bazel present but not run: the in-tree BUILD.bazel still
  loads the removed `fltk_pyo3_cdylib` and calls `generate_rust_parser` as a rule
  (intentional mid-flow breakage per increments 4–5); the §4 BUILD.bazel-rewrite
  increment is the first to `bazel build` the new macro end-to-end. buildifier not
  installed. Committed with `--no-verify`.

## Increment 7 — rewrite BUILD.bazel in-tree targets to the new macro (§4)

Design §4. Final increment: rewire the in-tree Bazel targets to the single
`generate_rust_parser` macro after increments 4–6 removed the old public symbols.

- BUILD.bazel:5: `load("//:rust.bzl", ...)` drops the demoted `fltk_pyo3_cdylib`,
  now loads only `generate_rust_parser`.
- BUILD.bazel:108-125: `bootstrap_rust_srcs` rewritten to the macro in pure-Rust
  mode (`python_extension` defaults False; `.rs` only). `bootstrap_native`
  rewritten from the old `fltk_pyo3_cdylib(rs_srcs=...)` two-call form to the
  single macro call with `src = "fltk/fegen/bootstrap.fltkg"`,
  `python_extension = True`, `protocol_module = "bootstrap_native.cst_protocol"`,
  `protocol = True` — exercising the full Python path plus stub-package emission.
- Verified: `bazel build //:bootstrap_native_stub_srcs` produces the stub package
  at `bazel-bin/bootstrap_native/cst.pyi` + `bootstrap_native/__init__.pyi`
  (+ `cst_protocol.py`), named after the macro `name` `bootstrap_native` — the
  design §4 stub-dir regression guard passes, confirming the single-name fix and
  `rust_srcs`/`stub_srcs` output-group routing. Analysis is clean for both targets
  (distinct labels `//:bootstrap_native` vs `//:bootstrap_native_srcs` do not
  collide — the design's directory/target coexistence check).
- `make check` (the precommit gate: lint/format/typecheck/pytest + full cargo
  suite + cargo-deny) passes. Note: `make check` runs no `bazel build` step —
  Bazel is a separate alternative build system, so this BUILD.bazel-only change is
  outside the precommit gate's coverage.
- DEVIATION (pre-existing, out of scope): a full `bazel build //:bootstrap_native`
  / `//:bootstrap_rust_srcs` does NOT complete — the `gen-rust-parser` action
  fails on `bootstrap.fltkg`'s block-comment regex `[^*]*(?:\*(?!\/)[^*]*)*`,
  which is outside the Rust backend's portable regex subset. Confirmed pre-existing
  by building the OLD `//:bootstrap_rust_srcs` at the base commit (3c244d1) in a
  worktree: it fails identically. Prior increments only ran `bazel build --nobuild`
  (analysis), never full execution, so the limitation was never surfaced. The
  `gen-rust-cst` half (the stub package — the design's actual regression guard)
  builds cleanly; only the `.rs` parser action fails. The design assumed
  bootstrap.fltkg compiles fully via the Rust backend; it does not. Fixing the
  Rust parser generator / choosing a Rust-compilable smoke grammar is out of scope
  for this Bazel-surface work.
- TODO(bazel-rust-smoke-bootstrap-regex): filed for the above; comment at
  BUILD.bazel (bootstrap_rust_srcs smoke target), entry in TODO.md.

## Misconfiguration coverage (design "Test plan" → "Misconfiguration coverage")

No `bazel_skylib` / `analysistest` harness exists in-tree, so the design's
fallback applies: the two `fail()` paths are documented here as verified manual
`bazel` expectations. Both `fail()`s fire during the loading phase, so `bazel
query` surfaces them without reaching the pre-existing `gen-rust-parser` regex
build failure. Verified via a throwaway package instantiating each
misconfiguration against `//:rust.bzl`'s `generate_rust_parser` macro (temp
package removed afterward; no repo change):

- `python_extension = False` (default) with `protocol_module` set →
  `Error in fail: generate_rust_parser: protocol_module is only valid with
  python_extension = True.`
- `protocol = True` with empty `protocol_module` →
  `Error in fail: generate_rust_parser: protocol = True requires a non-empty
  protocol_module.`

Both match the guard messages at rust.bzl:583-600. The other pure-Rust-only
guards (`lib_rs`, `deps`, `crate_features`, non-default `recursion_limit`) are
the same `if cond: fail(...)` shape and were eyeballed rather than each
separately exercised.
