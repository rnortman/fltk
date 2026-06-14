# Requirements: Codegen the Rust `lib.rs` boilerplate

## Goals

Eliminate the hand-written `lib.rs` boilerplate that every Rust-backend consumer currently
authors by generating it from the FLTK toolchain. The end state: both `fltk._native` and the
Clockwork integration crate obtain their `lib.rs` from codegen, and a new downstream consumer can
stand up an `fltk_pyo3_cdylib` extension module without writing any Rust module-wiring boilerplate
by hand.

## In scope

- A generator that emits a complete, compilable `lib.rs` for the **standard consumer** layout
  (the Clockwork case): one CST submodule + one parser submodule, registered into a named
  `#[pymodule]`.
- A CLI surface to invoke that generator (analogous to the existing `gen-rust-cst` /
  `gen-rust-parser` sub-commands in `genparser.py`).
- A Bazel surface so that `fltk_pyo3_cdylib` consumers no longer need to author and pass a
  `lib_rs` file; the macro obtains the generated `lib.rs` instead.
- Producing `fltk._native`'s `lib.rs` from codegen as well, including its special registrations
  (`Span`, `SourceText`, `UnknownSpan`, the `UNKNOWN_SPAN` static, and its multiple non-standard
  submodules). See "fltk._native special case" for how this is handled.
- Migrating the existing hand-written `lib.rs` files (Clockwork, `fltk._native`, and the in-tree
  fixture crates) to the generated form, OR retiring them in favor of the generated output, such
  that no hand-written `lib.rs` boilerplate remains for these targets.

## Out of scope

- Any change to the **Python-visible API surface**: generated CST class names, accessor methods,
  `NodeKind` members, `Label` enum names, parser bindings, and their type-annotation /
  equality / comparison surfaces are unchanged. `lib.rs` contains only module wiring and
  introduces no rule-derived public symbols. (CLAUDE.md: generated symbols are downstream API.)
- Changing the contents or shape of generated `cst.rs` / `parser.rs`.
- Changing the Python backend in any way; this is Rust-backend-only.
- Changing how `#[pymodule]` function names map to importable module / `.so` names (that mapping
  already exists; this work only supplies the function body and declarations).

## System behavior

### Standard consumer generator

Input:
- A grammar (the same grammar input the CST/parser generators consume).
- A **module name** (the importable extension-module name, e.g. `clockwork_native`), supplied
  explicitly as a CLI argument / Bazel attribute. The grammar itself carries no name field, so
  the module name is always an external input.

Output: a single `lib.rs` string that, when assembled alongside the generated `cst.rs` and
`parser.rs`, compiles into a working pyo3 cdylib. Observable constraints on the generated file
(the exact emitted source — import ordering, glob vs. enumerated imports, statement layout — is a
design choice and may be normalized for cleanliness; see "Note on shape" below):

- It defines a `#[pymodule]` function named exactly the supplied module name, taking the standard
  pyo3 module-init signature.
- The compiled module exposes a `cst` submodule and a `parser` submodule, each populated by the
  registration entry point of the correspondingly generated `cst.rs` / `parser.rs`.
- It does NOT re-register `Span` / `SourceText` / `UnknownSpan` and does NOT declare an
  `UNKNOWN_SPAN` static (consumers import those from `fltk._native` at runtime).
- It is compatible with the `#![recursion_limit]` ownership resolved in Constraints (the generated
  file omits that attribute; the Bazel assembly injects it).

Note on shape: the request explicitly sanctions reshaping the boilerplate ("it's boilerplate, and
we can fix its shape"). The hard requirement is the observable import surface and behavior above;
the internal shape of the emitted `lib.rs` may be regularized/normalized where that simplifies the
generator or the output, and need not reproduce the current hand-written files token-for-token.

Illustrative (non-normative) shape — a generated standard `lib.rs` would look approximately like:

```rust
use fltk_cst_core::register_submodule;
use pyo3::prelude::*;

mod cst;
mod parser;

#[pymodule]
fn <module-name>(m: &Bound<'_, PyModule>) -> PyResult<()> {
    register_submodule(m, "cst", cst::register_classes)?;
    register_submodule(m, "parser", parser::register_classes)?;
    Ok(())
}
```

The designer may deviate from this exact text as long as the observable constraints hold.

Acceptance criteria:
- Replacing Clockwork's hand-written `clockwork_native_lib.rs` with the generated `lib.rs`
  (module name `clockwork_native`) produces a behaviorally-equivalent module: the resulting
  extension exposes the same `clockwork_native.cst` and `clockwork_native.parser` submodules with
  the same registered classes as today. Source-level byte-equivalence with the hand-written file is
  NOT required (and is not expected, since generator output is normalized by `make fix`).
- The generated standard `lib.rs` is parameterized only by the module name; no other consumer
  input is required for the standard one-grammar layout.
- A consumer Bazel target can build `fltk_pyo3_cdylib` without supplying a hand-written
  `lib_rs` file.

### fltk._native special case

`fltk._native` is structurally non-standard: it is the canonical provider of `Span`,
`SourceText`, `UnknownSpan` and the `UNKNOWN_SPAN` static, and it hosts multiple grammar
submodules (`poc_cst`, `fegen_cst`) rather than the standard one CST + one parser.

Requirement: `fltk._native`'s `lib.rs` must end up codegenned (no hand-written boilerplate
remaining). The chosen approach (a dedicated specialized template/mode versus a flag-driven
general generator) is a design decision, but the result must satisfy (these are observable /
behavioral requirements; the exact emitted source is a design choice and may be normalized):

- The rebuilt `fltk._native` is behaviorally equivalent at the Python-import surface to the
  current hand-written one: `Span` and `SourceText` are exposed as classes, `UnknownSpan` is
  available as a module attribute, the `UNKNOWN_SPAN` singleton is initialized exactly once, and
  each grammar submodule is registered under its current name (`poc_cst`, `fegen_cst`).
- Whatever imports / statements the special registrations require are present so the file compiles.

Cost/benefit caveat: per the exploration (§2, §4, open question 1), `fltk._native` is a *singleton*
with unique, non-reusable responsibilities. The replicated-consumer payoff (Clockwork, future
downstream) does not apply to it — generating a one-off file via a one-off code path may cost more
machinery than the boilerplate it removes. It is in scope because the request named it explicitly,
but this is the lowest-confidence part of the scope. See Open questions →
`native-special-mechanism`, which now also asks the requester to confirm this sub-goal is worth the
specialized machinery (vs. leaving `fltk._native` hand-written).

### Migration of in-tree fixtures and crates

The three in-tree fixture crates (`tests/rust_cst_fixture`, `tests/rust_cst_fegen`,
`tests/rust_parser_fixture`) and the Clockwork integration crate today carry hand-written
`lib.rs` files. Acceptance: after this change, the standard-shaped ones are produced by the
generator. Fixtures that exercise non-standard shapes (CST-only, multi-grammar) are governed by
the Open questions on those modes — if those modes are not implemented, those fixtures may retain
hand-written `lib.rs` and that is acceptable.

## User-visible surface

### CLI

A way to generate `lib.rs` from the FLTK CLI, consistent with the existing `genparser.py`
sub-commands. Most plausible shape (subject to design): a new `gen-rust-lib` sub-command:

```
gen-rust-lib <grammar_file> <output_file> --module-name <name>
```

- `--module-name` (required): the `#[pymodule]` function name / importable module name.
- `<output_file>`: path to write the generated `lib.rs`.

Error messages: a missing/empty `--module-name` must fail with a clear error rather than emitting
an unnamed module. An invalid Rust identifier as a module name must be rejected with a message
naming the offending value.

### Bazel

`fltk_pyo3_cdylib` consumers no longer need a hand-authored `lib_rs`. Most plausible shape:
the macro derives the `lib.rs` from the target `name` (which already drives the `#[pymodule]`
function name and `.so` stem) and the generated `cst.rs` / `parser.rs`, so the `lib_rs` attribute
becomes optional/unnecessary for the standard layout. Existing consumers that still pass a
hand-authored `lib_rs` must continue to work (opt-in migration; see Constraints → compat).

### Makefile / maturin

The Makefile path that builds `fltk._native` (and the fixture crates, where applicable) gains a
generation step for `lib.rs`, consistent with the existing `gencode` invocations of
`gen-rust-cst` / `gen-rust-parser`.

## Constraints

- **No Python API churn.** Adding `lib.rs` codegen is purely additive to the build pipeline and
  must not rename or alter any generated public symbol, nor force any downstream annotation/call-site
  change. (CLAUDE.md, exploration §7.)
- **Backward compatibility / opt-in.** Existing consumers with a hand-authored `lib.rs` must not
  break. Switching to generated `lib.rs` is opt-in. No existing downstream consumer is broken by
  merely adding the capability. (exploration §7.5.)
- **Cross-backend equivalence.** The Python-import surface of the resulting extension modules
  (which submodules and classes are registered, `UnknownSpan` semantics) is unchanged versus the
  current hand-written `lib.rs` files. This constrains observable behavior, not the internal source
  shape — see System behavior → "Note on shape": the emitted `lib.rs` may be normalized.
- **`#![recursion_limit]` ownership (resolved).** The Bazel `fltk_pyo3_cdylib` assembly currently
  injects `#![recursion_limit = "N"]` at assembly time, and the consumer file must NOT contain it
  (clockwork_native_lib.rs:7-8). Resolution for this work: the macro continues to own and inject
  this attribute at assembly time, and the generated `lib.rs` therefore OMITS it. This is the
  assumption consistent with the Bazel surface below (the macro still assembles the generated
  `lib.rs` with `cst.rs` / `parser.rs`). The attribute must appear exactly once (macro-injected).
  If the design instead chooses to emit `lib.rs` directly bypassing the macro's assembly, that is a
  design-level change that must move recursion_limit ownership into the generator and is called out
  here as the trigger for revisiting this resolution.
- **Generated-code formatting.** Per CLAUDE.md, generator output need not pass `ruff`/formatter
  checks straight out; the regen → `make fix` → commit flow applies. The generated `lib.rs` must be
  clean after `make fix` so `make check` passes on committed output.

## Open questions

- **`native-special-mechanism`**: Should `fltk._native`'s non-standard `lib.rs` (Span/SourceText/
  UnknownSpan registration, `UNKNOWN_SPAN` static, multiple custom-named submodules) be produced by
  a *separate specialized generator/template/mode*, or by extending the single generator with flags
  (e.g. `--register-span-types`, repeated `--submodule name=register_fn`)? Assumed default for this
  spec: a dedicated specialized path for `fltk._native`, since it is a singleton with unique
  responsibilities, while the standard generator stays minimal (module name only). If the user wants
  one flag-driven generator covering both, say so and the standard CLI grows submodule/registration
  flags. **Also for the requester to confirm:** is codegenning `fltk._native` worth the specialized
  machinery at all? It is a singleton — a one-off file produced by a one-off code path — so the
  payoff is far lower than for the replicated consumer case. Options: (a) generate it (current
  default — accept the bespoke path); (b) leave `fltk._native` hand-written and scope this work to
  the standard consumer generator only.

- **`cst-only-mode`**: Should the standard generator support CST-only modules (no parser submodule),
  as in `tests/rust_cst_fixture`? Assumed default: yes — a parser submodule is included only when a
  parser is generated; a CST-only flag/mode omits `mod parser;` and its registration. If the user
  considers CST-only out of scope, those fixtures keep hand-written `lib.rs`. To redirect: "parser is
  always present" or "CST-only not needed."

- **`multi-grammar-mode`**: Should one generated `lib.rs` host multiple grammars/submodules (as in
  `tests/rust_parser_fixture` with `cst`/`parser` + `collision_cst`/`collision_parser`)? Assumed
  default: out of scope for the standard generator; the standard template is one grammar (one CST,
  optional one parser). Multi-grammar crates either remain hand-written or are covered only via the
  `fltk._native`-style specialized path. To redirect: "multi-grammar must be a first-class CLI mode."

- **`submodule-naming`**: The standard layout fixes submodule names to `cst` and `parser`. Assumed
  default: these are fixed (not parameterized) for the standard generator, matching Clockwork. To
  redirect: "submodule names must be configurable."

- **`bazel-lib_rs-attribute`**: Should the `lib_rs` attribute on `fltk_pyo3_cdylib` be removed,
  made optional (default = generated), or kept as an override hook? Assumed default: made optional —
  defaults to the generated `lib.rs`, but an explicitly-supplied `lib_rs` still overrides it
  (preserves backward compatibility and supports any consumer that genuinely needs custom wiring).
