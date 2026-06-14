# Dispositions: design review (round 1)

Design: [`design.md`](./design.md)
Reviewer notes: [`notes-design-design-reviewer.md`](./notes-design-design-reviewer.md)
Round: 1

Fact-check basis: confirmed CLI signatures in `fltk/fegen/genparser.py`
(`gen-rust-cst` lines 265–297, `gen-rust-parser` lines 368–379), the existing
`generate_parser` rule in `rules.bzl` (lines 1–71, uses `--output-dir`), and the
in-tree fixture layout (`tests/rust_parser_fixture/src/{lib.rs,cst.rs,parser.rs}`
physically co-located; `lib.rs` uses bare `pub mod cst;` / `pub mod parser;` with
no `#[path]`).

---

design-1:
- Disposition: Fixed
- Action: §2.3 — annotated the `lib.rs` snippet and added a paragraph explaining
  that bare `mod cst;`/`mod parser;` resolve only because the macro co-locates
  all three files; §2.2 item 3 (`fltk_pyo3_cdylib` bullet) now states the macro
  is responsible for crate-source assembly; §3.4 adds a "Crate-source assembly"
  sub-item specifying the `copy_file`/`crate_root` mechanism with fixed `cst.rs`/
  `parser.rs` basenames, and records the rejected `#[path]` alternative.
- Severity assessment: Verified against source — the fixture's three files are
  physically co-located in one `src/` dir and `lib.rs` uses bare `mod` with no
  `#[path]`, so the design's snippet would not compile on Bazel action outputs.
  This is the core compile step (AC #2); leaving it unspecified left the central
  deliverable undesigned.

design-2:
- Disposition: Fixed
- Action: §2.2 item 3 (`generate_rust_parser` bullet) and §3.4 rewritten to
  specify two separate actions with positional `output_file` args, note the Rust
  subcommands have no `--output-dir` (unlike the Python `generate`), and state
  `--cst-mod-path` applies only to `gen-rust-parser`. Added that the rule passes
  no `--protocol-module`/`--pyi-output` (no `.pyi`; out of scope per requirements).
- Severity assessment: Verified exactly against `genparser.py:265–297`/`368–379`
  and `rules.bzl:10`. An implementer following the original `--output-dir`/
  `--cst-mod-path`-on-the-rule sketch would mis-wire the actions. Low risk of
  shipping wrong, high churn risk — now eliminated.

design-3:
- Disposition: Won't-Do
- Action: None.
- Severity assessment: None — the reviewer self-classified this as a fact-check
  confirmation ("No correction needed... this is a confirmation, not a defect"),
  verifying the version claims in §1 (core crates 0.2.0; `fltk-native`
  publish=false) hold. No design change is warranted.
- Rationale (Won't-Do): The finding explicitly confirms the design is correct as
  written and requests no change; `crates/fltk-cst-core/Cargo.toml:3`,
  `crates/fltk-parser-core/Cargo.toml:3`, and the root `Cargo.toml` corroborate
  the stated versions. Editing the design in response would alter accurate text
  for no reason.

design-4:
- Disposition: Fixed
- Action: §3.4 adds a "`.so` basename binding" sub-item specifying that
  `rust_shared_library` emits `lib<name>.so` and the macro must `copy_file`-rename
  it to the abi3 basename (`fltk/_native.abi3.so` for `@fltk//:native`,
  `<pkg>/<name>.abi3.so` for a consumer cdylib) on the correct import path; §2.2
  item 2 and §3.3 now point at this mechanism instead of the vague "re-homes".
- Severity assessment: Verified — the exact `.so` basename is a maturin
  convention (`pyproject.toml:29`) with no maturin under `rules_rust`. If the
  `.so` lands as `libnative.so` or on the wrong path, `import fltk._native` fails
  and AC #3 fails. This rename is the lynchpin of AC #3 and was previously
  hand-waved.

design-5:
- Disposition: Fixed
- Action: §3.1 rewritten to commit to a single mechanism — a FLTK-owned
  `crates_repository`/`crate` extension seeded from the root `Cargo.toml`/
  `Cargo.lock`, covering `fltk-cst-core`/`fltk-parser-core`/`fltk-native` and
  their transitive graph, with `fltk-cst-spike` and `tests/*` excluded —
  removing the §3.1-vs-§3.2 either/or. §3.2 already named the same mechanism and
  now reads consistently; both name the seed manifest and the exclusion set.
- Severity assessment: Internal inconsistency (one section deferred, the next
  committed) plus an unaddressed seed-manifest question. Without resolution the
  implementer could not tell whether to stand up a `crates_repository` or inline
  pins, nor which manifest seeds the lockfile — risking a wrong lockfile or a
  second design round.

design-6:
- Disposition: Fixed
- Action: §2.2 reworded to mark the Bzlmod toolchain-precedence claim as an
  assumption to validate in the first implementation spike (not grounded in
  in-repo source) while keeping the robust conclusion (root drives
  `rust.toolchain`). §3.2 adds (a) a note that extension-created repos are
  module-private and the macro references pyo3 deps as FLTK-internal labels so
  Clockwork needs no `use_repo` for FLTK's `@crates` hub, and (b) a statement
  that both `bazel_dep(rules_rust)` versions must be compatible/identical.
- Severity assessment: Mostly a groundedness flag, not a hard contradiction. Risk
  was an implementer surprised by Bzlmod's actual toolchain/visibility behavior
  or a `rules_rust` version conflict between the two `bazel_dep`s. Now flagged as
  spike-validated and the version-match requirement is explicit.

design-7:
- Disposition: Fixed
- Action: §2.3 — added the concrete entry method (`apply__parse_module`, since
  `clockwork.fltkg`'s top rule is `module`) and a note that the representative
  source string must be a valid `module`, which takes care for the 413-line
  grammar.
- Severity assessment: Non-blocking; the reviewer said "No fix required". Applied
  a cheap, source-grounded clarification (the `apply__parse_<rule>` convention +
  top rule `module` from exploration-clockwork §2) to reduce implementation-time
  effort risk. No design decision changed.
