# Design review notes — codegen-rust-lib-boilerplate

Adversarial fact-check of design.md against requirements.md, exploration.md, and source
(fltk @ 7200d9c, clockwork worktree). Most load-bearing claims verified accurate: the
clockwork/`fltk._native` lib.rs contents, `register_submodule` usage, `_CST_MOD_PATH_RE`
reuse (genparser.py:365), the Bazel assembly genrule + recursion_limit injection
(rust.bzl:220-239), the three fixtures' non-standard shapes, the `src/span.rs` hand-written
re-export, and the orphaned `native-submodule-error-context` TODO all check out.

Findings below.

---

## design-1 — "clean after `make fix`" / formatting gate is wrong for a `.rs` file

Section: §2.1 (Generated-code formatting reference), §4 Test plan ("`make check` passes on
the committed generated `src/lib.rs` (formatting clean after `make fix`)"), and the
requirements Constraint it inherits.

What's wrong: The design (and the requirement it cites) asserts the generated `lib.rs` must
be "clean after `make fix`" and that `make check` gates its formatting. This is false for a
Rust file. `make fix` runs only ruff (`uv run --group lint ruff check --fix . ; ruff format .`
— Makefile:85-87), which is Python-only. There is no rustfmt/`cargo fmt` step anywhere in
`make fix`, `check-common` (Makefile:39-51), `check`, or `.github/` (grep for
`rustfmt|cargo fmt|fmt --check` returns nothing). The existing generated `.rs` files
(`src/cst_fegen.rs`, `src/cst_generated.rs`) are likewise never run through a Rust formatter.

Why: Makefile:39-51 enumerates the `check-common` steps — `lint format-check typecheck test
cargo-check cargo-clippy cargo-test cargo-test-python-features cargo-test-no-python
cargo-clippy-no-python check-no-pyo3`. None of these is a Rust *formatting* gate; the Rust
gates are clippy/check/test (semantic/compile), not rustfmt. The "regen → make fix → commit"
flow in CLAUDE.md is described for the Python generators; it does not apply to `.rs` output.

Consequence: The implementer may waste effort trying to make `RustLibGenerator` output
"rustfmt-clean" or assume `make fix` will normalize it, and may write a test asserting
formatting cleanliness that has no corresponding gate. More importantly, the real
"done" gate for the generated `lib.rs` is *compilation* (fixture crates via cargo-clippy /
the maturin `build-native` for `src/lib.rs`), not formatting. The acceptance language should
be corrected so the implementer targets the right gate; otherwise the spec's notion of
"clean committed output" is unverifiable as written.

Suggested fix: Replace "clean after `make fix`" with "compiles under the existing Rust gates
(`build-native` for `src/lib.rs`; `cargo check`/`cargo clippy` for any migrated fixture
crate)" and drop the implication that `make fix` formats the `.rs`. If rustfmt-cleanliness of
generated `.rs` is genuinely desired, that is a new, separate gate not in scope here.

---

## design-2 — `make check` does NOT run `gencode` or a drift check; cheat-detection is manual

Section: §4 Test plan, fltk integration bullet: "A `git diff` after `make gencode` shows no
drift (cheat-detection per Makefile:233-234)" presented alongside "`make check` passes."

What's wrong: The design frames drift detection as part of the verification gate. But
`make check` / `check-common` never invokes `gencode` (Makefile:39-51 — `gencode` is not in
the steps list, and `check`/`check-ci` only add cargo-deny). The `git diff --stat` drift
check is a *manual* developer step the Makefile comment (Makefile:233-234) merely documents;
nothing automated runs it. So committing a hand-patched `src/lib.rs` that diverges from
generator output would NOT be caught by `make check`.

Why: Makefile:39-51 (`check-common` step list) and Makefile:61-76 (`check`/`check-ci`)
contain no `gencode` or `git diff` invocation. Makefile:233-234 is a comment on the
`gencode` target describing how a developer *can* spot drift.

Consequence: The implementer/reviewer may believe `make check` enforces that committed
`src/lib.rs` matches generator output (it does not), creating a false sense that drift is
impossible. The acceptance criterion "the committed `src/lib.rs` becomes generated output,
gated by `make check` like the other generated files" (§2.7) overstates the guarantee — the
other generated `.rs` files have the same manual-only drift posture. Not fatal, but the test
plan should state drift detection is a manual `make gencode` + `git diff` step, not part of
`make check`.

Suggested fix: Reword §2.7 / §4 to say drift is caught by the manual `make gencode` +
`git diff` workflow (matching how `cst_generated.rs`/`cst_fegen.rs` are already handled), and
that `make check` only gates compilation, not regeneration.

---

## design-3 — fltk-side Bazel acceptance criterion has no in-repo test; relies on out-of-repo clockwork

Section: §4 Test plan "Bazel macro" bullet, and requirements acceptance criterion
"A consumer Bazel target can build `fltk_pyo3_cdylib` without supplying a hand-written
`lib_rs`."

What's wrong: The design correctly notes (§5.4 reference, §4) that there is no in-tree
`fltk_pyo3_cdylib` invocation in fltk — confirmed: the only `fltk_pyo3_cdylib` use is
clockwork's (out of this repo), and BUILD.bazel:117-122 carries `TODO(fltk-pyo3-cdylib-smoke)`
noting the macro is "only tested transitively via Clockwork's build." The design leaves wiring
the smoke target *optional* ("If the in-tree TODO smoke target is wired, point it at the
no-`lib_rs` path"). So the new no-`lib_rs` Bazel codepath (the most mechanically novel part of
the Bazel change) would ship with zero automated coverage inside the fltk repo.

Why: rust.bzl `fltk_pyo3_cdylib` is a macro; the new conditional-generation path (§2.5
step 1) only executes when `lib_rs` is omitted. The sole exerciser of `lib_rs`-omitted is
clockwork (separate repo, separate CI). BUILD.bazel:111-122 confirms only `generate_rust_parser`
runs in fltk CI.

Consequence: A regression in the macro's lib.rs-generation branch (e.g. wrong genrule wiring,
missing dependency on the genparser tool, basename collision with the assembled `lib.rs`)
would not be caught by any fltk test — only by clockwork's build breaking later. Given the
requirement explicitly lists this as an fltk-side acceptance criterion, the design should
make wiring the smoke target (with the no-`lib_rs` path) part of scope, not optional, OR
explicitly accept that the fltk-side criterion is verified only out-of-repo and call that out
as a risk.

Suggested fix: Promote "wire `TODO(fltk-pyo3-cdylib-smoke)` to exercise the no-`lib_rs` path"
from optional to in-scope, so the new Bazel branch has in-repo coverage.

---

## design-4 — CST-only Bazel path: `--no-parser` lib.rs vs. always-emitted parser.rs is unresolved

Section: §2.5 step 3 ("`--no-parser` is wired through if a `with_parser`/`cst_only` macro
attribute is added").

What's wrong: In Bazel, `cst.rs` and `parser.rs` are produced by `generate_rust_parser`,
which *always* emits BOTH outputs unconditionally (rust.bzl:39-40, 48-70 — two fixed
`ctx.actions.declare_file` + two `ctx.actions.run`). The assembly genrule then requires both
`cst.rs` AND `parser.rs` to be present (rust.bzl:231-232: `test -f $$OUTDIR/parser.rs ||
... exit 1`). So a CST-only `lib.rs` (no `mod parser;`) assembled in Bazel would still have a
`parser.rs` copied into the gendir (now an unreferenced module file — harmless) AND the
assembly's mandatory `parser.rs` presence check still passes. The design's `--no-parser`
macro attribute (§2.5 step 3) controls only the lib.rs shape, not `generate_rust_parser`'s
outputs, and the design never reconciles this coupling.

Why: rust.bzl:39-40 declares both outputs always; rust.bzl:231-232 asserts both always
present. There is no `cst_only` switch on `generate_rust_parser`.

Consequence: If a consumer sets the hypothetical `cst_only` macro attribute, the build would
still generate and demand a `parser.rs` (from a grammar that may produce a degenerate or
empty parser), and the CST-only `lib.rs` would leave that `parser.rs` as an unused sibling
module — at best wasteful, at worst a compile error if the emitted `parser.rs` references
`super::cst` symbols that interact poorly, or if `parser::register_classes` is expected.
Since CST-only Bazel support is not actually exercised by any migration target (all three
fixtures stay hand-written, §2.7; clockwork has a parser), this is speculative scope: the
`--no-parser`/`cst_only` Bazel wiring (§2.5 step 3) has no consumer in scope and adds an
unreconciled coupling.

Suggested fix: Drop the Bazel `cst_only`/`with_parser` macro attribute from this design (keep
`--no-parser` only as a CLI flag for the Makefile/maturin path, which is where the sole
CST-only candidate `tests/rust_cst_fixture` lives — though that one stays hand-written too).
If CST-only Bazel is wanted later, it must also gate `generate_rust_parser`'s parser output
and the assembly presence check — out of scope here.

---

## design-5 — relocated TODO still won't satisfy the two-part TODO convention

Section: §3 / §4 "TODO handling" — relocate `TODO(native-submodule-error-context)` comment to
`register_submodule` in `fltk_cst_core`.

What's wrong: The design proposes moving the inline comment but does not add the required
`TODO.md` entry. CLAUDE.md's TODO System mandates BOTH a `TODO.md` entry AND a `TODO(slug)`
comment; the slug join key requires both halves. Confirmed: `native-submodule-error-context`
has NO entry in fltk `TODO.md` (only `fltk-pyo3-cdylib-smoke`, `bazel-rules-rust`, etc.) and
none in clockwork — it exists only as the inline comment plus ADR dispositions
(`docs/adr/2026/06/13-rust-bazel-packaging/dispositions-final.md:24-25`). Relocating the
comment perpetuates a convention-violating orphan TODO.

Why: CLAUDE.md "TODO System": "Adding a TODO requires both an entry in TODO.md and a
TODO(slug) comment." grep confirms no `TODO.md` entry for the slug in either repo.

Consequence: After implementation the repo still has a TODO(slug) with no TODO.md anchor —
the exact non-conformance the convention forbids — now living in `fltk_cst_core` where it is
even less likely to be reconciled. Minor, but since the design explicitly touches this TODO
it should either (a) add the missing `TODO.md` entry when relocating, or (b) resolve/drop the
TODO per the check-todos rubric rather than relocate it.

Suggested fix: When relocating, also add a `native-submodule-error-context` entry to fltk
`TODO.md` (where `register_submodule` lives — crates/fltk-cst-core/src/py_module.rs:87), or
adjudicate it for removal.

---

## design-6 (minor) — Bazel "consumes generated lib.rs exactly as a consumer-authored one" understates the wiring change

Section: §2.5 step 2 ("The existing assembly genrule consumes that generated `lib.rs` exactly
as it consumes a consumer-authored one today").

What's wrong: The current macro takes `lib_rs` as a *mandatory* parameter (rust.bzl:123-131 —
no default) and feeds it directly as a genrule `srcs` label and `$(location {lib_rs})`
(rust.bzl:222, 227). Making it optional-with-generated-default is not "exactly as today": the
macro must (a) give `lib_rs` a default of `None`, (b) instantiate a new generation target
producing a file label when `None`, and (c) substitute that label into the assembly genrule.
The design's step 1 sketches this but step 2's "exactly as ... today" glosses that the
assembly genrule's `lib_rs` input now comes from a generated target, and that `gen-rust-lib`
(which per §2.3 takes NO grammar file) needs a Bazel rule/genrule wrapper distinct from
`generate_rust_parser` (which is grammar-driven). The design does not specify how
`gen-rust-lib` is invoked as a Bazel action (a new tiny rule? a genrule calling
`//:genparser`?).

Why: rust.bzl:123-131 (mandatory `lib_rs`), :220-239 (assembly genrule consuming `lib_rs` as
a file). §2.3 states `gen-rust-lib` takes no grammar, so the existing grammar-driven
`generate_rust_parser` rule cannot host it.

Consequence: Underspecified Bazel mechanism. An implementer must design the new lib.rs Bazel
generation action from scratch (tool dependency on `//:genparser`, output declaration,
module-name = target `name` plumbing). Low risk of getting *built wrong* (it's mechanical),
but the design should name the concrete mechanism (new `genrule` calling `//:genparser
gen-rust-lib $(OUTS) --module-name <name>`, gated on `lib_rs == None`) so the implementer
isn't inventing it.

Suggested fix: In §2.5, spell out the conditional: `if not lib_rs:` create a `genrule`
named `name + "_gen_lib"` that runs `$(location //:genparser) gen-rust-lib $@ --module-name
<name>`, and set `lib_rs = ":" + name + "_gen_lib"`; otherwise use the supplied `lib_rs`.
