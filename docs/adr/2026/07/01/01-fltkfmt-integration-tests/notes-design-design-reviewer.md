# Design review findings: fltkfmt integration tests

Verification basis: base commit `c03a801`. I re-verified the design's code citations
against source and re-ran its empirical claims against a freshly built debug
`crates/fltkfmt/target/debug/fltkfmt` binary and the Python reference pipeline.

What checked out (verified, not just plausible):

- All `fltk-fmt-cli/src/lib.rs` line cites are accurate: macro at 283-333, parse-`None`
  arm at 309-311, `fully_consumed` partial-parse return at 315-317, unparse-`None` arm at
  321-326, exit-code-2 contract in the `run_inner` doc at 339-341, `{display}: {msg}`
  prefixing at 405, `temp_dir` helper at 576-584. `-w`/`-i` short flags exist
  (lib.rs:53,57); stdin via no-args or `-` exists (lib.rs:363-366).
- `crates/fltk-parser-core/src/errors.rs:100-160` cite accurate; message skeleton
  `"Syntax error at line {N} col {M}:"` confirmed at errors.rs:149.
- `grammar := , rule+` confirmed (`fltk/fegen/fegen.fltkg:2`); the file ends with exactly
  one `\n` (verified via `od`).
- Parity pytest cites accurate: corpus at `tests/test_fltkfmt_parity.py:42-51` (8 files),
  configs `(80,2)`/`(40,4)` at line 56; it builds the debug binary (line 117) and only
  does single-pass byte-parity — the design's characterization of its coverage gap is
  correct.
- `Makefile:141` runs `cargo test -q --manifest-path crates/fltkfmt/Cargo.toml`
  (confirmed at base commit), so new tests are auto-gated with no Makefile change.
- Empirical claim "fegen.fltkg 80/2 output is byte-identical to the source file":
  verified true (`cmp` clean).
- Empirical trailing-newline claims: verified true in the Rust binary (0-nl == 1-nl,
  single trailing `\n`; 3-nl output == 1-nl output + exactly one `\n`; 3-nl output is a
  formatting fixed point) AND verified byte-identical in the Python backend
  (`plumbing.parse_text` → `unparse_cst` → `render_doc` at 80/2 on all three variants).
- Parse-error claims: both inputs (`"%%% not a grammar\n"`, `"a := \"x\";\n???\n"`) exit
  2 with empty stdout and stderr `<path>: Syntax error at line 1 col 1:` /
  `... line 2 col 1:` respectively — exactly as the design states.
- §2.4's unparse-`None` reasoning is sound and honestly resolves the TODO/request wording
  ("two error branches") against reality; requirements coverage is otherwise complete
  (all four tests + TODO closure in both `TODO.md` and `main.rs`).

## design-1 — Idempotency test as specified fails today on one corpus×config case

- Section: §2.2 Test 1 (`format_format_is_format`): "Corpus: the same 8 `.fltkg` files
  ... Configs: both parity configs ... assert `out2 == out1` byte-for-byte"; and §4 TDD
  note: "Each test should be seen passing against the current binary before the TODO
  entries are deleted."
- What's wrong: the design asserts (implicitly, and via the TDD note) that all 16
  corpus×config cases are idempotent under the current binary. This was never verified —
  the design's "verified against the current binary" markers cover the golden,
  trailing-newline, and parse-error claims only. I ran the full 8×2 sweep:
  `fltk/fegen/test_data/rust_parser_fixture.fltkg` at `w=40 i=4` is **not idempotent**.
  Pass 1 → pass 2 changes a grouped alternation's layout (pass 1 emits
  `( inner:rec_via_sub . "+"` / `| inner:atom ) .`; pass 2 breaks it into a 4-line
  `(` ... `)` block). Pass 2 is a fixed point (pass 3 == pass 2). File-vs-stdin input is
  not the cause (verified: both input modes give identical pass-1 output).
- Why: reproduced deterministically with the debug binary built from base commit
  `c03a801`; command sequence: format file at 40/4, re-format output via stdin at 40/4,
  `diff` (lines 69-72 of the outputs differ).
- Consequence: the implementer lands in a dead end. Test 1 as designed fails on
  `rust_parser_fixture.fltkg × 40/4`, and the design itself rules out the only fixes:
  §2.2 Test 3 says "Changing formatter behavior is out of scope for a test addition," and
  the §4 TDD note requires every test to pass before TODO closure. The implementer must
  either silently shrink the corpus/configs (undocumented scope change), or fix a
  formatter bug out of scope, or ship a failing `make check`. Separately, this is a real
  formatter non-idempotency bug (both backends, presumably, given single-pass parity)
  that per CLAUDE.md's bug protocol should be surfaced to the user, not discovered
  mid-implementation.
- Suggested fix: the design must acknowledge this case explicitly and pick a deliberate
  disposition — e.g. (a) surface the non-idempotency to the user as a bug and carve this
  one case out with a documented, linked exclusion (or an expected-failure-style
  assertion pinning today's two-pass convergence), or (b) assert convergence-by-pass-2
  for that case. Silent corpus shrinkage should not be the implementer's improvised call.

## design-2 — Stale `TODO.md` line references

- Section: §1 ("`TODO.md:93-95`") and §2.3 ("Delete the `## fltkfmt-integration-tests`
  section from `TODO.md` (lines 93-95)").
- What's wrong: at the review base commit `c03a801`, `TODO.md` is 61 lines total; the
  `## fltkfmt-integration-tests` section header is at line 51 (body at 53). The 93-95
  numbers were copied from the exploration, which was done at `8fd5ecf` — the intervening
  commit `c03a801` ("TODO burndown: Delete bad/stale TODOs") deleted other entries and
  shifted the file.
- Why: `grep -n 'fltkfmt-integration-tests' TODO.md` → line 51; `wc -l TODO.md` → 61.
- Consequence: an implementer who follows the line numbers literally targets a
  nonexistent region (past EOF) or, after further TODO.md churn, could delete the wrong
  section. Recoverable because the slug header uniquely identifies the section, but the
  design directive is factually wrong as written.
- Suggested fix: reference the section by slug header only ("delete the
  `## fltkfmt-integration-tests` section"), not by line numbers.

## design-3 — Golden regeneration command relies on CLI defaults the test deliberately avoids

- Section: §2.2 Test 2: the test passes `-w 80 -i 2` explicitly "so the test doesn't
  silently drift if CLI defaults change," but the documented regeneration command is
  `cargo run --manifest-path crates/fltkfmt/Cargo.toml -- fltk/fegen/fegen.fltkg > ...`
  with no width/indent flags.
- What's wrong: internal inconsistency. The test's config is pinned; the regen command's
  config floats with the CLI defaults (`FmtArgs` defaults, lib.rs:53,57).
- Why: if defaults ever change (the exact scenario the explicit flags guard against),
  running the failure message's command regenerates the fixture at the *new* defaults
  while the test keeps formatting at 80/2 — the golden test then fails persistently and
  confusingly right after being "regenerated."
- Consequence: the self-healing instruction in the failure message breaks precisely in
  the scenario the test was hardened for; a future maintainer loops on
  regenerate-fail-regenerate.
- Suggested fix: include `-w 80 -i 2` in the documented regeneration command.
