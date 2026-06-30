# Deep correctness review — codegen protocol + .pyi outputs

Commit reviewed: 19348b3a8900ae0eaf883f3f7b3531b029d9a814 (base f0edfd75)

## Findings

No findings.

## What was traced (no bugs found)

- **Cross-path protocol byte-identity (central risk, design §1.2).** `RustCstGenerator.generate_protocol`
  builds a fresh `CstGenerator` with `py_module=pyreg.Module(["_protocol"])` (non-empty → `kind` Literal
  emitted, not degraded `kind: object`). Confirmed structurally: within protocol generation `self.py_module`
  is used only at `gsm2tree.py:891` (truthiness gate); rule refs emit bare quoted Protocol names, and
  library types resolve via their canonical module (terminalsrc), not `py_module`, so the placeholder value
  never reaches output. Grammar set matches across paths: both apply `add_trivia_rule_to_grammar`
  (idempotent — returns unchanged when `_trivia` present) + `classify_trivia_rules` (only flips
  `is_trivia_rule`, which protocol generation ignores). Empirically: `test_..._matches_python_protocol`
  passes; `simple_grammar` exercises both the `kind` Literal and the Span library-type annotation path.
- **Fresh context / no shared-state mutation.** `generate_protocol` constructs its own `CstGenerator` +
  `create_default_context()`; it does not mutate `self._py_gen`, `self.context`, or `self.grammar` (grammar
  is read-only iterated). `.rs` output unchanged confirmed by `test_..._rs_unchanged_with_protocol_output`.
- **`generate` opt-in gate.** Protocol write moved behind `if protocol or protocol_only:`. All four
  flag combinations traced; `--protocol-only` still short-circuits and wins; no double-write when both flags
  set; verbose echo uses an inline path recompute so no NameError when the block is skipped.
- **Write ordering / partial-file invariant.** gen-rust-cst generates all artifact text (pyi, protocol,
  src) before any write; `init_pyi_text` rendered before grammar parse. Validation (`--protocol-output`
  requires `--protocol-module`; `--init-pyi-output` requires name+submodules; identifier checks) all precede
  parse and any write — confirmed by the "nothing written on rejection" tests.
- **Marker rendering + drift.** `render_stub_package_init` validates identifiers, rejects empty submodule
  list, emits comment-only newline-terminated text. Committed `fltk/_stubs/{fegen_rust_cst,rust_parser_fixture}/__init__.pyi`
  verified byte-equal to live generator output (drift clean). `gen-rust-unparser` marker write is top-level
  (not nested under `if pyi_text`), so the fixture's no-`--protocol-module` routing works.
- **Bazel wiring** (`rules.bzl`, `rust.bzl`) is additive/default-off; `fail()` guards `generate_protocol`
  without `protocol_module`; `cst_outputs` depset has no duplicates. (Note, not a bug: with `protocol_module`
  set, `--extension-name {name}` now requires the target name to be a valid identifier — correct, since it
  is the stub-package import name.)

All targeted new + adjacent tests pass (28 + 6 + 4 selected).
