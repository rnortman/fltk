# Judge verdict — deep review

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Phase: deep. Base 8ec5324..HEAD 04c41c6 (commit reviewed: 709c01d; fixes at 04c41c6). Round 1.
Notes: 7 reviewer files (security, quality, reuse: no findings); 11 dispositioned items.

## Added TODOs walk

No TODO dispositions. No TODOs added in the diff (TODO.md change is a deletion: `registry-unit-tests` entry + matching code comment removed, per design §5; grep confirms no orphaned slug).

## Other findings walk

### errhandling-1 — Fixed
Claim: `addr_of` raises bare `StopIteration` on registry miss, masking registration bugs; consequence is undiagnosable failure (plumbing bug vs test defect indistinguishable).
Verified at `tests/test_registry_gc_eviction.py:74-78` (HEAD): `next((...), None)` sentinel; `None` → `AssertionError` with `node!r` context; docstring updated to explain what a miss indicates.
Assessment: fix addresses the consequence exactly as suggested. Accept.

### errhandling-2 — Won't-Do
Claim: none — the reviewer's own note states "Not a finding against this diff"; the `.expect` at `registry.rs` race branch is pre-existing and intentionally correct for an invariant violation.
Assessment: no consequence stated, finding self-retracted. Won't-Do is the only sensible disposition. Accept.

### errhandling-3 — Fixed
Claim: `parent.children[0][1]` double-index in stress test raises `IndexError` on structural bug, obscuring root cause vs the test's identity purpose.
Verified at `tests/test_registry_gc_eviction.py:179-181` (HEAD): `assert len(parent.children) == 1 and len(parent.children[0]) == 2` with message, placed before the double-index access — matches the reviewer's suggested fix verbatim.
Assessment: accept.

### correctness-1 — Fixed
Claim: `snapshot` copied via `dict(WeakValueDictionary)` — check-then-act (`keys()` then per-key `__getitem__`); weakref death mid-copy raises flaky `KeyError`. Latent (not triggerable with current non-GC-tracked handles), should-fix.
Verified at `crates/fltk-cst-core/src/registry.rs:140-148` (HEAD): now `registry.call_method0("items")?` → `dict_class.call1((items,))`; `WeakValueDictionary.items()` dereferences each weakref atomically per entry and skips dead ones; doc comment explains the TOCTOU hazard. `dict(iterable_of_pairs)` is valid construction.
Assessment: fix is the reviewer's suggested fix; correct. Accept.

### test-1 — Won't-Do (finding bogus)
Claim: `test_register_after_eviction_installs_fresh` ends without `del obj_b`, violating the module's documented `del` discipline.
Responder: finding factually incorrect — `del obj_b` is present at line 256.
Verified: `git show 04c41c6:tests/test_registry_gc_eviction.py` — the test's last line is `del obj_b`; the 709c01d..04c41c6 diff touches only `addr_of` and the stress-test shape assertion, so `del obj_b` was already present in the commit the reviewer reviewed (709c01d).
Assessment: responder right; reviewer hallucinated the omission. Won't-Do correct. Accept.

### test-2 through test-6 — Won't-Do
Claims: each is an explicit "no fix needed / observation for record only" confirmation note (coverage split between stress test and `test_py_new_registers_immediately`; near-duplicate snapshot tests acceptable; `is`-identity strictly stronger than addr equality; snapshot lifetime sound; eviction-after-del covered elsewhere). No consequence stated in any.
Assessment: no action requested, none owed. Accept all five.

### efficiency-1 — Won't-Do
Claim: per-iteration `gc.collect()` in the 200-iteration stress loop; consequence is full-collection cost scaling with suite size — potentially seconds of wall time as the suite grows.
Rationale: design-mandated — design §3 specifies "`gc.collect()` (each iteration)" for `test_stress_create_drop_cycles`; the reviewer itself framed it as "a design-level choice to revisit, not an implementer deviation."
Verified: design §3 quote matches; correctness reviewer's empirical run shows the whole 10-test file passes in 0.56s, so the consequence is not currently material. An implementer silently deviating from an approved-design specification would be the wrong move; the cost concern is a future design revisit at most.
Assessment: rationale sound. Accept.

### efficiency-2 — Won't-Do
Claim: `addr_of` copies the whole registry per call, O(registry size) — but the reviewer's own fix line reads "Fix: none required now," scale-ceiling note only; registry is delta-bounded and evicted per iteration; preemptive plumbing unjustified.
Assessment: reviewer requested no action; Won't-Do matches the finding's own conclusion. Accept.

## Disputed items

None.

## Approved

11 findings: 3 Fixed verified, 8 Won't-Do sound (1 bogus finding correctly rejected, 1 self-retracted, 5 observation-only, 2 with sound rationale).

---

## Verdict: APPROVED

All dispositions acceptable. Round 1, no rework needed.
