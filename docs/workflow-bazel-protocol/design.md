# Design: unify FLTK's Bazel parser-codegen surface

Scope and settled decisions are in
[`requirements.md`](./requirements.md); current-state facts are in
[`exploration.md`](./exploration.md). This document does not restate them; it
specifies the change.

## Root cause / context

FLTK ships two Bazel codegen entry points that have drifted apart:

- **Python backend** — `generate_parser` rule (`rules.bzl:47-82`). Opts into the
  protocol module with a single bool `protocol` (`rules.bzl:71-74`).
- **Rust backend** — `generate_rust_parser` rule (`rust.bzl:192-267`) plus the
  `fltk_pyo3_cdylib` macro (`rust.bzl:271-462`). Opts into the protocol `.py`
  module with a bool named `generate_protocol` (`rust.bzl:221-229`), and keeps a
  separate string `protocol_module` (`rust.bzl:210-220`) for the `.pyi` dotted
  import path.

Three concrete problems follow from this shape:

1. **Gratuitous name divergence.** The same concept ("also emit the protocol
   `.py` module") is spelled `protocol` on the Python rule and `generate_protocol`
   on the Rust rule.

2. **Two-call surface.** A Rust consumer must instantiate `generate_rust_parser`
   (`.rs` output) and then `fltk_pyo3_cdylib` (crate assembly → `rust_shared_library`
   → abi3 rename → `py_library`), threading the first target's label into the
   second (`rust.bzl:325-333`). The Clockwork call site shows the required pairing
   (`/home/rnortman/tps/clockwork/clockwork/dsl/BUILD.bazel:70-82`).

3. **Latent stub-directory bug.** The PEP 561 stub package must be a directory
   named after the *compiled Python module*. That module name is the
   `fltk_pyo3_cdylib` target `name` (it becomes the crate name and the
   `#[pymodule]` fn name — `rust.bzl:414`, `rust.bzl:362`). But the codegen rule
   derives both the stub-package subdirectory and the `--extension-name` CLI flag
   from **its own** target `name` (`rust.bzl:124`, `144-153`, `161`). These are
   two independent caller-chosen strings on two separate targets; nothing threads
   one into the other. In Clockwork they differ (`clockwork_rs_srcs` vs
   `clockwork_native`), so a stub package, if emitted, would be named after the
   wrong thing. It is latent only because no live call site sets `protocol_module`
   today (`exploration.md` §3).

The single-name macro proposed below removes divergence #1 by renaming, collapses
#2 into one call, and eliminates #3 structurally: one owner `name` is
simultaneously the compiled module name, the `--extension-name`, and the
stub-package directory, so there is no second name to fall out of sync.

The CLI (`genparser.py`) already accepts explicit output paths, `--extension-name`,
`--protocol-module`, `--protocol-output`, `--init-pyi-output`, and `--submodules`
(`genparser.py:329-406`). No CLI flag needs to change; all work stays in the Bazel
layer, per requirements.

## Proposed approach

### 1. Rename the Rust protocol toggle

Rename the Rust bool `generate_protocol` → `protocol`, matching the Python rule.
The string `protocol_module` (dotted `.pyi` import path) is unchanged — it has no
Python-side analog. The existing coupling stays: `protocol = True` requires
`protocol_module` non-empty, and `protocol_module` non-empty is what triggers
`.pyi` emission. This is a pure rename of the boolean; the trigger relationship is
not redesigned. The rule's analysis-time guard (`rust.bzl:120-121`) and the CLI's
`--protocol-output requires --protocol-module` check (`genparser.py:458-460`) are
retained; only the guard's referenced attribute name changes.

### 2. Split `generate_rust_parser` into an internal rule + public macro

**Internal codegen rule** — the current `generate_rust_parser` rule
(`rust.bzl:192-267`) is renamed to a private rule (proposed `_generate_rust_srcs`)
and gains one new attribute:

- `extension_name` (string, default `""`) — when non-empty, this value is used as
  BOTH the `--extension-name` CLI argument and the output subdirectory that holds
  the generated files (`cst.rs`, `parser.rs`, and, when `protocol_module` is set,
  `cst.pyi` / `__init__.pyi` / `cst_protocol.py`). When empty, the subdirectory
  falls back to `ctx.attr.name` (preserving today's behavior for the pure-Rust
  case, where no stub is emitted and the subdir name is irrelevant to type
  resolution).

  This attribute is the structural fix: the stub-package directory and
  `--extension-name` are decoupled from the rule's own target name and instead
  driven by a value the macro sets to the single owner `name`.

Otherwise the internal rule keeps its two independent actions (`gen-rust-cst` and
`gen-rust-parser`, `rust.bzl:132-188`), its `src` / `cst_mod_path` attributes, the
renamed `protocol` bool, and `protocol_module`.

**Output routing.** The internal rule exposes its outputs both as `DefaultInfo`
(all declared files) *and* as an `OutputGroupInfo` with two named groups, so the
macro can route heterogeneous outputs without addressing individual files:

- `rust_srcs` — always `[<name>/cst.rs, <name>/parser.rs]`.
- `stub_srcs` — the files that ride along on the compiled Python module:
  `<name>/cst.pyi` + `<name>/__init__.pyi` when `protocol_module` is non-empty,
  plus `<name>/cst_protocol.py` when `protocol = True`. When `protocol_module` is
  empty this group is an **empty depset**.

Output groups are load-bearing here because a Bazel macro cannot address an
individual `declare_file` output (e.g. `":" + name + "/cst.pyi"`) by label — only
the target and its providers are visible. The groups let the macro feed just the
`.rs` files to crate assembly and just the stub/protocol files to
`py_library.data`, and an empty `stub_srcs` group extracts to nothing rather than
to a dangling label.

**Public macro** — a new `generate_rust_parser(...)` *macro* (a `def`, replacing
the old rule of that name) is what consumers call. Signature (proposed):

```python
def generate_rust_parser(
        name,
        src,
        cst_mod_path = "super::cst",
        python_extension = False,   # the pure-Rust ↔ Python-extension toggle
        protocol_module = "",
        protocol = False,
        # Python-extension-only knobs (folded in from fltk_pyo3_cdylib):
        lib_rs = None,
        deps = [],
        crate_features = [],
        recursion_limit = 512,
        visibility = None,
        **kwargs):
```

The macro instantiates targets differently per mode:

**`python_extension = False` (default — pure Rust).**
- Instantiate the internal codegen rule with `name = name` (it *is* the public
  target), passing `src`, `cst_mod_path`, `visibility`. `extension_name` is left
  empty.
- Emit only `cst.rs` / `parser.rs` under `<name>/`. No `.pyi`, no protocol module,
  no cdylib, no `py_library`.
- `protocol_module`, `protocol`, and the Python-only knobs (`lib_rs`, `deps`,
  `crate_features`, `recursion_limit`) must be at their defaults; otherwise the
  macro `fail()`s with a message pointing at `python_extension` (see Edge cases).
- The public `:name` target provides the `.rs` files for the consumer to drop into
  their own crate.

**`python_extension = True` (full Python extension).**
- Instantiate the internal codegen rule as `name + "_srcs"` with
  `extension_name = name` (the single owner name), plus `src`, `cst_mod_path`,
  `protocol_module`, `protocol`. Outputs land under `<name>/`.
- Fold in the four `fltk_pyo3_cdylib` steps (crate assembly genrule →
  `rust_shared_library` cdylib → abi3 rename → `py_library`), with the public
  `py_library` named `name`. The crate-assembly genrule consumes **only the
  `rust_srcs` output group** of `":" + name + "_srcs"` (the `.rs` files), not the
  whole target — so the `.pyi` / `.py` outputs never enter the flat crate root.
  `lib_rs` / `deps` / `crate_features` / `recursion_limit` / `visibility` /
  `**kwargs` flow into this path exactly as they do into `fltk_pyo3_cdylib` today.
- Stub emission stays *optional and gated on `protocol_module`*, matching today's
  behavior (the rename does not force stubs on):
  - `protocol_module = ""` → cdylib + `py_library` only, no stubs.
  - `protocol_module = "x"` → additionally `<name>/cst.pyi` + `<name>/__init__.pyi`
    (stub package named after `name`, i.e. the compiled module — the bug fix).
  - `protocol_module = "x"`, `protocol = True` → additionally
    `<name>/cst_protocol.py`.
- Stub exposure: the macro adds the internal rule's `stub_srcs` output group to
  the public `py_library` `name` as `data`, so a downstream target depending on
  `:name` gets both the runtime `.so` and the PEP 561 stub package. Because
  `stub_srcs` is empty exactly when `protocol_module` is empty (and omits
  `cst_protocol.py` unless `protocol = True`), this routing is self-gating: the
  explicitly-valid `python_extension = True`, `protocol_module = ""` case ("cdylib
  + `py_library` only, no stubs") adds nothing to `data` and references no
  undeclared file. This replaces today's pattern of depending on the separate
  `generate_rust_parser` label for `.pyi` files (`exploration.md` §5, step 2). The
  `.rs` files stay internal to crate assembly; the `.pyi` stub package and, when
  generated, the `cst_protocol.py` module reach `:name` through `stub_srcs`.

**Toggle attribute name.** `python_extension` (bool, default `False`) is chosen
because it self-documents intent (`python_extension = True` = "build the Python
extension"). Alternatives considered: `python` (too generic), `pyo3` (leaks the
implementation), `build_python` (verb-y). This is a deliberate design choice, not
an open question — the requirements delegated it.

### 3. Demote `fltk_pyo3_cdylib` to an internal helper

Rather than delete the working four-step logic (`rust.bzl:271-462`) and its
extensive load-bearing comments, rename the `def` to a private helper (proposed
`_build_pyo3_cdylib`) with the same body, and call it from the macro's
`python_extension = True` branch. Drop `fltk_pyo3_cdylib` from the public surface:
remove it from the BUILD.bazel `load` (`BUILD.bazel:5`). Also update the file-level
module docstring's load example (`rust.bzl:13`) and the two `fltk_pyo3_cdylib`
references in doc strings (`rust.bzl:89`, `rust.bzl:251`) so the source no longer
advertises a symbol removed from the public surface. The `generate_rust_lib`
rule (`rust.bzl:58-98`) and the auto-`lib_rs` path (`rust.bzl:359-364`) are kept
unchanged, reached through the helper.

Removing the public name is sanctioned by requirements (breaking the Bazel
authoring surface is explicitly permitted; Clockwork migration is out of tree).

### 4. Keep the in-tree build green

`BUILD.bazel` currently has `bootstrap_rust_srcs` (old rule) and `bootstrap_native`
(old `fltk_pyo3_cdylib`) — `BUILD.bazel:111-126`. Update the `load` and rewrite
these to the new macro so both code paths stay covered:

- `generate_rust_parser(name = "bootstrap_rust_srcs", src = ..., python_extension = False)`
  — exercises the pure-Rust path (`.rs` only).
- `generate_rust_parser(name = "bootstrap_native", src = ..., python_extension = True,
  protocol_module = "bootstrap_native.cst_protocol", protocol = True)` — exercises
  the full Python path *including* stub-package emission, which no in-tree target
  does today. This turns the latent stub-dir bug into an actively built regression
  case: the stub package must materialize at `bootstrap_native/cst.pyi` and
  `bootstrap_native/__init__.pyi`.

No `Makefile` change: the regen path (`gencode`) invokes the CLI directly with
`--protocol` / `--init-pyi-output` / `--extension-name` / `--submodules`
(`exploration.md` §4), none of which are renamed. The Python `generate_parser` rule
and its `protocol` attribute are untouched.

## Edge cases / failure modes

- **Python-only attrs set with `python_extension = False`.** Setting
  `protocol_module`, `protocol`, `lib_rs`, `deps`, `crate_features`, or a
  non-default `recursion_limit` while `python_extension = False` is a
  misconfiguration (pure Rust produces no cdylib/stub). The macro `fail()`s at
  evaluation time with a message naming the offending attribute and
  `python_extension`. Fail-fast beats silently ignoring the value.
- **`protocol = True` with empty `protocol_module`.** Still rejected — retained at
  the internal rule's analysis-time guard (former `rust.bzl:120-121`) and mirrored
  in the CLI (`genparser.py:458-460`). The macro may additionally `fail()` early
  for a clearer message.
- **Directory/target name coexistence.** In `python_extension = True` mode the
  internal rule (target `name + "_srcs"`) declares outputs under directory
  `<name>/`, while the `py_library` target is `name`. These are distinct labels
  (`//pkg:name/cst.rs` vs `//pkg:name`) and do not collide, but this must be
  confirmed by an actual `bazel build` of the smoke target (see Test plan) — it is
  the one non-obvious analysis-time property of the single-name design.
- **Stub/protocol files must not reach crate assembly.** The internal rule's
  `DefaultInfo` bundles `.rs` *and* (when protocol is on) `.pyi` / `.py`. Feeding
  that whole target to the crate-assembly genrule would copy the `.pyi` / `.py`
  into the flat crate root — files the genrule does not declare in `outs`. Bazel
  discards undeclared genrule outputs, so it is likely harmless, but the design
  does not rely on that: crate assembly consumes only the `rust_srcs` output group
  (§2), so no non-`.rs` file enters the crate root. The `bootstrap_native` smoke
  target (protocol on) is the first in-tree build to exercise this and is the
  regression guard.
- **`rs_srcs` basename `lib.rs` hazard.** The old `fltk_pyo3_cdylib` warned callers
  never to pass an `rs_srcs` whose outputs include `lib.rs` (`rust.bzl:327-333`).
  With the codegen rule now internal and always the macro's own, this hazard is no
  longer consumer-reachable; the guard comment moves into the helper as an
  internal invariant.
- **`no_trivia` / span-only lib.rs.** The pre-existing `TODO(bazel-lib-rs-no-cst)`
  (`rust.bzl:382-386`) is unaffected and carried into the helper verbatim.

## Test plan

After this change the following exists:

- **Pure-Rust smoke target** (`bootstrap_rust_srcs`, `python_extension = False`):
  `bazel build //:bootstrap_rust_srcs` produces `bootstrap_rust_srcs/cst.rs` and
  `bootstrap_rust_srcs/parser.rs` and nothing else (no cdylib, no `.pyi`).
- **Python-extension smoke target** (`bootstrap_native`, `python_extension = True`,
  `protocol_module` set): `bazel build //:bootstrap_native` produces the abi3 `.so`
  and the `py_library`, AND the stub package at `bootstrap_native/cst.pyi` +
  `bootstrap_native/__init__.pyi` — asserting the stub directory is named after the
  macro `name` (the compiled module), which is the regression guard for the
  stub-dir bug. This also confirms the directory/target name coexistence above.
  Crate assembly for this target draws only the `.rs` files (via the `rust_srcs`
  output group), so the assembled crate root contains exactly `lib.rs` / `cst.rs` /
  `parser.rs` and no `.pyi` / `.py`.
- **Misconfiguration coverage.** Where FLTK can assert analysis failures (e.g. a
  `bazel build` expected to fail, or an existing negative-target harness),
  cover: `python_extension = False` with `protocol_module` set; `protocol = True`
  with empty `protocol_module`. If no harness exists, these are documented as
  manual `bazel build` expectations rather than automated tests.
- **Python `generate_parser` unchanged.** Its existing smoke targets
  (`BUILD.bazel:78-106`) still build; its `protocol` attribute is unaffected.
- **Generated artifacts unchanged.** Because no CLI flag or generator logic
  changes, the byte content of `cst.rs` / `parser.rs` / `cst.pyi` /
  `cst_protocol.py` is identical to today for the same grammar — only their Bazel
  wiring and the stub-dir *name* change. Existing generator-level tests remain
  valid without modification.

## Open questions

None. The two choices the requirements delegated to design — the toggle attribute
name and the fate of `fltk_pyo3_cdylib` — are decided above (`python_extension`;
demote to a private `_build_pyo3_cdylib` helper). No remaining question requires
user judgment.
