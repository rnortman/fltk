# Design review notes: Standalone Rust formatter binary (`fltkfmt`)

Base commit 6f975eb. Verified the load-bearing claims against source; the pipeline
(`Parser::new` → `apply__parse_grammar` → `result.read()` → `Unparser::new().unparse_grammar`
→ `resolve_spacing_specs(result.doc())` → `Renderer::render`), the crate deps
(`fegen-rust-cst { default-features = false }` is pyo3-free; native tests run with
`--no-default-features`), `UnparseResult::doc()` (result.rs:35), char-indexed positions
(native_tests.rs:1021 asserts `parsed.pos == src.chars().count()`), the `gen-rust-unparser`
CLI surface (genparser.py:470-580), and the fegen start rule `grammar` (fegen.fltkg:2) all
check out. Three findings.

---

## design-1: Parse-error message will NOT contain the filename

**Section:** §3 "Parse failure" and §4 test plan ("Parse-error path").

**Quotes:**
- §3: "`parser.error_message()`, which routes through the shared
  `fltk_parser_core::format_error_message` ... `Parser::new(src, filename, true)` is given
  the filename so it appears in the message."
- §4: "Parse-error path: malformed input yields a non-zero result and a message mentioning
  the (synthetic) filename and a line/col."

**What's wrong:** The cited mechanism does not exist. `Parser::error_message()`
(crates/fegen-rust/src/parser.rs:94-98) calls
`fltk_parser_core::format_error_message(&self.error_tracker, &self.terminals, &RULE_NAMES)`.
That function (crates/fltk-parser-core/src/errors.rs:123-158) produces only
`"Syntax error at line {line+1} col {col+1}:\n{line_text}\n{caret}\nExpected:\n..."` — it
never reads the filename. The filename passed to `Parser::new` lands in
`SourceText.filename` (span.rs:50,79-83) and is only ever surfaced through the span accessor
`Span::filename_inner()` / `py_filename()` (span.rs:566,843), never through the error
formatter. Confirmed by grep: no error/line/col formatting path in
`crates/fltk-parser-core/` or `crates/fltk-cst-core/` consumes `filename`.

**Consequence:** The §4 parse-error test ("a message mentioning the ... filename") will fail
against the proposed pipeline, because `parser.error_message()` emits no filename. To make
the filename appear, `run_main` (or the macro closure) must explicitly prepend it to the
error string — work the design does not describe and attributes instead to a non-existent
`Parser::new` behavior. Either add that prepend step to the design, or drop the
filename-mention assertion from the test.

---

## design-2: The `make check` aggregation does not work the way §2.3 describes; new crates won't be gated as written

**Section:** §2.3 Makefile bullet.

**Quote:** "wire them into the CI/`check` aggregation that already runs
`test-native-parser` / `test-rust-parser-fixture`."

**What's wrong:** The `check` aggregation does *not* run `test-native-parser` or
`test-rust-parser-fixture`. `check` → `check-ci` → `check-common`, and `check-common`'s step
list (Makefile:40,51) is exactly:
`lint format-check typecheck test cargo-check cargo-clippy cargo-test
cargo-test-python-features cargo-test-no-python cargo-clippy-no-python check-no-pyo3`.
The standalone Rust crates are exercised *inside* those steps by explicit
`--manifest-path` lines, not via the `test-native-parser` (Makefile:235) /
`test-rust-parser-fixture` (Makefile:238) targets (which exist but are not invoked by any
check target). Specifically a standalone crate is listed in:
- `cargo-test-no-python` (Makefile:135-140) — `cargo test --manifest-path .../Cargo.toml`,
- `cargo-clippy-no-python` (Makefile:142-147) — `cargo clippy ... -D warnings`,
- `check-no-pyo3` (Makefile:153-170) — the pyo3-absence proof for the pure-Rust claim,
- `cargo-deny` (Makefile:176-181) — each standalone crate's own Cargo.lock is checked with
  its own `--manifest-path` line.

Because `crates/fltkfmt/` is a standalone crate with its own `[workspace]`/Cargo.lock
(§2.3), `cargo test`/`clippy`/`deny` at the root will NOT see it. To actually gate it the
implementer must add explicit `--manifest-path crates/fltkfmt/Cargo.toml` lines to all four
targets above (and, to back the "zero pyo3" claim, to `check-no-pyo3`). The Makefile also
carries a MANDATORY anti-drift rule (Makefile:27-32): new check steps go in `check-common`
only — adding bespoke `build-fltkfmt`/`test-fltkfmt` steps elsewhere is forbidden.

`fltk-fmt-cli` is different: §2.2 puts it in the *root* workspace, so root `cargo-test` /
`cargo-clippy` / `cargo-check` / root `cargo-deny` already cover it automatically. That makes
the proposed separate `test-fltk-fmt-cli` (`cd crates/fltk-fmt-cli && cargo test`) target
redundant with the existing `cargo-test` step — and adds clap's transitive tree to the root
`cargo deny --manifest-path Cargo.toml` check (clap is MIT/Apache-2.0, within deny.toml's
allow-list, so it should pass, but the design never states this was checked).

**Consequence:** Following §2.3 literally produces a binary that compiles locally but is not
covered by `make check` / CI: `fltkfmt`'s tests, clippy `-D warnings`, pyo3-absence proof,
and supply-chain (cargo-deny) gate would all silently skip it, and the "first consumer proves
the scaffolding" goal would have no gate enforcing it stays green. The added `build-fltkfmt`/
`test-fltkfmt`/`test-fltk-fmt-cli` targets wired "into CI" would not run in CI at all
(they're not in `check-common`), and `test-fltk-fmt-cli` duplicates work `cargo-test` already
does. Fix: enumerate the exact `--manifest-path` additions to `cargo-test-no-python`,
`cargo-clippy-no-python`, `check-no-pyo3`, and `cargo-deny` for `crates/fltkfmt/`, and drop
the redundant `test-fltk-fmt-cli` target.

---

## design-3: `pub mod cst` rationale contradicts the macro design (§2.3); change may be unnecessary

**Section:** §2.1 ("change `mod cst;` → `pub mod cst;`") vs §2.3 ("the macro names neither").

**What's wrong:** §2.1 justifies making `cst` public with "the binary and unparser must name
CST types across the crate boundary." But (a) the generated `unparser.rs` references the CST
via `use super::cst;` *within* the same crate, where a private `mod cst` is already visible to
sibling modules — the existing crate compiles today with `mod cst;` private and `pub mod
parser;` exposing signatures like `apply__parse_grammar -> Option<ApplyResult<Shared<cst::
Grammar>>>` (parser.rs); and (b) §2.3 states the macro "names neither" the parser-core nor
cst-core types and binds method *identifiers* only, so the binary uses every CST-typed value
through type inference (`let parsed = parser.apply__parse_grammar(0); ... &*guard`) and never
writes a `fegen_rust_cst::cst::...` path. Inference-only use of an unnameable type from a
downstream crate compiles; naming is not required. So the stated reason for `pub mod cst` is
not supported by the design's own approach.

**Consequence:** Either the macro actually does need to name a CST type (in which case §2.3's
"names neither" is wrong and the binary's explicit-dep list in §2.3 is incomplete), or it does
not (in which case `pub mod cst` widens `fegen-rust-cst`'s public Rust surface for a reason
that does not hold). Low blast radius — making `cst` public is harmless and arguably tidy —
but the contradiction means the visibility reasoning was not pinned down; the implementer
should confirm by compiling the macro expansion against `mod cst;` private before widening the
surface, and correct whichever statement is wrong.
