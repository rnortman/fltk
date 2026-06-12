# Adversarial Validation: TODO(regex-automata-features)

Concise. Precise. No fluff. Source-anchored facts only.

---

## 1. What APIs does fltk-parser-core actually call from regex-automata?

Three import sites in `crates/fltk-parser-core/src/terminalsrc.rs`:

- `:8` — `use regex_automata::meta::Regex;`
- `:9` — `use regex_automata::{Anchored, Input};`

Call sites in `consume_regex` (`:141-165`):

```rust
let input = Input::new(text)
    .anchored(Anchored::Yes)
    .span(byte_pos..text.len());
let m = regex.search(&input)?;
```

`Regex::new(pattern)` — called in tests (`:325`, `:334`, etc.) and re-exported
for generated code.

`Regex::search(&Input)` — the only search API called at runtime.

`lib.rs:23` re-exports the entire `regex_automata` crate:
`pub use regex_automata;` so generated parsers access
`fltk_parser_core::regex_automata::meta::Regex` without a direct dep.

Generated parsers (e.g. `tests/rust_parser_fixture/src/parser.rs:16`) use only
`meta::Regex::new(pattern)` and pass the resulting `&Regex` to
`TerminalSource::consume_regex`. They call no other `regex_automata` API
directly.

---

## 2. Which features does the code actually require?

The code path is `regex_automata::meta::Regex` → `Regex::new` → `Regex::search`.

The `meta` feature in `regex-automata-0.4.14/Cargo.toml` expands to:

```
meta = ["syntax", "nfa-pikevm"]
```

`syntax` → `dep:regex-syntax` + `alloc`.  
`nfa-pikevm` → `nfa-thompson` → `alloc`.

`meta::Regex` is the only API the crate's own code calls. The `std` feature
(`regex-automata-0.4.14/Cargo.toml` `[features]` section) adds std-dependent
code (notably OS-visible error formatting). The code uses `Regex::new` at
startup and `Regex::search` on the hot path; no `hybrid`, `dfa-build`,
`dfa-search`, `nfa-backtrack`, `perf`, or `unicode` APIs are referenced
directly.

---

## 3. What features does the current `default` pull in vs. what `regex=1` pulled?

**Current** (`regex-automata = "0.4"`, default features):

Per `cargo tree -p fltk-parser-core --edges features` output:

```
regex-automata feature "default"
├── dfa → dfa-build + dfa-search + dfa-onepass
│   ├── dfa-build → (full DFA determinizer + NFA-Thompson)
│   ├── dfa-search
│   └── dfa-onepass
├── hybrid → (lazy DFA + NFA-Thompson)
├── meta → nfa-pikevm + syntax
├── nfa → nfa-thompson + nfa-pikevm + nfa-backtrack
├── perf → perf-inline + perf-literal (aho-corasick + memchr)
├── std
├── syntax → dep:regex-syntax
└── unicode → (7 sub-features)
```

**Prior** (`regex = "1"`, default features):

`regex-1.12.4/Cargo.toml` default features activate, through `regex-automata`:
`std`, `perf-inline`, `perf-literal`, `unicode` (all 7 sub-features),
`nfa-pikevm`, `nfa-backtrack`, `dfa-onepass`, `hybrid`. They do **not**
activate `dfa-build` or `dfa-search` (those are under `regex`'s
`perf-dfa-full` feature, which is non-default). `nfa-thompson` is pulled
transitively by `hybrid` and `nfa-backtrack` in both cases.

**Delta — features enabled by current dep that were not enabled by `regex=1`:**

- `dfa-build` (the full DFA determinizer — NFA→dense DFA at `Regex::new` time)
- `dfa-search` (the full DFA search runtime)

These are the only two additional features. `dfa-onepass` and `hybrid` are
shared between both.

---

## 4. Does the meta engine actually use the full DFA at runtime?

`regex-automata-0.4.14/src/meta/wrappers.rs:834-924` — `DFAEngine`:

```rust
pub(crate) struct DFAEngine(
    #[cfg(feature = "dfa-build")] dfa::regex::Regex,
    #[cfg(not(feature = "dfa-build"))] (),
);
```

`DFAEngine::new` (`:839-924`) is guarded by `#[cfg(feature = "dfa-build")]` and
contains two early-exit checks before doing any work:

1. `if !info.config().get_dfa()` — returns `None` if DFA is disabled.
2. NFA state limit check using `get_dfa_state_limit()`.

Default value of `get_dfa_state_limit()` per
`regex-automata-0.4.14/src/meta/regex.rs:3186`:

```rust
self.dfa_state_limit.unwrap_or(Some(30))
```

Default value of `get_dfa_size_limit()` per `:3176`:

```rust
self.dfa_size_limit.unwrap_or(Some(40 * (1 << 10)))  // 40 KiB
```

So the full DFA is attempted only when the NFA has ≤ 30 states. Many trivial
patterns (e.g. `\w+`, single character classes, keywords) will have NFA state
counts well within that limit and **will** have the full DFA built at `Regex::new`
time. Patterns exceeding 30 NFA states fall back to `hybrid` (lazy DFA) or
`nfa-backtrack` / `nfa-pikevm`.

`crates/fltk-parser-core/src/terminalsrc.rs:141` calls `Regex::new` per pattern
at compile time (via `OnceLock`). The DFA determinization cost is paid once per
pattern per process lifetime, not per parse call.

---

## 5. Is the TODO's suggested minimal feature set accurate?

TODO text proposes:
```
default-features = false, features = ["std","syntax","perf","unicode","meta",
  "nfa-backtrack","nfa-pikevm","hybrid","dfa-onepass"]
```

This matches exactly what `regex=1` default features enable in `regex-automata`:
`std`, `syntax` (via `meta`), `unicode`, `nfa-pikevm` (via `meta`),
`nfa-backtrack`, `hybrid`, `dfa-onepass`, `perf`. Omits only `dfa-build` and
`dfa-search`. The suggested set is **accurate** as a parity-with-`regex=1`
minimal set.

---

## 6. Would pinning risk behavior/perf change?

**Behavior:** No. The meta engine's `Regex::new` and `Regex::search` API
behavior is identical with or without `dfa-build`; the engine simply won't
attempt full DFA construction (the `DFAEngine::new` path returns `None`
unconditionally when `dfa-build` is absent). The lazy DFA (`hybrid`) path,
which is shared between both feature sets, provides the same match semantics.

**Performance:** Yes, there is a real difference, bounded and one-directional:

- With `dfa-build`: simple patterns (≤ 30 NFA states, ≤ 40 KiB DFA) get a fully
  compiled DFA at startup. Subsequent `search` calls on those patterns are
  table-lookup speed.
- Without `dfa-build`: the same patterns fall through to `hybrid` (lazy DFA),
  which builds the DFA lazily as it encounters new states. Amortized cost is
  similar for repeated use of the same pattern on long inputs; startup cost
  (first search) is lower (no upfront determinization).

For a parser that calls the same `Regex` objects repeatedly on different
positions in a single input, the lazy DFA likely reaches a fully-compiled
state quickly — the perf difference is probably negligible in practice, but
there is no measurement.

---

## 7. Is the `pub use regex_automata` re-export a complication?

Yes. `crates/fltk-parser-core/src/lib.rs:23`:

```rust
pub use regex_automata;
```

This re-exports the *entire* `regex_automata` crate. Generated parser code uses
`fltk_parser_core::regex_automata::meta::Regex` exclusively (confirmed in
`fltk/fegen/gsm2parser_rs.py:269`, `tests/rust_parser_fixture/src/parser.rs:16`).
They call only `Regex::new` and pass `&Regex` to `consume_regex`.

The re-export is intentional (version coherence guarantee, documented in
`lib.rs:10-14`). Pinning features on `fltk-parser-core`'s dep affects what
modules/types are visible through the re-export, but generated code only uses
`meta::Regex` which is gated by the `meta` feature — present in both the
current and the suggested minimal sets.

---

## 8. Is there a deeper structural problem?

No. The `pub use regex_automata` re-export is a deliberate architecture choice
(version coherence), not a workaround. The choice to use `default-features`
rather than the minimal set was explicitly called out at the time the TODO was
written (commit `61f9384`, 2026-06-11): the commit message says "regex-automata
features pinned to match the prior regex feature selection (no binary-size
regression)" but the `Cargo.toml` comment added in the same commit
acknowledges the feature set was NOT pinned to the `regex=1` equivalent —
default features were kept deliberately. The TODO is self-consistent with the
commit.

The "deeper problem" framing in the TODO (compile time / binary size) is
accurate in direction: `dfa-build` adds the determinization code and the dense
DFA data structures to the binary. The `DFAEngine` struct is `#[cfg(feature =
"dfa-build")]`-gated, so it compiles to zero overhead when absent. `dfa-search`
adds the DFA search runtime. Both are dead code if the DFA is never actually
built (i.e., all patterns exceed the 30-state limit), but the *compilation* of
that code and its presence in the binary is unconditional when the features are
enabled.

---

## 9. Summary verdict

| Claim | Verdict |
|---|---|
| Default features include `dfa-build`/`dfa-search` | **True** — confirmed via `cargo tree` output |
| `regex=1` default did not enable those features | **True** — `regex-1.12.4/Cargo.toml`: `perf-dfa-full` (non-default) enables them |
| DFA-build is size-capped | **True** — `get_dfa_state_limit()` default = 30, `get_dfa_size_limit()` default = 40 KiB |
| Code only calls `meta::Regex` and `{Anchored, Input}` | **True** — confirmed `terminalsrc.rs:8-9, 147-150` |
| No `dfa::`, `hybrid::`, `nfa::` APIs called directly | **True** — full crate source search found zero direct calls |
| Minimal feature set in TODO comment is accurate | **True** — matches what `regex=1` default activated in `regex-automata` |
| Pinning would change behavior | **False** — meta API behavior is engine-selection-agnostic |
| Pinning would change perf | **Partially true** — small patterns lose pre-built DFA; lazy DFA fills in; difference likely negligible without profiling data |
| `pub use regex_automata` re-export is a structural problem | **False** — intentional, documented version-coherence mechanism |
| The TODO was written at the time the choice was made | **True** — same commit `61f9384` that switched from `regex=1` to `regex-automata=0.4` |

**Overall:** The TODO is accurate. The suggested minimal feature set is correct.
The only un-validated claim is the magnitude of compile-time and binary-size
impact, which would require a measurement.
