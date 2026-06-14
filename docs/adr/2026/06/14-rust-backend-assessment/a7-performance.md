# A7 — PERFORMANCE: Was speed a goal, and is it realized/measured?

Production-readiness retrospective, performance dimension. Adversarial. All claims anchored to
source (file:line) or ground-truth runs on this machine (2026-06-14).

---

## TL;DR verdict: **WEAK**

Performance was the **implicit primary justification** for the entire Rust backend ("opt-in for
performance", `05/25-pyo3-cst-plan/phase-plan.md:139`), yet after ~3 months there is **not one
end-to-end measurement** comparing the Rust backend against the Python backend it is meant to
replace. The single benchmark in the repo (`crates/fltk-cst-spike/benches/traverse.rs`) measures
a hand-built spike tree's `Shared<T>` lock overhead in *pure Rust*, never crosses the PyO3
boundary, runs against a **stale `cp`-duplicated spike CST** (not the production generated CST),
and is **wired into no Makefile/CI target** — so it can rot silently and produces no signal in the
gate. The exploration explicitly flagged at the outset that the per-child PyO3 boundary crossing
"could negate the speedup" (`05/25-rust-backend-exploration/synthesis.md:217-219`); the code now
confirms that *every* Python-side child access does a registry dict lookup + O(n) Arc-clone
snapshot (`crates/fegen-rust/src/cst.rs:613-631`), which is exactly the cost that warning was
about — and it remains unmeasured. The packrat memo retains the full O(input × rules) memo table
for the entire parse with no cap and no eviction, which is an unbounded-memory characteristic on
adversarial/large inputs. The runtime building blocks are individually sane (regex compiled once
via `OnceLock`, anchored matching, depth-limit DoS guard), but the **central performance claim is
aspirational, not evidence-backed**, and one perf characteristic (memo memory) is a genuine
production risk on large/hostile inputs.

This dimension does not block on a *correctness* basis, but for a project whose entire reason to
exist is "go faster", shipping with zero validation of that premise is a serious gap.

---

## 1. Was performance a stated goal? YES — and it was flagged unmeasured from day 0

- The Rust path is sold as a performance opt-in: *"The fallback is permanent... The Rust path is
  opt-in for performance"* (`docs/adr/2026/05/25-pyo3-cst-plan/phase-plan.md:139`).
- The exploration's own synthesis listed, under **"Missing from all analyses"**, two performance
  gaps: **(a)** no performance characterization / baseline, and **(b)** the cost of near-identical
  PyO3 CST interfaces — *"every child access crosses the boundary, possibly negating the speedup"*
  (`05/25-rust-backend-exploration/synthesis.md:213-219`, per U1 §1.1).
- Phase plan **Risk R5** conceded the Rust CST nodes "may be *slower* than Python dataclasses due
  to FFI overhead... No baseline profiling data exists... trades performance for infrastructure
  establishment" (`phase-plan.md:243-245`, per U1 §3.2).

So: performance is a first-class stated goal, and the project knew from the start it had no
baseline and a plausible boundary-crossing tax that could erase the win. The retrospective
question is whether that was ever closed. **It was not.**

---

## 2. The only benchmark: what it measures, and everything it does NOT

`crates/fltk-cst-spike/benches/traverse.rs` (the sole bench in the tree — confirmed:
`find -name '*.rs' -path '*bench*'` returns exactly this one file; `criterion` appears in exactly
one Cargo.toml).

What it measures (ground-truth re-run on this machine, release build):
- `build/256`: ~17.7 µs to allocate an `Items` root + 256 `Shared<Identifier>` (~69 ns/child).
- `traverse/256`: ~2.2 µs to read-lock + sum span starts across 256 children (~8.6 ns/child).

These numbers reproduce the recorded gate verdict in the file header (`traverse.rs:17-23`): "~8 ns
per uncontended read... within the same order of magnitude as a `Box` deref. Gate verdict: PASSED."
That conclusion is *fine on its own terms* — `Arc<RwLock<T>>` is cheap to read uncontended. But as
evidence for the **backend's** performance it is nearly worthless, for five concrete reasons:

1. **It never crosses the PyO3 boundary.** The bench is pure Rust (`traverse.rs:50-58`): `tree.read()`
   then `guard.children_item()` then `child_shared.read()`. The actual product is consumed *from
   Python*, where each child access pays a GIL-held registry lookup + Python object materialization
   (§3). The bench measures the one path that is fast and skips the one the exploration warned about.

2. **It is not Python-vs-Python.** There is no Python-dataclass baseline anywhere. `grep` for any
   "vs python / speedup / faster / slower" comparison across `fltk/ crates/ src/ tests/` returns
   **nothing**. So even the in-Rust number cannot be turned into "Rust is Nx faster than the thing
   we're replacing."

3. **It runs against a stale, `cp`-duplicated CST.** The bench imports `fltk_cst_spike::cst::{...}`
   (`traverse.rs:26`). Per U7, `crates/fltk-cst-spike/src/cst.rs` (3,188 LoC) is kept in sync only by
   a literal `cp tests/rust_poc_cst/src/cst.rs crates/fltk-cst-spike/src/cst.rs` in the Makefile —
   it is NOT the production generated CST (`crates/fegen-rust/src/cst.rs`, 15,515 LoC). The bench
   measures a hand-shaped proof-of-concept tree, not what a real grammar emits.

4. **It is wired into no target.** `grep -n 'bench\|criterion\|traverse' Makefile .github/workflows/*`
   returns empty. The bench is not built, run, or regression-checked by `make check`, `make check-ci`,
   or CI. It only runs if a human types `cargo bench -p fltk-cst-spike`. It can silently stop
   compiling against drifted CST APIs with zero signal (it happens to still compile today — verified
   — but nothing guards that).

5. **N=256, one tree shape, one workload.** No depth scaling, no wide-vs-deep, no large-input, no
   pathological-grammar case. It cannot surface memory blow-up or super-linear behavior.

**Net:** the design doc claims a perf gate was "PASSED" (`traverse.rs:21`), but that gate answers
only "is an uncontended `RwLock` read cheap" — a question whose answer was never in doubt. It does
not answer "is the Rust backend faster than the Python backend for a real consumer," which is the
only question the project's performance premise actually raises.

---

## 3. The boundary-crossing tax the exploration warned about — present and unmeasured

The exploration's specific fear was that crossing PyO3 per child access negates the speedup
(`synthesis.md:217-219`). The current code confirms the per-access cost is real:

- **`children` getter snapshots and Arc-clones every child, every call**
  (`crates/fegen-rust/src/cst.rs:613-631`): acquires the read lock, does `guard.children.clone()`
  — an O(n) Vec clone with a refcount bump per node child (comment at :614 admits "Arc clones for
  node children — O(n) refcount bumps") — then builds a brand-new `PyList`, and for each entry
  materializes a Python label object + calls `child.to_pyobject(py)`.
- **`to_pyobject` per child hits the registry** (`cst.rs:233-244`): `registry::get_or_insert_with`
  is a `WeakValueDictionary` lookup keyed by Arc address, under the GIL. So reading N children from
  Python is N hash-map lookups + N potential Python-handle allocations, on top of the Vec clone.
- This is *per call*: the Rust `children` getter "returns a fresh per-call snapshot" (U4; documented
  at `gsm2tree_rs.py:1304-1338`). A Python consumer iterating `node.children` in a loop, or calling
  it repeatedly, re-pays the full snapshot + per-child crossing each time.

None of this is benchmarked. The exploration named exactly this cost as the thing that could erase
the Rust advantage, and three months later there is no measurement of it. For a CST that is
*traversal-heavy by nature* (that's what a CST is for), an unmeasured per-access boundary tax over a
fresh snapshot is precisely the wrong thing to leave unquantified.

There are TODOs acknowledging two micro-costs on this path — `extend-children-owned` (Arc
inc/dec churn on the parse hot path, `gsm2parser_rs.py:706-710` / `TODO.md:41-43`) and
`rust-cst-accessor-clone-efficiency` (per U1 §3.2) — but `extend-children-owned` is explicitly
gated **"Re-open only with profiling evidence"** (`TODO.md:43`), and *no profiling exists*, so by the
project's own rule these can never be acted on. They are perf-debt placeholders against a baseline
that was never taken.

---

## 4. Packrat memo memory profile — unbounded retention, a real large/hostile-input risk

The generated parser holds **one `HashMap<i64, MemoEntry<T>>` per grammar rule** for the whole
parse: 14 cache fields for the fegen grammar (`crates/fegen-rust/src/parser.rs:40-53`), each a
`Cache<Shared<NodeT>>` (= `HashMap<i64, MemoEntry<Shared<NodeT>>>`, `memo.rs:62`).

- **The memo is never cleared or evicted during or after a parse.** `grep '.clear()\|fn reset'` on
  `parser.rs` returns nothing; entries are only ever `insert`/`get_mut` (`memo.rs:297, 321, 335`).
  This is canonical packrat — full memoization buys linear time at the cost of **O(input_length ×
  rule_count) memory**, retained for the entire parse. Every position the parser touches for every
  rule leaves a resident `MemoEntry` holding a `Shared<NodeT>` (an Arc) plus bookkeeping.
- **Consequence:** on a large input (say a multi-MB generated source file an out-of-tree consumer
  feeds in), peak memory grows with input length × rule count, and because successful entries hold
  `Shared<NodeT>` Arcs, the memo **pins the entire CST plus partial/failed sub-parses alive** until
  the `Parser` is dropped. There is no streaming, no windowed cache, no cap. This is a known packrat
  tradeoff, but it is **undocumented as a memory characteristic**, **unmeasured**, and **unbounded**.
  A downstream consumer parsing large files has no guidance and no guard rail on memory.
- The only resource guard is the **depth limit** (`DEFAULT_MAX_DEPTH = 1000`, `memo.rs:74`), which
  bounds *stack* depth, not memo *memory*. And that guard is sticky + must-be-checked: if a caller
  forgets `depth_exceeded()`, they get a silently-truncated parse (`memo.rs:139-164`) — a
  correctness footgun, separately covered in the runtime review, but relevant here because it is the
  *only* backstop near this hot path and it does nothing for memory.

This is the one performance characteristic I would call an actual production risk: **unbounded memo
memory on large/adversarial inputs, never measured, never documented, no cap.**

---

## 5. What the runtime DOES get right (performance-wise)

To be fair and concrete — the building blocks are not naive:

- **Regex compiled once per pattern** via `static REGEX_CELLS: [OnceLock<Regex>; N]` +
  `get_or_init` (`crates/fegen-rust/src/parser.rs:26-30`). No per-call recompile. Good.
- **Anchored matching** with full-haystack input and `Anchored::Yes` (`terminalsrc.rs:141-166`):
  a non-match fails immediately at `byte_pos` without scanning the rest of the input, and
  `regex-automata` gives linear-time matching (no catastrophic backtracking). This is the right
  regex-DoS posture.
- **`cp_to_byte` table built once** at `TerminalSource` construction and `shrink_to_fit`'d
  (`terminalsrc.rs:58-68`); codepoint→byte is O(1) index, byte→codepoint is a binary search
  (`partition_point`, :160). The memory note (`:41-42`, 8 bytes/codepoint, u32 would halve it) is
  an honest acknowledged-and-deferred cost, acceptable for grammar-sized inputs but a linear
  overhead on the source that compounds the §4 memo memory on large inputs.
- **`Shared<T>` shallow clone is an Arc bump**, and uncontended reads are ~8 ns (§2) — fine.
- **One micro-opt already taken on the parse hot path:** the `+`/`*` loop builds the parent with
  `Span::unknown()` and back-patches via `set_span` to avoid an Arc clone per loop entry
  (`gsm2parser_rs.py:689-691`, comment "efficiency-2").

So the *primitives* are competent. The gap is entirely at the level of **whole-system measurement
and the boundary/memory characteristics**, not in the choice of data structures.

---

## 6. Is the performance claim evidence-backed or aspirational?

**Aspirational.** Concretely:

- Zero end-to-end Rust-vs-Python measurement exists (§2.2).
- The one bench measures the cheap path, in pure Rust, against a stale spike CST, gated by nothing
  (§2).
- The exploration's named risk (per-child boundary crossing) is present in the code and unmeasured
  (§3).
- The project's own perf-debt TODOs are gated on "profiling evidence" that was never produced
  (§3) — a self-referential deadlock that guarantees the perf questions stay open.
- No perf regression gate exists in `make check` / CI (`grep` for bench/perf/criterion in Makefile
  check targets = empty), so even if a baseline existed, drift would not be caught.

The U1 intent map reaches the same conclusion from the ADR side: *"the single most important
unanswered question, unchanged since 05/25: does any of this actually go faster end-to-end... No
measurement appears in the entire ADR record"* (`u1-intent-history.md:290-292`). This code-level
review independently confirms it: not only is there no measurement in the ADRs, there is no
measurement *infrastructure* in the codebase capable of producing one (no Python-side bench, no
fegen-CST bench, no comparative harness).

---

## 7. Production-risk summary

| Concern | Severity | Why |
|---|---|---|
| No end-to-end Rust-vs-Python perf validation after 3 mo | major | The entire premise ("opt-in for performance") is unproven; could be neutral or slower under the per-child boundary tax. A consumer migrating "for speed" has no evidence it pays off. |
| Per-child PyO3 crossing + O(n) snapshot clone unmeasured | major | Exactly the cost the exploration flagged could negate the speedup; CST traversal is the dominant use; left unquantified. |
| Unbounded packrat memo memory on large/hostile inputs | major | O(input × rules) resident, never evicted, pins whole CST; no cap, undocumented, unmeasured — a memory-blowup vector. |
| Sole bench is unwired, pure-Rust, stale-CST, single-shape | minor | Gives false "perf gate PASSED" comfort while measuring the one path that was never in doubt. |
| Perf-debt TODOs gated on profiling that doesn't exist | minor | Self-deadlocked: the gate to act on them can never be met. |

**Dimension verdict: WEAK.** Not blocking on correctness, but the backend's reason for existing is
performance and that has been neither measured nor instrumented; one characteristic (memo memory)
is an unmeasured production risk on large inputs.
