# Security review — codegen-rust-lib-boilerplate

Commits reviewed:
- fltk: 7200d9c..25bbfef
- clockwork: 6ede250..ea34388

Scope: new `gsm2lib_rs.py` Rust `lib.rs` generator + `gen-rust-lib` /
`gen-rust-native-lib` CLI commands; `fltk_pyo3_cdylib` Bazel macro now
auto-generates `lib.rs` from the target `name`; clockwork drops its
hand-written `clockwork_native_lib.rs`; a TODO comment in `py_module.rs`;
`src/lib.rs` mod-order cleanup.

## Trust model

This is entirely build-time codegen. The only inputs are:
- a Bazel target `name` (BUILD-file-author controlled, build time)
- a `--module-name` CLI arg (build-author controlled)
- an `output_file` path (build-author controlled)

There is no runtime path, no network/user/file-content input crossing a
trust boundary into this code. The "attacker" would have to control the
BUILD.bazel / Makefile / CLI invocation — i.e. already have commit/build
access. Findings below are therefore defense-in-depth observations, not
exploitable-from-untrusted-input vulnerabilities.

## Findings

### security-1 — `name` interpolated unquoted into genrule shell cmd (defense-in-depth)
File: `rust.bzl:213`
Issue: `fltk_pyo3_cdylib` builds the genrule `cmd` via
`"... gen-rust-lib $@ --module-name {module_name}".format(module_name = name)`.
The target `name` is interpolated unquoted into a shell command string.
Data flow: `name` (BUILD-file author) -> macro -> genrule `cmd` -> shell.
The Rust-identifier validation (`_RUST_IDENT_RE`) lives *inside* the
`gen-rust-lib` Python command, which runs only *after* the shell has already
parsed the line — so the regex does not protect the shell. Bazel's own target
name grammar disallows most shell metacharacters and spaces, which is what
actually prevents injection here; the macro is relying on that implicit
constraint rather than quoting.
Consequence: A target `name` containing shell-significant characters that
Bazel nonetheless permits would be expanded by the shell before genparser's
validation could reject it. In practice Bazel target-name rules make this
hard/impossible to weaponize, and the actor is already the build author, so
impact is minimal. Mentioned only because the code reads as "validated" when
the validation is on the wrong side of the shell boundary.
Suggested fix: shell-quote the interpolated value, e.g. pass
`--module-name '{module_name}'`, or assert the Rust-ident constraint in
Starlark (`name` matches `[A-Za-z_][A-Za-z0-9_]*`) before constructing the
genrule, so the guarantee is enforced before the shell sees it.

### security-2 — generator emits `module_name` into Rust source unescaped (defense-in-depth)
File: `fltk/fegen/gsm2lib_rs.py:316-344`, `genparser.py:139`
Issue: `module_name` / submodule names are interpolated directly into the
generated Rust (`fn {module_name}(...)`, the `fltk.{module_name}.UnknownSpan`
comment, `register_submodule(m, "{submodule_name}", ...)`). This is gated by
`_validate_rust_ident` (anchored `^[A-Za-z_][A-Za-z0-9_]*$`, linear — no ReDoS),
which is the correct guard and *is* applied before generation
(`RustLibGenerator.__init__` calls `spec.validate()`).
Data flow: CLI `--module-name` -> `LibSpec` -> validated -> emitted Rust.
Consequence: With the validation in place, no Rust-source/string injection is
possible (the charset excludes `"`, `}`, newlines, etc.). If the validation
were ever removed or a future caller constructed a `RustLibGenerator` from an
unvalidated path, the submodule-name interpolation into the `"..."` string
literal would become a Rust string/code-injection vector. Currently safe.
Suggested fix: none required. Keep `validate()` as the single mandatory gate
(it already is, via `__init__`); do not add an unvalidated construction path.

### security-3 — no path validation on output_file (acceptable for build-time tool)
File: `genparser.py:150-154`, `181-183`
Issue: `output_file.write_text(src)` writes to an arbitrary
caller-supplied path with no normalization/confinement.
Data flow: CLI arg / genrule `$@` -> `Path` -> `write_text`.
Consequence: A caller could direct output anywhere the process can write
(overwrite). The caller is the build author / genrule (which controls `$@`
to a sandboxed declared output), so there is no privilege escalation or
untrusted-input traversal. Acceptable for a developer codegen CLI.
Suggested fix: none required.

## Other changed code
- `crates/fltk-cst-core/src/py_module.rs`: comment-only (TODO). No impact.
- `src/lib.rs`: mod-ordering / comment cleanup, behavior-equivalent. No impact.
- Test files, TODO.md, Makefile, BUILD.bazel: no security-relevant surface.

No secrets, no crypto, no auth surface, no deserialization, no SSRF, no
network or runtime untrusted input introduced by this change.
