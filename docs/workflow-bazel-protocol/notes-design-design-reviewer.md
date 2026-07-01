# Design review: unify FLTK's Bazel parser-codegen surface

Reviewer posture: adversarial fact-check. Base commit 3b95f0a.

## Verification summary (grounded, no finding)

Every load-bearing factual claim in the design was checked against source and holds:

- `generate_parser` Python rule with `protocol` bool — `rules.bzl:61-72`, `if ctx.attr.protocol` at `rules.bzl:44-47`. Confirmed.
- Rust rule `generate_rust_parser` at `rust.bzl:192-267`; `generate_protocol` bool `rust.bzl:221-229`; `protocol_module` string `rust.bzl:210-220`. Confirmed.
- Analysis-time guard `if generate_protocol and not protocol_module: fail(...)` at `rust.bzl:120-121`. Confirmed.
- Output paths derived from `ctx.attr.name`: `cst.rs`/`parser.rs` `rust.bzl:124-125`; `cst.pyi`/`__init__.pyi` `rust.bzl:144-145`; `--extension-name ctx.attr.name` `rust.bzl:152-153`; `cst_protocol.py` `rust.bzl:161`. Confirmed — the stub-dir/extension-name are indeed driven by the codegen rule's own name.
- `fltk_pyo3_cdylib` macro `rust.bzl:271-462`; four steps (auto lib.rs `359-364`, assembly genrule `387-406`, `rust_shared_library` with `crate_name = name` `409-435`/`414`, abi3 rename `442-447`, `py_library(name=name)` `456-462`). `module_name = name` at `rust.bzl:362`. Confirmed.
- CLI (`genparser.py`) already accepts `--extension-name`/`--protocol-module`/`--protocol-output`/`--pyi-output`/`--init-pyi-output`/`--submodules`; validation `--protocol-output requires --protocol-module` at `genparser.py:458-459` (also `--pyi-output requires --protocol-module` at `455-456`). No CLI change needed — confirmed.
- Clockwork call site (`/home/rnortman/tps/clockwork/clockwork/dsl/BUILD.bazel:70-82`): `generate_rust_parser(name="clockwork_rs_srcs")` + `fltk_pyo3_cdylib(name="clockwork_native")`, names differ, neither sets protocol_module/generate_protocol — confirms the bug is real but latent. Confirmed.
- In-tree callers: only `BUILD.bazel:5` (load) and `BUILD.bazel:111-126` (bootstrap_rust_srcs, bootstrap_native). No other in-tree target depends on these two. `Makefile` uses the CLI directly, not the Bazel rules — so "no Makefile change" is correct.

Requirements coverage: all four requested changes (rename, unified macro, pure-Rust toggle, structural stub-dir fix) plus keep-in-tree-green map to design sections 1-4. Toggle name (`python_extension`) and `fltk_pyo3_cdylib` fate (demote to `_build_pyo3_cdylib`) — both delegated choices, both decided. No scope creep; the added `extension_name` attr and `fail()` guards are necessary, not speculative.

## Findings

### design-1 — "Stub exposure" paragraph reads as unconditional; must be gated on `protocol_module`

Section 2, `python_extension = True`, "Stub exposure" paragraph: "the macro adds the internal rule's stub outputs (`<name>/__init__.pyi`, `<name>/cst.pyi`) to the public `py_library` `name` as `data` ... the `.py` protocol module, when generated, is likewise exposed via `:name`."

The design elsewhere (same section's gating bullet list) correctly establishes that `<name>/cst.pyi`, `<name>/__init__.pyi` exist only when `protocol_module` is non-empty, and `<name>/cst_protocol.py` only when `protocol = True`. But the "Stub exposure" paragraph states the `data` additions without restating that conditionality. Those files are declared outputs of the internal `_generate_rust_srcs` rule *only* in those cases (see `rust.bzl:138-164`, where the `declare_file` calls live inside `if protocol_module:` / `if generate_protocol:`). Referencing a file label like `":" + name + "/cst.pyi"` as `data` when the file was never declared is a Bazel analysis error ("no such target").

Consequence: if an implementer follows the "Stub exposure" paragraph literally and adds those labels to `py_library.data` unconditionally, the design's own explicitly-listed valid case — `python_extension = True` with `protocol_module = ""` ("cdylib + `py_library` only, no stubs") — fails at analysis time on a non-existent-label error. The macro must add the stub/protocol file labels to `data` only under the same `protocol_module` / `protocol` guards that gate their declaration.

Suggested fix: state the `data` additions inside the gating (e.g. "when `protocol_module` set, additionally add `<name>/cst.pyi` + `<name>/__init__.pyi` to `py_library.data`; when `protocol = True`, also add `<name>/cst_protocol.py`").

### design-2 — Crate-assembly genrule now receives `.pyi`/`.py` files for the first time; unmentioned in test plan

Section 2 folds in the assembly genrule "consuming `":" + name + "_srcs"` as `rs_srcs`". The internal rule's `DefaultInfo` includes not just `cst.rs`/`parser.rs` but also `cst.pyi`/`__init__.pyi`/`cst_protocol.py` when protocol is set (`rust.bzl:190`, outputs = `cst_outputs + [parser_out]`). The assembly genrule's copy loop is `for f in $(locations {rs_srcs}); do cp $$f $$OUTDIR/$$(basename $$f); done` (`rust.bzl:395-397`) with `outs` declaring only `crate_root/{lib,cst,parser}.rs` (`rust.bzl:390`).

The new `bootstrap_native` smoke target sets `protocol_module` + `protocol = True` (design §4), so this is the *first* built target where the loop copies `.pyi`/`.py` files into the crate root as files that are not declared genrule `outs`. Today no live caller sets protocol, so this path has never been exercised.

Consequence: almost certainly harmless (Bazel discards genrule-written files not in `outs`), but it is a genuinely newly-exercised path that the design's test plan does not name. If Bazel's sandbox/execution strategy in FLTK CI is stricter about undeclared genrule outputs than assumed, `bazel build //:bootstrap_native` fails. The `bazel build` in the test plan should be treated as the verification of this specific interaction, and if it is a concern the macro could pass only the `.rs` file labels to the assembly genrule rather than the whole `_srcs` target.

### design-3 — Stale `fltk_pyo3_cdylib` reference in the `rust.bzl` module docstring (doc hygiene)

Section 3 removes `fltk_pyo3_cdylib` from the public surface (BUILD.bazel load) and demotes it to `_build_pyo3_cdylib`. It does not mention the file-level module docstring at `rust.bzl:1-18`, whose usage example still reads `load("@fltk//:rust.bzl", "generate_rust_parser", "fltk_pyo3_cdylib")` (`rust.bzl:13`), plus the `generate_rust_lib` doc (`rust.bzl:89`) and the codegen-rule doc (`rust.bzl:251`) that reference `fltk_pyo3_cdylib` by name.

Consequence: after the change, the module's own documented load example advertises a symbol that no longer exists, misleading out-of-tree consumers reading the source. Low severity (docs, not behavior), but since the design is explicit about surface changes it should note updating these docstrings for consistency.

## Notes (not findings)

- The single flagged non-obvious property — coexistence of output directory `<name>/` (declared by target `name_srcs`) with the `py_library` target `name` (design "Directory/target name coexistence" edge case + test plan) — is correctly identified as requiring an actual `bazel build` to confirm. The design honestly gates the whole approach on that build succeeding. This is the right treatment; no finding.
- The design keeps generated artifact bytes identical (only Bazel wiring + stub-dir *name* change), consistent with CLAUDE.md's "generated output is public API" constraint. The Bazel authoring-surface break is explicitly sanctioned by requirements. Good.
