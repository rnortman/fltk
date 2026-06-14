# Correctness review: generate_rust_lib (rust.bzl)

Reviewed: HEAD 8f97975 vs base c08b5c5. Scope: new `generate_rust_lib` Starlark
rule in rust.bzl replacing the prior lib.rs genrule.

## No findings.

Verified the following, all correct:

- **ctx.actions.run wiring** (rust.bzl:48-54): `executable = ctx.executable._gen_tool`,
  `outputs = [lib_out]`, `arguments = [args]`, `inputs = []`. The empty inputs list
  is correct — gen-rust-lib takes no grammar file (genparser.py:401-435 confirms it
  needs no input file; lib.rs has no rule-derived content). Tool runfiles are pulled
  in automatically via the executable= path.

- **Tool resolution** (rust.bzl:77-82): `_gen_tool` private attr defaults to
  `Label("//:genparser")` with `executable=True, cfg="exec"`. Because the default is a
  `Label()` constructed in fltk's rust.bzl, it resolves to `@fltk//:genparser`
  (BUILD.bazel:13, public visibility), not the consumer repo. This is the documented
  fix for the cross-repo `$(location)` fragility the old genrule worked around, and it
  is more robust: a rule's private label attr is resolved in the rule-definition repo,
  so out-of-tree consumers (Clockwork) resolve fltk's genparser correctly. Matches the
  sibling generate_rust_parser `_gen_tool` attr exactly (rust.bzl:169-174).

- **Argument passing / CLI signature match** (rust.bzl:36-46 vs genparser.py:400-429):
  Order is `gen-rust-lib`, positional `<output_file>` (= lib_out), `--module-name`,
  `<module_name>`, then conditional `--no-cst` / `--register-span-types` /
  `--unknown-span-static`. This exactly matches the typer signature (output_file
  positional first, module_name as --module-name option, three bool flags). Flag names
  match verbatim. Bools are added only when True (correct for store-true flags); when
  False, omitting them is correct. No flag/value mismatch.
  Note: the rule does not expose `--no-parser`, but that is a feature-surface choice,
  not a correctness bug — defaults produce the standard cst+parser lib.rs.

- **Span-only flag interlock**: genparser.py:451 rejects `--register-span-types` /
  `--unknown-span-static` without `--no-cst`. The rule does not enforce this at
  analysis time, so a caller setting register_span_types=True without no_cst=True
  would fail at action execution rather than analysis. Not a logic bug in the rule
  (the CLI guards it); just a later failure point. No current caller hits it
  (TODO(bazel-lib-rs-no-cst) documents that all callers use the default path).

- **Output naming** (rust.bzl:34): `declare_file(ctx.attr.name + "/lib.rs")`. With the
  macro calling `generate_rust_lib(name = name + "_gen_lib", ...)`, the output path is
  `<name>_gen_lib/lib.rs` — byte-identical to the old genrule's
  `gen_lib_rs_out = name + "_gen_lib/lib.rs"`. The downstream assembly genrule consumes
  it via `lib_rs = ":" + name + "_gen_lib"` and `cat $(location {lib_rs})`; the rule
  returns a single-file depset (rust.bzl:56), so `$(location)` is unambiguous — this
  removes the prior TODO(bazel-lib-rs-location) single-out caveat.

- **No behavioral change to generated lib.rs**: old genrule ran
  `genparser gen-rust-lib $@ --module-name '<name>'` with no extra flags. New rule runs
  the same command with all three bools defaulting False (no extra flags emitted). The
  module_name passed is `name` in both cases. Identical command -> identical output.
  The shell-quoting around module_name in the old genrule is now unnecessary (args
  passed as a list to ctx.actions.run, no shell), which is strictly safer, not a
  behavior change.

- **Hermeticity**: action declares all outputs, has no undeclared inputs, no shell, no
  $@ ambiguity. Consistent with generate_rust_parser.
