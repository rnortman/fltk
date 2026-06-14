# U7 — Rust Backend: Completeness vs Python, plus Cruft / Dead Code

Scope: an honest inventory of what the Rust backend has FINISHED, what it has
DEFERRED, and what is MISSING relative to the Python backend's feature set; plus
the status of leftover artifacts (spike, fegen-rust, fixtures), duplicated/abandoned
code paths, and committed-generated-code drift risk. All claims cite file:line at
HEAD = c018206. `.claude/worktrees/**` ignored throughout.

---

## 1. The headline gap: Python has THREE generators, Rust has TWO

The Python backend produces, from one grammar, a **CST + parser + unparser**. The
Rust backend produces **CST + parser only**. The entire unparser/formatter
subsystem has **no Rust equivalent and no in-progress Rust work**.

Python unparser subsystem (`fltk/unparse/`), with no Rust counterpart:
- `gsm2unparser.py` (73,384 bytes) — the unparser code generator.
- `genunparser.py`, `fmt_config.py` (33,320 bytes), `resolve_specs.py`, `renderer.py`,
  `accumulator.py`, `combinators.py` — formatter config, spec resolution, rendering.
- `unparse_cli.py` at `fltk/` top level.
- CHANGELOG `[0.2.0]` calls unparser generation "the main feature" of that release
  ("alpha-level support for generating unparsers and source", CHANGELOG.md:~46).

Confirmation that no Rust unparser exists or is planned: `grep -ni unparse` across
`gsm2tree_rs.py`, `gsm2parser_rs.py`, `gsm2lib_rs.py` returns nothing; the only
`unparse` hits in `genparser.py` are `ast.unparse(...)` (Python AST → source, the
*Python* CST/parser writer) at genparser.py:114, 187, 206. There is no TODO(slug)
for a Rust unparser and no ADR proposing one (`docs/adr/2026/**` has ~30 dirs, all
CST/parser/runtime/packaging — none unparser-on-Rust).

**Production implication:** any out-of-tree consumer that uses FLTK for formatting /
source-rewriting (the documented `[0.2.0]` headline use case) CANNOT move to the Rust
backend at all. The Rust backend is a parse-only product. Whether that is acceptable
is a scoping decision the lead must make explicitly — today it is implicit.

---

## 2. Parser feature coverage: Rust vs Python (within parse-only scope)

Within the parse-only scope, coverage is broad but has hard `NotImplementedError`
holes. All in `fltk/fegen/gsm2parser_rs.py`:

| Feature | Rust status | Evidence |
|---|---|---|
| Literals | DONE | `_gen_consume_term` Literal arm, gsm2parser_rs.py:751 |
| Regex terms | DONE (restricted subset) | :757; restriction §2.1 below |
| Quantifiers `?` `+` `*` | DONE | `is_optional`/`is_multiple`/`is_required`, :533, :635, :682 |
| Separators `.` `,` `:` (no-ws / ws-allowed / ws-required) | DONE | trivia/sep handling :575-620; fixture `stmt`, `paren_expr` |
| `initial_sep` (leading separator) | DONE | fixture `leading_ws`, `rust_parser_fixture.fltkg` |
| Disposition SUPPRESS `%` | DONE | :821, :1007 |
| Disposition INCLUDE `$` | DONE | :1031 (unlabeled INCLUDE → push_child) |
| **Disposition INLINE `!`** | **NOT IMPLEMENTED** (raises) | `"INLINE disposition is not supported in Rust parser generation"` :825-826 and :1011-1012 |
| Sub-expressions `( ... )` incl. recursive inline-to-parent | DONE | `_gen_subexpr_term` :776; fixture `rec_via_sub` |
| Direct + indirect left recursion | DONE | fixture `expr`, `lval`/`rval`; packrat memo |
| Union labels (one label → multiple types) | DONE | fixture `val` |
| Multibyte literals / regex (codepoint spans) | DONE | fixture `arrow` (→), `latin_word` |
| **Invocation terms** | **NOT IMPLEMENTED** (raises) | `"Invocation terms are not supported in Rust parser generation"` :769-770 |
| Trivia / whitespace capture (`capture_trivia` flag) | DONE | parser carries `capture_trivia: bool` :338,:352; both trivia-rule (regex `\s+`) and grammar-trivia paths :575-620; Python binding `#[pyo3(signature=(text, capture_trivia=false, ...))]` :900-910 |
| Parse depth limit | DONE | `max_depth` :900-901 (ADR 06/11-parse-depth-limit) |
| Error reporting (line/col, expected-set) | DONE w/ parity test | ErrorTracker + `format_error_message` wired :273,:337,:387; structural parity asserted by `assert_error_equiv` (tests/parser_parity.py:91-102, used by test_rust_parser_parity_fegen.py:26) |

### 2.1 Regex subset restriction (permanent, not a TODO)

Grammar regexes must use the common subset of Python `re` and `regex-automata`;
**lookahead, lookbehind, backreferences are rejected** (gsm2parser_rs.py:6-15 module
docstring; enforced by a generated `#[test] fn all_regex_patterns_compile` emitted
into every parser, :980-990). This is documented as the "permanent default," not a
deferral. It is a real behavioral divergence from the Python backend, which uses
Python `re` and accepts lookahead. Concretely, `fltk.fltkg`'s `block_comment`
(`content:/[^*]*(?:\*(?!\/)[^*]*)*/`, fltk.fltkg:76) uses `(?!\/)` negative lookahead
and would be rejected by the Rust backend. (The simpler `fegen.fltkg` block_comment
rewrites this without lookahead, :21 — see §3.)

### 2.2 The INLINE hole means the Rust backend CANNOT self-host `fltk.fltkg`

`fltk.fltkg` uses INLINE *disposition* on items: `!alternatives` at fltk.fltkg:11
and `"(" , !alternatives , ")"` at :34. Combined with the lookahead regex (§2.1),
`fltk.fltkg` is doubly un-processable by the Rust backend. The Python backend
handles INLINE (gsm2parser.py inline_to_parent=True paths, :371,:533,:713).

This is mitigated, not solved: FLTK self-hosts the Rust backend on the **simpler
`fegen.fltkg`** instead (fegen.fltkg has no INLINE disposition — its only `!` is the
literal token `inline:"!"` at :14, which is just matching the `!` character, not an
INLINE item). The Makefile generates `fltk_cst.py` itself from `fegen.fltkg`, noting
"fltk.fltkg is intentionally broken" (Makefile:248-252). So the in-tree self-hosting
proof runs on a deliberately reduced grammar that sidesteps both Rust gaps. An
out-of-tree consumer whose grammar uses `!` inlining or lookahead regex hits a hard
`NotImplementedError` at generation time.

**Net:** parse-only coverage is good for the common subset, but "drop-in replacement"
is false for grammars using INLINE disposition, invocation terms, or
lookahead/lookbehind/backreference regex. None of these has a TODO(slug) tracking a
fix — they are silent scope cuts.

---

## 3. TODO inventory (TODO.md ↔ TODO(slug) comments) — all in sync, all minor

`TODO.md` has 11 real entries (plus the placeholder). Every `TODO(slug)` comment in
code joins to an entry; no orphans. Cross-check:

- `bazel-rules-rust` — MODULE.bazel does not yet build the Rust ext via Bazel (ADR in
  progress 06/13-rust-bazel-packaging). **No code comment** (intentional — it's a
  "what's missing" note), but referenced in CLAUDE.md.
- `verify-pyo3-ext-module`, `bazel-cst-spike-hub` — MODULE.bazel:42, :31. Bazel hygiene.
- `bazel-lib-rs-no-cst` — rust.bzl:311. Future runtime-only crate edge case.
- `native-submodule-error-context` — crates/fltk-cst-core/src/py_module.rs:86. Error-context polish.
- `native-span-init-error-context`, `submodule-register-fn-convention`, `rust-ident-dedup` —
  gsm2lib_rs.py:159, :48, :16. Error-context / validation polish + a dedup nit.
- `extend-children-owned` — gsm2parser_rs.py:706. Perf micro-opt, explicitly gated on
  "profiling evidence" before reopening.

Also present but NOT a backend-completeness gap:
- gsm2tree_rs.py:874 `TODO(rust-cst-child-node-identity)` — a code comment with **no
  matching TODO.md entry** (verify: `grep rust-cst-child-node-identity TODO.md` →
  none). Either resolved-and-stale or an orphan comment; minor bookkeeping drift.
- `TODO(module)` strings at gsm2parser.py:51, gsm2unparser.py:55 are placeholder
  module *names* in the Python backend, not TODO-system entries.
- test_nullable_loop_guard.py asserts a `TODO(nullable-loop)` block is **absent** from
  generated output — a resolved feature, not pending.

**Assessment:** The TODO ledger is clean and honest about the *small* stuff. What it
does NOT capture is the *large* stuff — the unparser absence (§1) and the INLINE /
invocation / lookahead-regex parser holes (§2) are nowhere in TODO.md. The TODO
system tracks polish, not the strategic feature gaps. A reader trusting TODO.md as
the "what's left" list would badly underestimate the distance to parity.

---

## 4. Leftover artifacts / dead code / duplication

### 4.1 `tests/rust_cst_fegen/` — DEAD, byte-identical duplicate of `crates/fegen-rust/` (~17K LoC)

This is the biggest cruft finding. `tests/rust_cst_fegen/` and `crates/fegen-rust/`:
- Same crate name `fegen-rust-cst`, same lib name `fegen_rust_cst`
  (tests/rust_cst_fegen/Cargo.toml vs crates/fegen-rust/Cargo.toml — identical
  `[package]`/`[lib]` modulo the relative `path = "../../crates/..."` vs `"../..."`).
- **Byte-identical generated sources**: `diff -q` reports IDENTICAL for both
  `cst.rs` (15,515 LoC each) and `parser.rs` (1,656 LoC each).
- fegen-rust/Cargo.toml comment: "Promoted from tests/rust_cst_fegen/ — canonical
  first-class fegen Rust artifact." The promotion copied the crate to `crates/` but
  **never deleted the original.**

The original is now orphaned:
- **No build target** writes to or builds it: `grep rust_cst_fegen Makefile` → NONE.
  The Makefile builds `crates/fegen-rust` (build-fegen-rust-cst, :205-206) and
  regenerates `crates/fegen-rust/src/cst.rs` in gencode (:274-275). `tests/rust_cst_fegen`
  appears in **no** Makefile recipe.
- **No test consumes it.** The `fegen_rust_cst` Python module that ~10 test files
  import (test_fegen_rust_cst.py, test_phase4_fegen_rust_backend.py, etc.) is produced
  by `crates/fegen-rust` via build-fegen-rust-cst, not by tests/rust_cst_fegen.
- **Stale CHANGELOG.** CHANGELOG.md:22 still claims "`make gencode` now regenerates
  `tests/rust_cst_fegen/src/cst.rs`" — but the current gencode target regenerates
  `crates/fegen-rust/src/cst.rs` (Makefile:274). The CHANGELOG describes a pre-promotion
  world. The only live references to `rust_cst_fegen` are historical ADR/CHANGELOG prose.
- It is fully git-tracked (6 files), so it still ships in the repo and still gets
  cargo-deny'd? No — even cargo-deny targets only `crates/fegen-rust` (Makefile:183),
  not tests/rust_cst_fegen. So it is built/checked by **nothing**.

**Verdict:** ~17,171 lines of committed generated Rust (15,515 + 1,656) that nothing
builds, tests, checks, or regenerates. Pure dead weight + drift bait. Should be
deleted. (It is the single largest cleanup win available.)

### 4.2 `crates/fltk-cst-spike/` — NOT dead, but redundant with `tests/rust_poc_cst/`

The spike is a live workspace member (root Cargo.toml members list) and is exercised:
- `cargo test -p fltk-cst-spike` and `-p fltk-cst-spike --features python` run in
  `cargo-test-no-python` (Makefile:137) and clippy (:145-146). `spike_tests.rs`
  (635 LoC) is real and runs.
- `benches/traverse.rs` is a real criterion benchmark with a recorded gate verdict
  (the Box→Shared/Arc<RwLock> overhead measurement, traverse.rs:1-25). This is the
  *one* artifact the spike uniquely owns — there is no other perf bench in the repo.

BUT its `cst.rs` (3,188 LoC) is **byte-identical** to `tests/rust_poc_cst/src/cst.rs`
(`diff -q` → IDENTICAL), and gencode keeps them in lockstep with a literal copy:
`cp tests/rust_poc_cst/src/cst.rs crates/fltk-cst-spike/src/cst.rs` (Makefile:288,
comment: "same grammar as rust_poc_cst/src/cst.rs; cp makes identity explicit").

So the spike's purpose has narrowed to: (a) the python-OFF compile lane exerciser and
(b) the home of the one traversal benchmark. Both could fold into `tests/rust_poc_cst`
(which already has a python-off lane, cargo-test-no-python:141) plus a benches/ dir,
eliminating the duplicated 3,188-LoC cst.rs and the `cp` step. Keeping it is
defensible (it predates poc_cst and the bench has historical value) but it is
**redundant scaffolding still carried as a first-class workspace member** — the
TODO(bazel-cst-spike-hub) note even flags that its workspace membership leaks it into
the Bazel crate hub (MODULE.bazel:31). Recommend: demote/merge.

### 4.3 Fixture sprawl — four CST fixtures + one parser fixture, overlapping grammars

Active, each with a purpose, but the set is large and partly overlapping:
- `tests/rust_poc_cst` (poc_grammar.fltkg, 3-rule toy) — CST-only, uniform shape proof.
- `crates/fltk-cst-spike` (same grammar, copied) — see §4.2.
- `tests/rust_cst_fixture` (phase4_roundtrip.fltkg, 6,990-LoC cst.rs) — module
  `phase4_roundtrip_cst`, top-level-Span exception test (test_module_split.py:223-224).
- `crates/fegen-rust` (fegen.fltkg, 15,515-LoC cst.rs + parser) — the canonical
  self-host artifact.
- `tests/rust_parser_fixture` (rust_parser_fixture.fltkg + collision_fixture.fltkg) —
  the feature-coverage parser fixture (20,332-LoC cst.rs + 1,649 parser + collision
  pair). This is the genuinely valuable one for parser coverage.

This is a lot of committed generated code to maintain, but only `rust_cst_fegen`
(§4.1) is truly dead.

---

## 5. Committed-generated-code DRIFT RISK (no CI gate)

All generated Rust (and the generated Python CST/parser) is **committed to the repo**
and regenerated only by a manual `make gencode` run. Total committed generated Rust
across the live + dead fixtures: **75,670 lines** (cst.rs/parser.rs files tallied:
fegen-rust 17,171; rust_cst_fegen 17,171 dead; rust_cst_fixture 6,990; rust_poc_cst
3,188; spike 3,188; rust_parser_fixture 20,332 + collision 5,981).

**The drift gate is manual, not enforced.** `make check` / `check-ci` / `check-common`
(Makefile:39-76) run lint/format/typecheck/test/cargo-clippy/cargo-deny but do **NOT**
run `gencode` followed by a `git diff --exit-code`. The gencode target's own comment
admits the gate is human-driven: "After running, `git diff --stat` reveals any drift
... (cheat-detection: committed hand-patches show as diffs)" (Makefile:245-246). There
is no CI step (no `.github` reference to gencode; `grep -rn gencode .github` → none)
and no Makefile target that fails on drift.

**Consequence:** a generator change (or a hand-edit to a committed `.rs`/`.py`) that is
not followed by a manual `gencode` + commit produces silent divergence between "what
the generator emits" and "what is committed and tested." The committed artifact is what
tests run against, so a generator regression can pass CI while the committed code is
stale, or a hand-patched committed file can pass CI while being unreproducible from the
generator. For a project whose generated output is the public product, an automated
"regenerate and assert no diff" gate is a notable missing control.

---

## 6. What's actually left to reach production (honest inventory)

**Strategic / large (none tracked in TODO.md):**
1. **Unparser/formatter on Rust** — entirely absent. Either build it (a multi-month
   effort mirroring the 73KB+ Python `gsm2unparser.py` + fmt_config + resolve_specs +
   renderer stack) or make "Rust backend is parse-only" an explicit, documented scope
   decision. Today it is implicit; consumers can't tell.
2. **INLINE disposition (`!`) in the Rust parser** — hard `NotImplementedError`
   (gsm2parser_rs.py:825,:1011). Required for true drop-in parity; `fltk.fltkg` itself
   needs it.
3. **Invocation terms** — hard `NotImplementedError` (:769). Unknown how many real
   grammars use them, but it's a silent cut.
4. **Lookahead/lookbehind/backreference regex** — permanently rejected by
   regex-automata (:6-15). Documented as permanent; means some Python-valid grammars
   (incl. `fltk.fltkg`) can't be ported. Needs to be a called-out compatibility note,
   not buried in a docstring.

**Cleanup (mechanical, low-risk, high-clarity):**
5. **Delete `tests/rust_cst_fegen/`** (~17K dead LoC, no builder/consumer; §4.1).
6. **Fix stale CHANGELOG.md:22** (claims gencode regenerates a path it no longer does).
7. **Merge/demote `crates/fltk-cst-spike`** into `tests/rust_poc_cst` to kill the
   `cp`-duplicated 3,188-LoC cst.rs and remove a workspace member that leaks into the
   Bazel hub (§4.2, TODO(bazel-cst-spike-hub)).
8. **Reconcile orphan `TODO(rust-cst-child-node-identity)`** at gsm2tree_rs.py:874 (no
   TODO.md entry; §3).

**Process / control gap:**
9. **Add an automated gencode-drift gate** to `make check-common` / CI: run gencode,
   `git diff --exit-code`, fail on diff (§5). Currently the regen→diff check is
   manual and trust-based.

**What IS solid (don't restart these):** CST runtime (Shared<T> identity, registry,
spans, escape, error), the parser runtime (packrat memo, terminalsrc, error tracking),
the python/no-pyo3 feature-gating discipline, error-message structural parity testing,
the broad parser feature coverage in the common subset, the regen-from-grammar pipeline
itself (genparser CLI), and the supply-chain + feature-matrix CI. The bones are good;
the gaps are (a) the missing unparser, (b) three named parser-feature cuts, and (c)
two cleanup/control items (dead duplicate crate + no drift gate).
