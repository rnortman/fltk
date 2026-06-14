# Judge verdict — design review

Phase: design. Doc: `design.md` (Clockwork consumes FLTK + Rust under Bazel). Round 1.
Notes: 1 reviewer file (design-reviewer); 7 findings. No TODOs (design phase).

Fact-check basis (verified against source this round):
- `fltk/fegen/genparser.py:265–297` — `gen-rust-cst` has positional `grammar_file` + `output_file`, options `--protocol-module`/`--pyi-output` only, **no `--cst-mod-path`**. Confirmed.
- `fltk/fegen/genparser.py:368–379` — `gen-rust-parser` has positional `grammar_file` + `output_file`, `--cst-mod-path` (default `super::cst`) only. Confirmed.
- `rules.bzl` `_genparser_impl` — uses `--output-dir cst_file.dirname`, single action. Confirmed (the Rust path genuinely differs).
- `tests/rust_parser_fixture/src/lib.rs` — bare `pub mod cst;`/`pub mod parser;` (no `#[path]`); `cst.rs`/`parser.rs` physically co-located in `src/`. Confirmed.
- `crates/fltk-cst-core/Cargo.toml:3` = 0.2.0; `crates/fltk-parser-core/Cargo.toml:3` = 0.2.0; root `Cargo.toml` = fltk-native 0.1.0, `publish = false`, workspace members include `fltk-cst-spike`. Confirmed.
- `crates/fltk-cst-core/src/cross_cdylib.rs:353` imports literal `fltk._native`, `:358` raises `cross-cdylib Span type lookup failed (fltk._native.Span)`. Confirmed.
- `pyproject.toml:29` — `module-name = "fltk._native"` (maturin convention). Confirmed.

## Other findings walk

### design-1 — Fixed
Claim: §2.3 `mod cst;`/`mod parser;` snippet won't resolve on Bazel action outputs (generated `.rs` land in `bazel-out/.../bin`, `lib.rs` is a consumer source file). Consequence: the core compile step (AC #2) fails "file not found for module `cst`"; the central deliverable left undesigned.
Source: fixture's bare `mod` works only because its three files are physically co-located in one `src/`. Verified — `lib.rs` uses `pub mod cst;` with no `#[path]`; files co-located. Real, load-bearing gap.
Disposition action: §2.3 lines 211–233 annotate the snippet and add the "single synthesized crate directory" paragraph; §2.2 item 3 (line 169) states the macro owns crate-source assembly; §3.4 lines 379–391 add "Crate-source assembly" specifying the `copy_file`/`crate_root` mechanism with fixed `cst.rs`/`parser.rs` basenames and records the rejected `#[path]` alternative (paths unstable across configs).
Assessment: fix addresses the consequence at the named sections; the mechanism is now specified, not hand-waved. Accept.

### design-2 — Fixed
Claim: §2.3/§3.4 model `generate_rust_parser` on `generate_parser`'s single `--output-dir` action, but the Rust subcommands are two commands with positional `output_file` and no `--output-dir`; `--cst-mod-path` lives only on `gen-rust-parser`. Consequence: implementer mis-wires actions (nonexistent `--output-dir`, or `--cst-mod-path` on `gen-rust-cst`) — high churn.
Source: genparser.py:265–297 / 368–379 and rules.bzl confirm the signatures exactly. Real.
Disposition action: §2.2 item 3 (lines 154–162) and §3.4 (lines 356–373) rewritten to two actions with positional `output_file`, explicit "no `--output-dir` (unlike Python `generate`)", `--cst-mod-path` "here only" on `gen-rust-parser`, and "passes neither protocol option (no `.pyi`; out of scope)".
Assessment: matches source exactly; the mis-wire risk is eliminated. Accept.

### design-3 — Won't-Do
Claim: §1 line 53 stated as if `fltk-native` shares 0.2.0. Reviewer's own text: "This is actually accurate as written," "No correction needed," "this is a confirmation, not a defect," "(No consequence — fact-check pass.)"
Source: versions verified (core 0.2.0; fltk-native 0.1.0 publish=false). The design's invariant #2 keys on `fltk-cst-core`'s `CARGO_PKG_VERSION`, independent of fltk-native — design is correct.
Assessment: finding states no consequence and explicitly requests no change. Per the no-consequence rule, responder wins by default; editing accurate text would be harmful. Won't-Do sound.

### design-4 — Fixed
Claim: §2.2/§3.3 assert `rust_shared_library` produces `fltk/_native.abi3.so` but a bare `rust_shared_library` emits `lib<name>.so`; the abi3/`_native` basename is a maturin artifact with no maturin under `rules_rust`. Consequence: `.so` lands as `libnative.so` / wrong path → `import fltk._native` fails or `cross-cdylib Span type lookup failed` (AC #3 fails). "Re-homes" was hand-waved.
Source: cross_cdylib.rs:353 imports literal `fltk._native`; pyproject.toml:29 `module-name = "fltk._native"`. Real lynchpin.
Disposition action: §3.4 lines 392–403 add ".so basename binding" — `rust_shared_library` emits `lib<name>.so`, macro `copy_file`-renames to `fltk/_native.abi3.so` (FLTK) / `<pkg>/<name>.abi3.so` (consumer); §2.2 item 2 (143–150) and §3.3 (347–351) now point at this mechanism.
Assessment: the rename step is now concrete and on the right import path; addresses AC #3. Accept.

### design-5 — Fixed
Claim: §3.1 leaves third-party sourcing as an either/or (`crates_repository` **or** inline pins) while §3.2 commits — internal inconsistency; plus an unaddressed seed-manifest question (root workspace includes spike; test crates have own `[workspace]`). Consequence: implementer can't tell which mechanism / seed manifest → wrong lockfile or a second design round.
Source: root Cargo.toml is a workspace with `fltk-cst-spike`; the §3.1/§3.2 wording divergence was real.
Disposition action: §3.1 (lines 277–287) commits to one mechanism — FLTK-owned `crates_repository` seeded from root `Cargo.toml`/`Cargo.lock`, covering the three Bazel-linked crates + transitive graph, `fltk-cst-spike` and `tests/*` excluded; "supersedes any reading of an inline-pins alternative." §3.2 (297–302) reads consistently and names the same seed + exclusion set.
Assessment: inconsistency resolved, seed manifest and exclusion set named. Accept.

### design-6 — Fixed
Claim: §2.2 states the Bzlmod toolchain-precedence rule as fact without in-repo grounding (LLM-error-prone); both modules `bazel_dep(rules_rust)` without noting versions must agree; extension-created repos are module-private (Clockwork visibility of FLTK's pyo3 hub unstated). Consequence: groundedness flag — implementer surprised by Bzlmod resolution / a version conflict. Self-rated low-to-moderate.
Disposition action: §2.2 (119–126) marks precedence as "an assumption to validate in the first implementation spike," keeps the robust conclusion (root drives `rust.toolchain`); §3.2 adds (a) extension repos module-private + macro references pyo3 as FLTK-internal labels so Clockwork needs no `use_repo` (304–311), (b) both `bazel_dep(rules_rust)` versions must be compatible/identical, conflict = build error (313–317).
Assessment: the unverified claim is now flagged as spike-to-validate rather than asserted; version-match and visibility addressed. Proportionate to a moderate groundedness finding. Accept.

### design-7 — Fixed
Claim: §2.3/§5.3 say "through `clockwork_native.parser`" without naming the entry method; top rule is `module` (`apply__parse_module` convention); "one representative source string" for the 413-line grammar is non-trivial. Reviewer: "Not a defect... No fix required."
Disposition action: §2.3 (244–246) adds the entry method `apply__parse_module` (top rule `module`) and a note the source string must be a valid `module`.
Assessment: a cheap, source-grounded clarification on a finding the reviewer marked non-blocking; no design decision changed, no harm. Accept.

## Disputed items

None.

## Approved

7 findings: 6 Fixed verified (design-1,2,4,5,6,7), 1 Won't-Do sound (design-3). Coverage check (AC #1–#5 + ADR) maps cleanly; scope discipline holds (additive, rejections reasoned, O1/O2 deferred to user).

---

## Verdict: APPROVED

All seven dispositions acceptable. The two load-bearing gaps the reviewer flagged (design-1 crate-source assembly, design-4 `.so` basename binding) are now concretely specified in §3.4; the CLI-mechanics (design-2) and lockfile-mechanism (design-5) corrections match source exactly; design-3's Won't-Do correctly rejects a no-consequence fact-check confirmation; design-6/7 are proportionate. Design is ready to proceed.
