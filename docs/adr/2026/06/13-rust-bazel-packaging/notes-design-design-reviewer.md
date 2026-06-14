# Design review notes: Clockwork consumes FLTK + Rust under Bazel

Base commit: fafa6d7c12f9bd053f9f32f4cfb1a29e8136fe0e
Reviewer posture: adversarial fact-check against fltk + clockwork source.

Most claims in the design are well-grounded; the invariants section (§1), the
packaging decision (§2.1), and the ABI-gate citations all check out against
`cross_cdylib.rs`, the crate Cargo.tomls, and `genparser.py`. Findings below are
the gaps where the design's concrete mechanics either contradict source or are
under-specified enough to mislead implementation.

---

## design-1 — `mod cst;` / `mod parser;` in consumer lib.rs is not compatible with files emitted to a Bazel action-output dir

Section: §2.3, the `clockwork_native_lib.rs` snippet:
```rust
mod cst;      // = generated cst.rs
mod parser;   // = generated parser.rs
```
and §2.3 macro plumbing where `cst_rs` / `parser_rs` are separate label inputs
(`cst_rs = ":clockwork_rs_srcs"`, `parser_rs = ":clockwork_rs_srcs"`).

What's wrong: A Rust `mod cst;` (no inline body, no `#[path]`) makes rustc look
for the module source at a compiler-determined relative path next to the parent
file (`cst.rs` or `cst/mod.rs` in the same directory as `lib.rs`). Under Bazel,
`generate_rust_parser` declares `cst.rs`/`parser.rs` as **action outputs**,
which land in a `bazel-out/.../bin/...` tree, while the consumer-authored
`clockwork_native_lib.rs` is a source file in `clockwork/dsl/`. These are not
the same directory, so `mod cst;` will not resolve without either (a) the macro
co-locating all three `.rs` files into one synthesized crate-source directory,
or (b) emitting `#[path = "..."]` attributes. The existing in-tree fixture sees
no such problem only because its `cst.rs`/`parser.rs` are **checked-in files
physically next to `lib.rs`** (`tests/rust_parser_fixture/src/{lib.rs,cst.rs,
parser.rs}` — verified by `ls`), which is exactly the situation that does NOT
hold for Bazel-generated outputs.

Why / source: `rules_rust`'s `rust_shared_library` takes `srcs` and a `crate_root`;
it does not magically flatten multiple `declare_file` outputs from different
packages into one module-resolution directory. The design's snippet treats the
generated files as if they sit beside `lib.rs`.

Consequence: The single most load-bearing build step — compiling the generated
`cst.rs` + `parser.rs` + consumer `lib.rs` into one cdylib (AC #2) — will fail
to compile as drawn. The implementer will hit "file not found for module `cst`"
and have to invent the file-layout/`#[path]` mechanism the design omitted. Since
this mechanism is the core of the new public `fltk_pyo3_cdylib` macro surface,
leaving it unspecified means the central deliverable is undesigned.

Suggested fix: Specify how the macro assembles the crate source tree — e.g. the
macro symlinks/copies `cst.rs`/`parser.rs` and `lib.rs` into a single generated
directory used as the crate root dir, or the generated files are emitted with a
known basename and the consumer `lib.rs` uses `#[path]`. State which.

---

## design-2 — `generate_rust_parser` rule conflates two distinct CLI subcommands with different signatures; `--output-dir` does not exist for the Rust commands

Section: §2.3 (`generate_rust_parser(... cst_mod_path = "super::cst")` "emits
clockwork_rs_srcs/cst.rs, clockwork_rs_srcs/parser.rs") and §3.4 ("runs
`@fltk//:genparser` with `gen-rust-cst` then `gen-rust-parser`... `cst_mod_path`
attr forwards to `--cst-mod-path`").

What's wrong: The design models `generate_rust_parser` on the existing
`generate_parser` rule (`rules.bzl:1-71`), which calls one `generate`
subcommand with `--output-dir` and lets it emit all files. But the Rust path is
two separate subcommands, each taking a **positional `output_file`**, not a
shared `--output-dir`:
- `gen-rust-cst grammar_file output_file [--protocol-module ...] [--pyi-output ...]`
  (`genparser.py:265-297`) — has **no** `--cst-mod-path`.
- `gen-rust-parser grammar_file output_file [--cst-mod-path ...]`
  (`genparser.py:368-379`) — `--cst-mod-path` lives **only here**.

So the rule must run two actions with two explicit output-file paths, and
`cst_mod_path` forwards only to the second. This is doable but materially
different from the `generate_parser` analogy the design leans on, and §2.3's
single-rule sketch hides it. Also note `gen-rust-cst`'s default emits **no**
`.pyi` (requires `--protocol-module`); the design never says whether the Bazel
rule passes `--protocol-module`, which matters if pyright type-checking of the
cdylib surface is wanted (out of scope per requirements, so omission is
defensible — but should be stated).

Consequence: An implementer following §3.4 literally ("reuses the existing CLI
as-is", `--cst-mod-path` on the rule) will mis-wire the actions — e.g. try a
nonexistent `--output-dir` or attach `--cst-mod-path` to `gen-rust-cst`. Low
risk of shipping wrong, high risk of churn. The "reuse CLI as-is" claim in
requirements/Implementation-notes is satisfiable, but only with two positional
output args, which the design should call out.

Suggested fix: In §3.4, specify two actions with explicit per-file output args
and note `--cst-mod-path` applies only to `gen-rust-parser`.

---

## design-3 — Crate version stated as 0.2.0 for fltk-cst-core/parser-core is correct, but §1 implies fltk-native shares it; fltk-native is 0.1.0

Section: §1 line 53 — "The crates `fltk-cst-core` (v0.2.0) and `fltk-parser-core`
(v0.2.0) are `license = "MIT"`, not published to crates.io; `fltk-native` is
`publish = false`."

What's wrong: This is actually accurate as written (core crates 0.2.0;
`fltk-native` publish=false) — verified `crates/fltk-cst-core/Cargo.toml:3`,
`crates/fltk-parser-core/Cargo.toml:3`, root `Cargo.toml:6-11` (`fltk-native`
version 0.1.0, publish=false). No correction needed to the stated facts. Noting
only that the ABI marker is keyed on `fltk-cst-core`'s `CARGO_PKG_VERSION`
(0.2.0), independent of `fltk-native`'s 0.1.0 — the design's invariant #2 is
correct because both cdylibs link the *same* `fltk-cst-core` rlib regardless of
the `fltk-native` package version. Downgrade: this is a confirmation, not a
defect. Recorded so the judge knows the version claims were checked and hold.

(No consequence — fact-check pass.)

---

## design-4 — "rust_shared_library produces fltk/_native.abi3.so" — abi3 filename / module-name binding is asserted but not mechanized

Section: §2.2 item 2 and §3.3 — `@fltk//:native` "a `rust_shared_library` (or
`py_cc`/pyo3 extension target) producing `fltk/_native.abi3.so`" and a
`py_library` that "re-homes the produced `.so` to `fltk/_native.abi3.so` on the
import path."

What's wrong: A bare `rust_shared_library` produces a platform-default
`lib<name>.so`, not `_native.abi3.so`. Getting the exact `_native.abi3.so`
basename (which is what `py.import("fltk._native")` requires — `cross_cdylib.rs:
353` imports literally `fltk._native`) requires either a rename step or the
pyo3-specific extension rule that knows the abi3 suffix convention. maturin does
this today via `module-name = "fltk._native"` (`pyproject.toml:29`,
exploration-fltk §PyO3/maturin); `rules_rust` has no maturin. The design
acknowledges a "re-home" `py_library` but does not say what performs the rename
or how the `.abi3` infix and `_native` (leading-underscore, not `lib`-prefixed)
basename are produced. This is the same class of gap as design-1: the load-bearing
glue is named but not designed.

Why / source: invariant #1 (§1) and requirements Constraints both hinge on the
import path being exactly `fltk._native`; exploration-fltk "Open Factual
Questions §3" explicitly flags that the exact `.so` filename is a
maturin-naming-convention artifact, "not verified in source code." The design
inherits that open question without closing it.

Consequence: If the `.so` lands as `libnative.so` or `_native.so` (no abi3
infix) on the wrong import path, `import fltk._native` fails or the cross-cdylib
`get_span_type` raises `RuntimeError: cross-cdylib Span type lookup failed`
(AC #3 fails). The rename/relocation step is essential to AC #3 and is currently
hand-waved ("re-homes").

Suggested fix: Specify the mechanism — e.g. a genrule/`copy_file` renaming the
`rust_shared_library` output to `fltk/_native.abi3.so`, or use a pyo3-aware
`rules_rust` extension target if one is adopted. Confirm the abi3 suffix is
acceptable on the target CPython (abi3-py310 → `_native.abi3.so` is the maturin
convention and importable, but state it).

---

## design-5 — Third-party crate sourcing left split between two mechanisms within one document

Section: §3.1 ("third-party deps ... obtained via a `crate_universe`
(`crates_repository`) lockfile owned by FLTK ... **or** pinned in the root
module's `crate` extension — see §3.2") vs §3.2 ("declared through the
`rules_rust` `crate` extension with a checked-in `Cargo.lock` that FLTK owns").

What's wrong: §3.1 leaves the third-party-dep mechanism as an unresolved
either/or, while §3.2 states it as decided (FLTK owns a `crate` extension +
`Cargo.lock`). Internal inconsistency: one section defers, the next commits.
Additionally, a real feasibility wrinkle the design doesn't address: FLTK's root
`Cargo.toml` is a **workspace** (`Cargo.toml:1-2`, members include
`crates/fltk-cst-core`, `fltk-parser-core`, plus `fltk-cst-spike`), and the
three test crates declare their own `[workspace]` and are excluded
(exploration-fltk §Cargo, constraint "Separate Cargo workspace topologies").
`rules_rust`'s `crate` extension / `crates_repository` keys off a `Cargo.toml` +
`Cargo.lock`; which manifest FLTK points it at (root workspace vs. per-crate)
determines what third-party graph is locked. §3.1 asserts the workspace
topology is "irrelevant" because Bazel builds per-crate — true for the
*first-party* rlibs, but the **third-party** lockfile still has to be generated
from *some* manifest, and the spike crate / test crates are in or out of that
set.

Consequence: Implementer cannot tell from the doc whether to stand up a
`crates_repository` or inline pins, nor which manifest seeds the lockfile. Risk
of a lockfile that omits or double-counts crates, or a second round of design.
This is the kind of infra-before-features gap (requirements: "infrastructure
before features") that should be nailed before the macro work.

Suggested fix: Pick one mechanism and state the seed manifest (e.g.
"`crates_repository` seeded from root `Cargo.toml`/`Cargo.lock`, covering
fltk-cst-core + fltk-parser-core + fltk-native + transitive pyo3/regex-automata;
fltk-cst-spike and tests/* excluded"). Reconcile §3.1 and §3.2.

---

## design-6 — `bazel_dep(rules_rust)` in a non-root module: design's precedence claim is plausible but the toolchain-visibility mechanics are asserted without a cited source

Section: §2.2 — "a non-root module (FLTK) can `bazel_dep(name = "rules_rust")`
and that dependency is visible to the build, but toolchains registered by a
non-root module sit at lower precedence ... the *root* module (Clockwork) drives
`rust.toolchain(...)`."

What's wrong: This is a reasonable Bzlmod design and the conclusion (root
registers toolchains) is almost certainly right, but the design states the
precedence rule as fact without grounding it in any doc/source in-repo, and it's
the kind of Bzlmod nuance LLMs get subtly wrong. More concretely actionable: the
design has **both** FLTK and Clockwork declare `bazel_dep(name = "rules_rust",
version = "<pinned>")` (§3.2). Under Bzlmod single-version resolution that is
fine only if the versions are compatible; the design defers the version to
"<pinned>" / "resolved at impl" in both places without noting they must agree.
Also unverified: that `rules_rust`'s `crate` extension repos exported from FLTK
via `use_repo` are actually visible to Clockwork's `fltk_pyo3_cdylib`
invocations — extension-created repos are module-private by default and are not
automatically visible to other modules. The macro in `@fltk//:rust.bzl`
references `@fltk//crates/...` (fine, those are FLTK's own targets) and injects
pyo3 deps — if those pyo3 deps come from FLTK's `crate` hub, the macro can
reference them as FLTK-internal labels (fine), but if Clockwork must supply pyo3
for its own `lib.rs` crate, O1 (§6) is where that bites and it's left open.

Consequence: Mostly a groundedness flag, not a hard contradiction. Risk: an
implementer takes the precedence claim at face value and is surprised by
Bzlmod's actual toolchain-resolution / repo-visibility behavior, or by a
`rules_rust` version conflict between the two `bazel_dep`s. Low-to-moderate;
worth a citation or a spike note.

Suggested fix: Cite the Bzlmod toolchain-precedence behavior (rules_rust docs)
or mark it as an assumption to validate in a spike. State that both
`bazel_dep(rules_rust)` versions must match. Confirm whether the pyo3 repo the
macro injects is FLTK-internal (no consumer `use_repo` needed) or must be
re-exported.

---

## design-7 — Roundtrip test grounding: top-level rule name not pinned, but this is acceptable scope

Section: §2.3 / §5 item 3 — the test "parses one representative
`clockwork.fltkg` source string."

Note: `clockwork.fltkg`'s top rule is `module` (exploration-clockwork §2 line
38). The generated parser exposes `apply__parse_module` (the established
`apply__parse_<rule>` convention). The design says "through
`clockwork_native.parser`" without naming the entry method — acceptable at design
altitude since AC #4 only requires *a* parse result, but the implementer will
need to use the `module` rule's apply method, and a "representative source
string" for the full Clockwork DSL (413-line grammar, `module := (doc...)? ...`)
is non-trivial to hand-author minimally. Not a defect; flagging that "one
representative source string" may need care to be a valid `module`.

Consequence: None blocking. Minor implementation-time effort risk if the chosen
string doesn't satisfy the `module` rule. No fix required.

---

## Coverage check (requirements ACs → design)

- AC #1 (codegen under Bazel): §2.3 `generate_rust_parser`, §3.4 — covered, but
  see design-2 (CLI mechanics).
- AC #2 (cdylib builds, same fltk-cst-core): §2.1 + §2.3 + §3.1 — covered, but
  see design-1 (mod resolution) — the compile step is the weak point.
- AC #3 (both modules import, native Span path live): §2.3 + §4 — covered, but
  see design-4 (.so filename/path mechanism is the lynchpin and is hand-waved).
- AC #4 (roundtrip parse, some result): §2.3 + §5.3 — covered; see design-7.
- AC #5 (pure-Python path intact): §2.2 item 2, §3.3, §5.5 — covered cleanly
  (existing `py_library(name="fltk")` untouched; native is additive `data` dep).
  This is the best-specified part.
- ADR recording the packaging decision: §2.1/§2.2 are explicit, called-out
  decisions — satisfies requirements "In scope" ADR requirement.

Scope discipline: design stays additive, rejects wheel/crates.io with reasons,
no speculative features. O1/O2 correctly deferred to user. Good.
