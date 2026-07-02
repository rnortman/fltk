# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `forged-abi-extract-span-uniformity`

`check_instance_layout` is generic and could be applied to `extract_span` for uniformity.
Currently `extract_span` is not reachable by forged objects (it is gated by `is_instance`
against the non-subclassable canonical `fltk._native.Span` type, plus `check_abi_pair::<Span>`
in `get_span_type`), so adding `check_instance_layout` there would add no rejection power.
Revisit only if a future change makes `extract_span` reachable by non-canonical types.
Location: `crates/fltk-cst-core/src/cross_cdylib.rs` (`extract_span`).

## `extend-children-owned`

`extend_children(&Self)` clones every child Arc even though the donor node is immediately dropped after the call (inline-to-parent sub-expression and `+`/`*` loop paths). A consuming variant `extend_children_owned(other: Self)` using `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`, `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>` blocks). Re-open only with profiling evidence.

## `spanprotocol-native-linecol`

`SpanProtocol.line_col` / `line_col_or_raise` are typed to return `terminalsrc.LineColPos`. The native `fltk._native.Span.line_col` returns the native `LineColPos` (a distinct nominal class declared in `fltk/_native/__init__.pyi`), so `fltk._native.Span` is **not statically** assignable to `SpanProtocol` — it conforms only by runtime `isinstance` plus its `.pyi` `span: SpanProtocol` declaration. This is a contained, pre-existing gap (the pure-Python parser, the only place a span *value* is statically assigned into a `SpanProtocol` slot within `make check`'s pyright scope, feeds `terminalsrc.Span`, which *is* statically conformant). Close it by unifying `LineColPos` across the two backends (one shared nominal type) so native spans conform statically too. Deferred per design-delta D5.2/D8; it does not block the span-isolation work. Location: `fltk/fegen/pyrt/span_protocol.py` (`line_col`/`line_col_or_raise` return annotations), `fltk/_native/__init__.pyi` (native `LineColPos`).

Constraint when closing this: the generated pipeline (parser/CST/protocol/unparser) imports `SpanProtocol`, and its R2 pyright stub-stability holds structurally only because `SpanProtocol`'s own definition names no `fltk._native` symbol (delta D5.1). The source-level "generated files name no native" tests (`fltk/fegen/test_cst_protocol.py`, `test_genparser.py`, `test_gsm2tree_rs.py`, `test_is_span_guard.py`) do NOT cover transitive stub-sensitivity introduced via `span_protocol.py` itself. If a fix makes `SpanProtocol`'s structural surface native-dependent, add a differential (stub-present-vs-absent) or structural stub-stability guard for the generated pipeline at the same time.


## `unparser-source-helper`

`fltk/unparse/test_is_span_guard.py`'s `_generate_unparser_source` re-implements `plumbing.generate_unparser`'s 7-step assembly pipeline (`create_default_context` → `add_trivia_rule_to_grammar` → `classify_trivia_rules` → `gsm2unparser.generate_unparser` → `compiler.compile_class` → `ast.Module` assembly → `ast.unparse`) because `plumbing.generate_unparser` exposes no way to retrieve the generated source before it `exec`s the module. The helper is called 4x in that file, and any change to the assembly list (new imports, reordered trivia steps) must be mirrored in both places or they drift. Expose a source-returning entry point — e.g. `plumbing.generate_unparser_source(grammar, cst_module_name, formatter_config)` returning the unparsed source, with `generate_unparser` exec'ing its output — and have the test call it, single-sourcing the pipeline. Location: `fltk/unparse/test_is_span_guard.py` (`_generate_unparser_source`), `fltk/plumbing.py` (`generate_unparser`, line ~257).

## `unparser-none-path-diagnostics`

The generated Rust unparser has two `None`-return paths that surface no diagnostic. (1) The non-trivia separator block calls `_has_preservable_trivia(&trivia_node)` and then `unparse__trivia(&trivia_node)` with no `else` arm, so when the helper confirmed comments exist but `unparse__trivia` returns `None` (label mismatch or sourceless content span), the comment is silently dropped from formatted output. (2) Labeled-span text extraction emits `let text = span.text()?;`, so a sourceless/sentinel span propagates `None` to the public `unparse_*` entry point with no record of which span/label failed. In the `fltkfmt` pipeline (`Parser::new(src, filename, true)`) every span carries source, so both are invariant-violation paths, not expected failures — hence deferred rather than fixed now. Closing this needs a deliberate cross-backend policy decision (log-and-continue vs `debug_assert!` vs halt) applied to **both** the Rust generator and the Python unparser so backend behavior stays in parity; emitting a Rust-only `eprintln` would diverge the backends. Locations: `fltk/unparse/gsm2unparser_rs.py` (the `if self._has_preservable_trivia(...)` / `if let Some(trivia_result)` block, ~line 1346; the `let text = span.text()?;` site in `_gen_regex_term_body`, ~line 1077).

## `fmt-cli-per-consumer-about`

`fltk-fmt-cli` is shared scaffolding consumed by out-of-tree formatter binaries for arbitrary FLTK grammars, but clap's `#[derive(Parser)]` bakes the `--help` `about` text into `FmtArgs` at the library's compile time. The grammar-specific `about = "Format FLTK grammar files."` was removed (clap now falls back to the struct doc comment), but there is still no hook for each consumer to supply its own description. When `run_main` / `fltk_formatter_main!` land (later increment), thread a per-consumer `about: &'static str` and build the command via `FmtArgs::command().about(..)` so each binary's `--help` describes the language it actually formats — otherwise `FmtArgs::parse()` inside `run_main` seals one wording in for every consumer. Location: `crates/fltk-fmt-cli/src/lib.rs` (`FmtArgs`, and the future `run_main`).

## `fltkfmt-integration-tests`

Design §4 specifies four `crates/fltkfmt/tests/` integration tests that need the real Rust parser + unparser end-to-end: idempotency (`format(format(x)) == format(x)` over a `.fltkg` corpus incl. `fegen.fltkg`), golden/canonical (formatting `fltk/fegen/fegen.fltkg` at width 80 / indent 2 is stable), trailing-newline robustness, and the parse-error path (malformed input ⇒ non-zero exit + a message naming the synthetic filename with line/col). These also exercise the `fltk_formatter_main!` macro's two error branches (`fully_consumed`-false partial parse → `Err(error_message())`; `unparse` → `None` → internal-error string), which cannot be unit-tested in `fltk-fmt-cli` (the macro requires a real consumer with concrete `Parser`/`Unparser`). Deferred to the planned §2.3 increment that also wires `crates/fltkfmt/` into `make check`; this test increment is a hard prerequisite before the binary is check-gated. Location: `crates/fltkfmt/tests/` (new), `crates/fltkfmt/src/main.rs`.

## `protocol-module-truthiness-gate`

`CstGenerator.gen_protocol_module` gates the per-rule `kind: typing.Literal[NodeKind.*]` discriminant on `self.py_module.import_path` truthiness, dual-using `py_module` as both the concrete-CST module path (annotation emission) and a truthiness sentinel for the protocol's `kind` discriminant. A `Builtins`-backed `CstGenerator` (empty `import_path`) silently emits the degraded `kind: object` form; `RustCstGenerator.generate_protocol` works around this by constructing a throwaway generator with a non-empty placeholder `py_module`. Replace the truthiness gate with an explicit parameter (e.g. `emit_kind_literal: bool`) so callers opt in deliberately and the trap is no longer rediscovered per caller. Location: `fltk/fegen/gsm2tree.py` (`_protocol_class_for_model_with_assignments`, the `if rule_name and self.py_module.import_path:` gate), `fltk/fegen/gsm2tree_rs.py` (`generate_protocol` placeholder workaround).

## `bazel-neg-test-harness`

The `generate_rust_parser` macro's misconfiguration `fail()` guards (the six pure-Rust-mode python-extension-only knobs, plus the `protocol` → `protocol_module` coupling) have no reproducible automated test. They were verified once by hand against a throwaway package (see `docs/workflow-bazel-protocol/implementation-log.md` "Misconfiguration coverage"), which the design's Test plan explicitly accepted ("If no harness exists, these are documented as manual `bazel build` expectations rather than automated tests"). Intentionally-failing targets cannot be committed to `BUILD.bazel` as-is — they would break `bazel build //...`. When a `bazel_skylib` `analysistest` harness is added to `MODULE.bazel`, wire one negative target per guard that asserts analysis failure with the expected message, so a future edit that disables a guard is caught. Location: `BUILD.bazel` (near the `bootstrap_native` smoke target).
