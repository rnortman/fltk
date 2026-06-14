# Design: Codegen the Rust `lib.rs` boilerplate

Scope spans two repos: **fltk** (`/home/rnortman/src/fltk`) — the generator, CLI,
Bazel surface, and `fltk._native` migration — and **clockwork**
(`/home/rnortman/tps/clockwork`) — the consumer migration. Requirements:
`requirements.md`. Exploration: `exploration.md`.

## 1. Root cause / context

Every Rust-backend consumer hand-authors a `lib.rs` whose entire job is module
wiring: a fixed set of `use` declarations, `mod cst;` / `mod parser;`
declarations, and a `#[pymodule]` function whose body is `register_submodule`
calls. The clockwork file is the canonical example (`clockwork/dsl/clockwork_native_lib.rs:10-25`):

```rust
use fltk_cst_core::register_submodule;
use pyo3::prelude::*;
mod cst;
mod parser;
#[pymodule]
fn clockwork_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    register_submodule(m, "cst", cst::register_classes)?;
    register_submodule(m, "parser", parser::register_classes)?;
    Ok(())
}
```

Nothing in this file is consumer-specific except the `#[pymodule]` function name
(`clockwork_native`), which the Bazel macro *already* knows as the target `name`
attribute (`rust.bzl:173` — "Must match the `#[pymodule]` fn name in lib_rs").
The submodule names (`"cst"`, `"parser"`) and registration entry points
(`cst::register_classes`, `parser::register_classes`) are invariant across all
standard consumers because `generate_rust_parser` emits exactly `cst.rs` and
`parser.rs` with `register_classes` entry points (`rust.bzl:39-40`;
exploration §1). So the consumer is forced to copy/paste a file that the
toolchain has all the information to produce.

The two generators (`RustCstGenerator`, `RustParserGenerator`) emit `cst.rs` and
`parser.rs` but neither emits `lib.rs`, and neither takes a module name
(exploration §1, line 48). The CLI (`genparser.py`) has `gen-rust-cst` and
`gen-rust-parser` sub-commands but no `gen-rust-lib` (genparser.py:265, 368).

`fltk._native` (`src/lib.rs:1-38`) is a structurally-distinct singleton: it is
the canonical provider of `Span`/`SourceText`/`UnknownSpan` and the
`UNKNOWN_SPAN` static, and it hosts two grammar submodules under custom names
(`poc_cst` ← `cst_generated.rs`, `fegen_cst` ← `cst_fegen.rs`) rather than the
standard one-CST + one-parser layout. Its module/file mapping is non-standard
(the file basenames `cst_generated`/`cst_fegen` differ from the registered
submodule names `poc_cst`/`fegen_cst`).

Why this matters per CLAUDE.md: `lib.rs` contains only module wiring and
introduces **no** rule-derived public symbols. The `#[pymodule]` function name
is supplied externally, not derived from grammar rules. So this work is purely
additive to the build pipeline and touches no downstream-visible API surface
(exploration §7). The risk surface is build-mechanics regressions, not API
churn.

## 2. Proposed approach

### 2.1 Scope decisions (resolving the requirements' open questions)

The requirements doc carries these as open questions but states an assumed
default for each. This design adopts those defaults; they are restated here as
decisions, with the genuinely user-facing one surfaced in §5.

- **`cst-only-mode`**: supported at the **CLI/generator level only** (a
  `--no-parser` flag; default parser included). It is deliberately **not** wired
  into the Bazel macro — see §2.5 for why (Bazel's `generate_rust_parser` always
  emits both `cst.rs` and `parser.rs` and the assembly requires both). Rationale:
  `tests/rust_cst_fixture` is CST-only (exploration §6) and the generator cost is
  one boolean flag; no in-scope target needs CST-only via Bazel.
- **`submodule-naming`**: fixed to `cst` and `parser` for the standard
  generator. These names are load-bearing in the Bazel assembly and the
  `--cst-mod-path super::cst` default (`rust.bzl:82-90`).
- **`multi-grammar-mode`**: out of scope for the *standard* generator. The
  standard template is one CST + optional one parser. Multi-grammar crates
  (`tests/rust_parser_fixture`) are covered only by the `fltk._native`-style
  specialized path (§2.4) or remain hand-written (§2.6).
- **`bazel-lib_rs-attribute`**: `lib_rs` becomes optional, defaulting to a
  generated `lib.rs`. An explicitly-supplied `lib_rs` still overrides
  (backward-compatible; preserves the escape hatch for custom wiring).
- **`native-special-mechanism`**: a *dedicated specialized path* (a parameter
  bundle / config object) produces `fltk._native`, not a flag-explosion on the
  standard CLI. See §5 open question — whether codegenning `fltk._native` at all
  is worth the bespoke machinery is the one genuine user-judgment call.

### 2.2 New generator: `gsm2lib_rs.py`

New module `fltk/fegen/gsm2lib_rs.py` with a `RustLibGenerator`. Unlike the CST
and parser generators, this generator does **not** consume grammar rules to
produce symbols — `lib.rs` has no rule-derived content. It is a small templating
unit over a structured description of the module layout. It therefore does not
need a `gsm.Grammar` at all; it takes a layout descriptor.

Core data type (a frozen dataclass in `gsm2lib_rs.py`):

```python
@dataclass(frozen=True)
class Submodule:
    mod_name: str        # Rust `mod <mod_name>;` — the .rs file basename stem
    submodule_name: str  # Python submodule name passed to register_submodule
    register_fn: str = "register_classes"

@dataclass(frozen=True)
class LibSpec:
    module_name: str               # #[pymodule] fn name; the importable module
    submodules: tuple[Submodule, ...]
    register_span_types: bool = False   # fltk._native special-case
    unknown_span_static: bool = False   # fltk._native special-case
    cfg_python_gate: bool = False       # emit #[cfg(feature = "python")] gates
```

`RustLibGenerator(spec: LibSpec).generate() -> str` emits the complete `lib.rs`
string. Two convenience constructors keep the common cases terse:

- `LibSpec.standard(module_name, *, with_parser=True)` → the clockwork case:
  submodules `[Submodule("cst", "cst"), Submodule("parser", "parser")]` (parser
  dropped when `with_parser=False`).
- A module-level `native_spec()` factory (in fltk, not the generic generator)
  builds the `fltk._native` `LibSpec` literally (§2.4).

**Standard output** (mirrors the requirements' illustrative shape; emitted
directly by the generator — no formatter pass applies, see the formatting note
below):

```rust
use fltk_cst_core::register_submodule;
use pyo3::prelude::*;

mod cst;
mod parser;

#[pymodule]
fn <module_name>(m: &Bound<'_, PyModule>) -> PyResult<()> {
    register_submodule(m, "cst", cst::register_classes)?;
    register_submodule(m, "parser", parser::register_classes)?;
    Ok(())
}
```

Per the requirements "Note on shape," exact emitted text (import ordering,
`#[cfg]` gates) is a design choice; the observable constraints are the binding
requirement. Note: unlike the Python generators, `.rs` output is **not**
normalized by `make fix` — `make fix` runs only ruff (Makefile:85-87) and there
is no rustfmt/`cargo fmt` step anywhere in the build (the existing generated
`src/cst_generated.rs` / `src/cst_fegen.rs` are likewise never run through a Rust
formatter). The real "done" gate for generated `.rs` is **compilation** (cargo
check/clippy for fixtures; maturin `build-native` for `src/lib.rs`), not
formatting. The generator should therefore emit text that compiles; matching a
formatter is neither required nor verifiable here.

The generated standard `lib.rs` **omits** `#![recursion_limit]` (the Bazel macro
owns and injects it — Constraint "recursion_limit ownership (resolved)";
`rust.bzl:226`). It also omits Span/SourceText registration and the
`UNKNOWN_SPAN` static (consumers import those from `fltk._native` at runtime;
requirements "Standard consumer generator").

**Validation**: `module_name` and each `mod_name`/`submodule_name`/`register_fn`
must be validated as Rust identifiers / paths. Reuse the existing
`_CST_MOD_PATH_RE`-style pattern (genparser.py:365). An empty or invalid
`module_name` raises `ValueError` naming the offending value; the CLI converts
that to a `typer.Exit(1)` with a clear message (matching
`gen-rust-parser`'s existing handling, genparser.py:381-391).

### 2.3 CLI: `gen-rust-lib`

New `@app.command(name="gen-rust-lib")` in `genparser.py`:

```
gen-rust-lib <output_file> --module-name <name> [--no-parser]
```

Note: unlike `gen-rust-cst`/`gen-rust-parser`, this command needs **no grammar
file** for the standard case — `lib.rs` has no rule-derived content. (Taking a
grammar argument would be consistent in shape but misleading and would force a
parse that produces nothing; we omit it. This is called out as a deliberate
divergence from the other two sub-commands.) If the requirements' "consistent
with existing sub-commands" intent is read strictly to mean "accept a grammar
positional," that is a thin alternative — see §5.

- `--module-name` (required): validated; empty/invalid → `typer.Exit(1)` naming
  the value.
- `--no-parser`: emit a CST-only `lib.rs` (omits `mod parser;` and its
  registration), covering `cst-only-mode`.
- `<output_file>`: write target. Generate the string first, then write, so a
  generation error leaves no partial file (matching the existing pattern at
  genparser.py:346-351).

The `fltk._native` specialized layout is **not** exposed as generic CLI flags
(per §2.1 `native-special-mechanism`). It is produced by a dedicated command
(§2.4).

### 2.4 `fltk._native` specialized generation

`fltk._native`'s `LibSpec` is fully determined and unique. Rather than growing
the standard CLI with `--register-span-types`, `--unknown-span-static`, and
repeated `--submodule mod=name=fn` flags (which would exist solely to describe a
single in-tree file), we encode the `fltk._native` layout as a fixed factory and
expose a dedicated, parameterless CLI command:

```
gen-rust-native-lib <output_file>
```

This calls `RustLibGenerator(native_spec()).generate()`, where `native_spec()`
returns:

```python
LibSpec(
    module_name="_native",
    submodules=(
        Submodule("cst_generated", "poc_cst"),
        Submodule("cst_fegen", "fegen_cst"),
    ),
    register_span_types=True,
    unknown_span_static=True,
)
```

The generator, when `register_span_types`/`unknown_span_static` are set, emits
the extra imports and statements observed in `src/lib.rs:1-38`: the
`pyo3::sync::PyOnceLock` import, `mod span;` + `use span::{SourceText, Span};`,
the `m.add_class::<Span>()` / `m.add_class::<SourceText>()` registrations, the
`UnknownSpan` module attribute, and the `UNKNOWN_SPAN.set(...)` once-init. The
`UNKNOWN_SPAN` static declaration and its explanatory comment (src/lib.rs:11-17)
are reproduced verbatim from a constant string in the generator (it is internal
documentation, not rule-derived).

This keeps `fltk._native`'s bespoke knowledge in **one** place (the
`native_spec()` factory + the special-case branches in `RustLibGenerator`)
rather than scattered across CLI invocation flags. The standard generator stays
minimal.

`fltk._native` also has the file/submodule-name mismatch
(`mod cst_generated` registered as `poc_cst`) and a `mod span;` declaration —
both naturally expressed by the `Submodule(mod_name, submodule_name)` split and
a fixed `mod span;` emission gated on `register_span_types`.

### 2.5 Bazel surface (fltk `rust.bzl`)

Make `lib_rs` on `fltk_pyo3_cdylib` optional (default `None`). When omitted, the
macro generates `lib.rs` from the target `name`. Concrete mechanism:

1. Change the `lib_rs` parameter (`rust.bzl:126`) to default `None`.
2. When `lib_rs is None`, instantiate a new `genrule` named `name + "_gen_lib"`
   that runs `$(location //:genparser) gen-rust-lib $@ --module-name <name>`,
   declaring a single output (e.g. `name + "_gen_lib/lib.rs"`) and adding
   `//:genparser` to its `tools`. Because `gen-rust-lib` takes **no grammar
   file** (§2.3), this is a standalone genrule, not the grammar-driven
   `generate_rust_parser` rule — `generate_rust_parser` cannot host it. Set the
   local `lib_rs` variable to `":" + name + "_gen_lib"`.
3. The existing assembly genrule (`rust.bzl:220-239`) then consumes that label
   through its `srcs`/`$(location {lib_rs})` slots (`rust.bzl:222,227`). This is
   the one wiring change beyond "as today": the assembly's `lib_rs` input now
   resolves to a generated target instead of a checked-in file; everything
   downstream (the `#![recursion_limit]` prepend at `rust.bzl:226`, the
   `cst.rs`/`parser.rs` copy and presence checks) is unchanged, so recursion_limit
   ownership is unchanged (Constraint: resolved).
4. **Smoke coverage (in scope):** wire `TODO(fltk-pyo3-cdylib-smoke)`
   (BUILD.bazel:117-122) to a `fltk_pyo3_cdylib` target with **no** `lib_rs`,
   driven by `bootstrap_rust_srcs` (or an equivalent in-tree
   `generate_rust_parser` output), so the no-`lib_rs` generation branch has
   automated in-repo coverage.

**CST-only is not wired into Bazel.** `generate_rust_parser` unconditionally
emits both `cst.rs` and `parser.rs` (`rust.bzl:39-40`) and the assembly genrule
unconditionally requires both present (`rust.bzl:231-232`). A `cst_only` /
`with_parser` macro attribute would control only the lib.rs shape, not those
outputs or the presence check, leaving an unreconciled coupling (a CST-only
`lib.rs` would still have a sibling `parser.rs` copied in, and the mandatory
`parser.rs` check still runs). No in-scope migration target needs CST-only Bazel
(all three fixtures stay hand-written, §2.7; clockwork has a parser), so this
design **omits** the Bazel `cst_only`/`with_parser` attribute. `--no-parser`
remains a CLI flag only (§2.3), for the Makefile/maturin path. Adding CST-only
Bazel later requires also gating `generate_rust_parser`'s parser output and the
assembly presence check — out of scope here.

Backward compatibility: an explicit `lib_rs` continues to be used verbatim
(opt-in migration; Constraint "Backward compatibility / opt-in",
exploration §7.5). The `WARNING` in the macro docstring about `rs_srcs` not
emitting a `lib.rs` basename (`rust.bzl:181-185`) still holds and is unaffected.

Note: `fltk._native` is **not** built via `fltk_pyo3_cdylib` — it is a maturin
crate (`pyproject.toml:27-30`, `Cargo.toml`). So the Bazel change does not touch
`fltk._native`; that migration is Makefile/maturin-only (§2.7).

### 2.6 Clockwork migration

In `clockwork/dsl/BUILD.bazel:75-80`, drop the `lib_rs` attribute from the
`fltk_pyo3_cdylib(name = "clockwork_native", ...)` call so the macro generates
`lib.rs` from `name = "clockwork_native"`. Delete
`clockwork/dsl/clockwork_native_lib.rs`. The resulting module exposes the same
`clockwork_native.cst` and `clockwork_native.parser` submodules with the same
registered classes (acceptance criterion, requirements "Standard consumer
generator"). The in-file `TODO(native-submodule-error-context)` comment
(clockwork_native_lib.rs:18-21) is orphaned by deletion — see §3 / §4.

### 2.7 `fltk._native` and fixture migration (fltk Makefile)

`fltk._native`: add a `gen-rust-native-lib` invocation to the `gencode` target
(`Makefile:235`) that writes `src/lib.rs`, alongside the existing
`gen-rust-cst` calls for `src/cst_generated.rs` and `src/cst_fegen.rs`
(Makefile:253-260). `build-native` (Makefile:186) compiles the generated
`src/lib.rs` via maturin. The committed `src/lib.rs` becomes generated output
with the **same drift posture as the other generated `.rs` files**: `make check`
gates that it *compiles* (via `build-native`/cargo), but does **not** regenerate
it or diff it against generator output. `check-common` (Makefile:39-51) never
invokes `gencode`. Drift between the committed file and generator output is
caught only by the manual `make gencode` + `git diff --stat` workflow the
Makefile documents (Makefile:233-234) — exactly how `cst_generated.rs` /
`cst_fegen.rs` are handled today. There is no rustfmt step, so no formatting
normalization applies (see §2.2).

Fixtures: only **standard-shaped** fixture lib.rs files are migration
candidates. None of the three qualifies:

- `tests/rust_cst_fixture/src/lib.rs` registers `Span`/`SourceText` at top level
  and adds three `native_tests`/`registry_introspection` functions and extra
  `mod` declarations (lib.rs:14-26). **Non-standard → remains hand-written.**
- `tests/rust_cst_fegen/src/lib.rs` is standard (cst + parser, no extras) except
  for a `mod native_parser_tests;` line and `#[cfg(feature="python")]` gating
  (lib.rs:9-24). The extra test mod makes it non-standard → **remains
  hand-written** unless the generator grows an "extra mods" hook (out of scope).
- `tests/rust_parser_fixture/src/lib.rs` is multi-grammar (cst/parser +
  collision_cst/collision_parser) plus `mod native_tests;` (lib.rs:1-20).
  Multi-grammar is out of scope → **remains hand-written.**

Per requirements "Migration of in-tree fixtures": fixtures exercising
non-standard shapes may retain hand-written `lib.rs`, and that is acceptable.
The migration target set is therefore **clockwork** + **`fltk._native`** (the
two the request named explicitly); all three fixtures stay hand-written because
they carry test-only `mod` declarations and non-standard registrations that the
standard generator intentionally does not model. This is a deliberate,
called-out outcome.

## 3. Edge cases / failure modes

- **Empty/invalid module name** → `ValueError` in the generator, `typer.Exit(1)`
  naming the value at the CLI (requirements "Error messages"). Covered by tests.
- **`recursion_limit` double-injection**: the generated `lib.rs` must NOT contain
  `#![recursion_limit]`; the Bazel macro injects it (`rust.bzl:226`). A test
  asserts the generated string does not contain `recursion_limit`. If it did,
  the assembled crate root would have the attribute twice → compile error.
- **`rs_srcs` emitting a `lib.rs` basename**: the macro's assembly copies
  generated `cst.rs`/`parser.rs` by basename *after* writing `lib.rs`
  (`rust.bzl:228-229`); a generated `lib.rs` from `gen-rust-lib` lives in a
  separate action output, so there is no basename collision. The existing
  WARNING invariant is preserved.
- **CST-only with a stale `mod parser;`**: `--no-parser` must omit both the
  `mod parser;` declaration and the registration; emitting one without the other
  fails to compile. Single flag controls both.
- **`fltk._native` once-init**: `UNKNOWN_SPAN.set(...)` uses
  `.expect("UNKNOWN_SPAN already set; module initialized twice")`
  (src/lib.rs:26-28). The generated output reproduces this exactly so the
  "initialized once" semantic (requirements "fltk._native special case") holds.
- **Submodule/file-name mismatch (`fltk._native`)**: `mod cst_generated` →
  `poc_cst`. The `Submodule(mod_name, submodule_name)` split models this; a
  naive single-name model would emit the wrong `mod` or registration name.
- **Orphaned TODO on clockwork deletion**: deleting `clockwork_native_lib.rs`
  drops the `TODO(native-submodule-error-context)` inline comment
  (clockwork_native_lib.rs:18). That slug has **no** `TODO.md` entry in either
  repo — it lives only as this inline comment (plus historical ADR dispositions
  at `docs/adr/2026/06/13-rust-bazel-packaging/`). The TODO concerns
  `register_submodule` error context — a `fltk_cst_core` concern, not the
  consumer file. When deleting the clockwork file, relocate the comment to the
  `register_submodule` definition in `fltk_cst_core`
  (`crates/fltk-cst-core/src/py_module.rs:87`) **and** add the matching
  `native-submodule-error-context` entry to fltk `TODO.md` — CLAUDE.md's TODO
  System requires both halves (the slug currently has only the inline comment,
  violating the convention). Alternatively, adjudicate the TODO for removal per
  the check-todos rubric rather than perpetuating an orphan (§4).

## 4. Test plan

After this change the following tests exist.

**Unit (string output, no compilation) — fltk `tests/` or `fltk/fegen/`:**

- `RustLibGenerator` standard output contains: `use fltk_cst_core::register_submodule;`,
  `mod cst;`, `mod parser;`, `fn <module_name>(`, both
  `register_submodule(m, "cst", cst::register_classes)` and `... "parser" ...`,
  and `Ok(())`.
- Standard output does **not** contain `recursion_limit`, `Span`, `SourceText`,
  `UnknownSpan`, or `UNKNOWN_SPAN`.
- `--no-parser` / `with_parser=False` output omits `mod parser;` and the parser
  registration but keeps `mod cst;`.
- Invalid module name (empty, `"1bad"`, `"has space"`, `"a-b"`) raises
  `ValueError` naming the value.
- `native_spec()` output contains: `mod span;`, `use span::{SourceText, Span};`,
  `pyo3::sync::PyOnceLock`, `m.add_class::<Span>()`, `m.add_class::<SourceText>()`,
  `m.add("UnknownSpan"`, the `UNKNOWN_SPAN` static, the `.expect(...)` once-init
  message, `register_submodule(m, "poc_cst", cst_generated::register_classes)`,
  and `... "fegen_cst", cst_fegen::register_classes ...`, and `fn _native(`.

**CLI tests (typer runner) — extend genparser CLI tests:**

- `gen-rust-lib out.rs --module-name clockwork_native` writes a file containing
  the standard module.
- Missing/empty `--module-name` exits non-zero with a message naming the
  problem.
- `gen-rust-native-lib out.rs` writes the `fltk._native` layout.

**Integration / behavioral:**

- **fltk**: `make gencode` regenerates `src/lib.rs`; `make build-native`
  compiles it; existing `fltk._native` import tests still pass (`Span`,
  `SourceText`, `UnknownSpan`, `poc_cst`, `fegen_cst` all resolve). `make check`
  passes because the committed generated `src/lib.rs` *compiles* (via
  `build-native`/cargo). Drift detection is **not** part of `make check`
  (`check-common`, Makefile:39-51, does not run `gencode`); it is the manual
  `make gencode` + `git diff --stat` step (Makefile:233-234) the developer runs,
  same as for `cst_generated.rs`/`cst_fegen.rs`. No formatting gate applies
  (no rustfmt; see §2.2).
- **clockwork**: `bazel build //clockwork/dsl:clockwork_native` succeeds with no
  `lib_rs` attribute; `clockwork_rust_roundtrip_test`
  (BUILD.bazel:87) passes — proving the generated `lib.rs` produces a
  behaviorally-equivalent module (acceptance criterion).
- **Bazel macro**: a build of a `fltk_pyo3_cdylib` target without `lib_rs`
  succeeds; a build with an explicit `lib_rs` still uses the supplied file
  (backward-compat). **In scope (not optional):** wire the in-tree
  `TODO(fltk-pyo3-cdylib-smoke)` smoke target (BUILD.bazel:117-122) to exercise
  the no-`lib_rs` path. Without this, the new lib.rs-generation branch — the most
  mechanically novel part of the Bazel change — ships with zero automated
  coverage inside the fltk repo; the requirement lists "a consumer Bazel target
  can build `fltk_pyo3_cdylib` without supplying a hand-written `lib_rs`" as an
  fltk-side acceptance criterion, so it must be verifiable in-repo rather than
  only transitively via clockwork's out-of-repo build. See §2.5 step 4.

**TODO handling:** `native-submodule-error-context` has no `TODO.md` entry —
it is an inline-only comment in the clockwork file, which already violates
CLAUDE.md's two-part TODO convention (slug requires both a `TODO.md` entry and a
`TODO(slug)` comment). On deleting that file, relocate the
`TODO(native-submodule-error-context)` comment to the `register_submodule`
definition in `fltk_cst_core` (`crates/fltk-cst-core/src/py_module.rs:87`, its
true home) **and** add the matching `native-submodule-error-context` entry to
fltk `TODO.md` so the convention is satisfied — merely moving the comment would
perpetuate the orphan. If the work is judged not worth tracking, adjudicate it
for removal instead. This is bookkeeping, not new functionality.

## 5. Open questions

1. **Is codegenning `fltk._native` worth the bespoke path?** (requirements
   `native-special-mechanism`.) `fltk._native` is a singleton with unique,
   non-reusable responsibilities (Span/SourceText/UnknownSpan, the
   `UNKNOWN_SPAN` static, two custom-named submodules with file/name mismatch).
   The replicated-consumer payoff that justifies the standard generator does not
   apply: generating one file via a one-off `native_spec()` + special-case
   generator branches may cost more machinery than the 38-line boilerplate it
   removes. Options: **(a)** generate it via the dedicated path in §2.4 (this
   design's default — satisfies the explicit request); **(b)** scope this work
   to the standard consumer generator only and leave `src/lib.rs` hand-written.
   This is the one genuine user-judgment call; everything else follows the
   requirements' stated defaults.

2. **Should `gen-rust-lib` accept a grammar positional for CLI symmetry?**
   (requirements "CLI" says "consistent with existing sub-commands.") The
   standard `lib.rs` needs no grammar (no rule-derived content), so §2.3 omits
   it. If "consistent" is meant strictly (every sub-command takes
   `<grammar_file>`), the command would accept and ignore it (or use it only to
   auto-detect CST-only vs. with-parser by checking whether the grammar yields a
   parser). Default: omit the grammar argument; surface here in case the
   requester wants strict positional symmetry or grammar-driven CST-only
   detection.
