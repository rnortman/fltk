# Handoff: TODO burndown 2026-06-12 — execution plan

Style: concise, precise, no padding. For a fresh orchestrator session. Triage with USER DECISION markers: `triage.md` (this dir). All decisions are user-approved; do not re-litigate.

## Prepared ADR workflows (run the standard chain per dir)

Each dir contains `request.md` (serves as the request+requirements; explicit about outcome and constraints) and `exploration.md` (validated, adequate — **skip the explore and phases, start at design**). Design may run in parallel across all three; **implementation strictly serialized**. Burndown policy: skip ship-gate, no pushes, squash each item to a single commit on `main` including its ADR docs.

1. `docs/adr/2026/06/12-rust-cst-eq-depth/` — iterative PartialEq on generated Rust CST nodes (uncatchable stack-overflow abort on deep-tree `==`). Highest value; queue first.
2. `docs/adr/2026/06/12-rust-generated-ident-collisions/` — generation-time cross-rule identifier collision check + `DropWorklistItem` reserved name.
3. `docs/adr/2026/06/12-error-msg-bidi-escape/` — extend escape set to bidi/LS-PS/zero-width (new `\u{XXXX}`-style spelling, both backends, repin parity) + fix divergent third copy in `cross_cdylib.rs`. Largest item.

## Direct actions (no workflow needed)

### `regex-automata-features` — one-liner, USER DECISION: Do

In `crates/fltk-parser-core/Cargo.toml`, change the `regex-automata` dep to `default-features = false` with the validated parity-with-`regex=1` set:
`["std", "syntax", "perf", "unicode", "meta", "nfa-backtrack", "nfa-pikevm", "hybrid", "dfa-onepass"]`
(drops only `dfa-build`/`dfa-search`; behavior-identical, meta engine falls back to lazy DFA — see `exploration-regex-automata-features.md`). Build + full test suite; remove the `TODO.md` entry and the `TODO(regex-automata-features)` Cargo.toml comment.

### Deletions — USER DECISION: Delete (rationale in `triage.md`; do not re-add)

Remove the `TODO.md` entry AND every `TODO(<slug>)` code comment (grep for the slug; if any occurrence is in generated files, fix the generator source and regen → `make fix`):

- `error-msg-escape-zero-copy` — comment at `crates/fltk-parser-core/src/errors.rs` (`escape_control_chars`).
- `mutator-remove-at-oob-atomicity` — comment at `fltk/fegen/gsm2tree_rs.py:1318-1319` (`_generic_remove_at`).
- `mutator-rs-fast-path-int-index` — comments in `fltk/fegen/gsm2tree_rs.py` (`_generic_insert`/`_generic_remove_at`/`_generic_replace_at`).

### No action

- `extend-children-owned` — USER DECISION: keep, blocked on profiling evidence. Leave `TODO.md` entry and code comments untouched.
- `bazel-rules-rust` — user-excluded from this burndown.

## End state checklist

- 3 workflow items implemented, each squashed to one commit on `main` with its ADR docs.
- `regex-automata-features` done directly (own commit).
- 3 TODO entries + comments deleted (can ride with any commit or their own).
- `TODO.md` afterwards contains only: `example-placeholder`, `bazel-rules-rust`, `extend-children-owned`.
- This triage dir's artifacts committed.
- User reviews all commits at end of batch; user pushes.
