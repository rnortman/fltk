# Design review: fix-forged-abi-segfault

Reviewer: design-reviewer (adversarial fact-check). Base commit 205c36b.

## Verification summary (what checked out)

The design's load-bearing technical claims were verified live against the built extension
and source:

- **Blocker is real.** Subprocess repro of §1.1 `Forge` exits with returncode `-11`
  (SIGSEGV), crash before output. Matches §1.1.
- **Core gate fact verified live.** `SourceText.__basicsize__ == 24 ==
  SourceText._fltk_cst_core_abi_layout`; `Span.__basicsize__ == 40 == layout attr`.
  Trivial `Forge` (copied attrs, no `__slots__`) → basicsize 32 ≠ 24 (rejected by gate).
  `class Forge: __slots__=('x',)` → basicsize 24 (passes gate — the documented residual).
  Genuine instance `type(SourceText('hello')).__basicsize__ == 24`. All exactly as §2.A claims.
- **pyo3 0.29 + abi3-py310** confirmed (Cargo.toml:24, Cargo.lock). `Py_tp_basicsize`
  (pyo3-ffi-0.29 slots_generated.rs:110) and `PyType_GetSlot` (object.rs:346) both exist.
  `__basicsize__` getattr path is valid. §2.A abi3 claim grounded.
- **Line citations accurate.** span.rs:444-453 (`_with_source_unchecked`), 433-443 (docstring),
  cross_cdylib.rs:63-116 (`extract_source_text`), 82-91 (cache-hit `cast_unchecked` bypassing
  `check_abi_pair`), 112 (`cast_unchecked`), 310-338 (`extract_span`), 321 (`is_instance`),
  257-297 / 270-285 (`span_to_pyobject`), Makefile:39/94-97/117-123 all verified.
- **Span non-subclassable** confirmed (span.rs:155, `pyclass(frozen, eq, hash, from_py_object)`,
  no `subclass`). §2.C reasoning sound.
- **Only non-test caller of `_with_source_unchecked` is `span_to_pyobject`** confirmed
  (grep: generated cst.rs routes through `span_to_pyobject`, never direct). §2 premise holds.
- No-API-rename / no-signature-change scope claim (§2.D) consistent with CLAUDE.md.

The design is unusually well-grounded and honest about its residual. Findings below are
about test-coverage tracking, a fragile test, and a couple of under-specified mechanics —
not about the core approach, which is sound.

---

## Findings

### design-1 — §4.3 omits the entire existing `_with_source_unchecked` direct-call test suite (the most likely thing to break)

Section: §4.3 "Existing tests preserved" — quote: "The full `TestSpanPathAbiGate` suite
(`test_rust_span.py:476-753`) must remain green ... so its seven scenarios are unaffected."

What's wrong: §4.3 names ONLY `TestSpanPathAbiGate` (the Span-path gate, which fires via
`get_span_type`→`check_abi_pair::<Span>`, NOT via `extract_source_text`). It entirely omits
the large pre-existing suite that calls `Span._with_source_unchecked(...)` *directly with
forged `FakeSource` objects* — exactly the code path the design modifies. These exist today at
`tests/test_rust_span.py`:
- 347 `test_with_source_unchecked_bogus_abi_marker_raises_type_error` (asserts `"ABI mismatch"`, `"FakeSource"`)
- 363 `test_with_source_unchecked_escape_in_type_name`
- 789 `test_source_text_abi_layout_mismatch_raises` (`FakeSource` layout=999999, asserts `"layout mismatch"`, `"999999"`)
- 803 `test_source_text_abi_layout_missing_raises` (asserts `"partial-upgrade"`)
- 815 `test_source_text_abi_layout_non_int_raises` (asserts `"not int"`)
- 827 `test_source_text_abi_string_missing_raises` (asserts `"SourceText ABI mismatch"`, `"pre-sentinel build"`)
- 399 `test_with_source_unchecked_foreign_cdylib_works` (genuine foreign — must stay accepting)

Why: These are pinned-message tests on the exact function (`extract_source_text`) the design
edits. Whether they stay green depends entirely on *check ordering* the design only implies
(§2.D: "apply the `tp_basicsize` gate ... before `cast_unchecked`" and "Keep `check_abi_pair`").
`FakeSource` objects above have no `__slots__`, so basicsize is 32 ≠ 24 — the new gate would
*also* reject them, but with a different message. If an implementer runs the basicsize gate
*before* `check_abi_pair`, every one of these pinned-message assertions (`"layout mismatch"`,
`"pre-sentinel build"`, `"not int"`, `"999999"`) flips to the basicsize-gate message and the
suite goes red.

Consequence: A design test plan that lists "existing tests preserved" but omits the suite most
exposed to the change gives the implementer no signal that check-ordering is load-bearing. The
likely outcome is ~6 broken pinned-message tests discovered only at `make check`, or a silent
weakening if the implementer "fixes" them by loosening the assertions. The blocker fix itself
would still work, but the regression surface the design claims to protect would be damaged.

Suggested fix: In §4.3, enumerate the direct-call suite (test_rust_span.py:~282-418, ~789-859)
and state explicitly that `check_abi_pair` must run *before* the basicsize gate so the existing
pinned diagnostic messages (`"ABI mismatch"`, `"layout mismatch"`, `"pre-sentinel build"`,
`"partial-upgrade"`, `"not int"`) continue to fire for those `FakeSource` inputs.

### design-2 — §4.1 `test_padded_forge_still_rejected_or_documented` proposes pinning a UB outcome as a contract

Section: §4.1 — quote: "this test pins the *current contract*: if the design adopts
basicsize-only (residual accepted), this test asserts the documented behavior (whatever it is)
so the residual is an explicit, tested contract".

What's wrong: The padded forge passes the basicsize gate and reaches `cast_unchecked` on memory
that is not a `PyStaticClassObject<SourceText>` — this is Undefined Behavior, which the design
itself states (§2.A "still UB if cast"). I verified live: `class ForgeSlots: __slots__=('x',)`
with the copied attrs and `f.x = 12345`, passed to `_with_source_unchecked`, currently returns
returncode 0 ("NO CRASH") — but this is UB, so the outcome is not stable across builds, allocator
state, or optimization levels. A test that asserts "whatever it is" on a UB path pins a
non-deterministic value.

Why: UB has no contract to pin. "Documented behavior (whatever it is)" for UB is a contradiction
— the next debug/release flip, pyo3 bump, or unrelated allocation change can turn the current
silent pass into a crash or corruption, flipping the test with no code change to this area.

Consequence: A test asserting a specific UB outcome is either flaky (fails spuriously on
unrelated changes) or, if written to assert "succeeds", actively lies — it tells future readers
the padded forge is a supported/safe input when it is UB. Either way it undermines the suite's
credibility for the one residual the design is being honest about.

Suggested fix: Do not assert the runtime outcome of the padded forge. Either (a) drop this test
and instead document the residual in the SAFETY comment + an xfail/skip with a clear note, or
(b) only assert that the basicsize gate *does not* raise for it (i.e. pin the gate boundary,
not the post-cast behavior), explicitly noting in the test that crossing that boundary is UB and
out-of-contract. This keeps the residual documented without pinning a UB value.

### design-3 — §2.C basicsize gate on `extract_span` is a near-tautology as described; the stated rationale doesn't hold

Section: §2.C — quote: "the basicsize gate helper should also guard the `extract_span`
`cast_unchecked`; this is cheap and removes a parallel latent hazard."

What's wrong: `extract_span`'s `cast_unchecked` (cross_cdylib.rs:331) is reached only after
`obj.is_instance(&native_span_type)?` passes (line 321), where `native_span_type` is the
*canonical* `fltk._native.Span` fetched by `get_span_type`. Because `Span` is non-subclassable,
anything that passes `is_instance` IS the canonical Span type, whose `__basicsize__` is by
construction equal to the local `size_of::<Span::Layout>()` *in the same process*. So the
proposed gate compares the canonical type's basicsize against the local size — a comparison that
can only fail under genuine cross-cdylib pyo3 layout skew, which `get_span_type`'s
`check_abi_pair::<Span>` (cross_cdylib.rs:362) already catches at first use. The new gate adds
essentially no rejection power on this path.

Why: The design markets §2.C as "removes a parallel latent hazard" / "defense-in-depth." But the
hazard it names (pure-Python forge reaching `extract_span`'s cast) is already fully blocked by
the `is_instance`-against-canonical check the design itself acknowledges (§2.C: "a pure-Python
forge fails it"). There is no forged object that reaches `extract_span`'s `cast_unchecked`, so
there is nothing for the basicsize gate to reject there beyond what `check_abi_pair::<Span>`
already does.

Consequence: Implementing §2.C as written adds code and a helper call to a path where it changes
no observable behavior — speculative generality on the hot span-read path, against the project's
"three similar lines beats premature abstraction" lean. Low harm, but it is scope the blocker
does not need and the design's own §2.C/OpenQ2 already flags as splittable. Recommend defaulting
to defer (OpenQ2's "minimal blocker fix") rather than presenting it as a clear win.

Suggested fix: Either drop §2.C from this change (the design already offers this as OpenQ2), or
restate its true value honestly: it is a consistency/uniform-helper measure, not a hazard
removal, because the only thing it can catch on the Span path (layout skew of the canonical
type) is already caught by `check_abi_pair::<Span>` in `get_span_type`.

### design-4 — `PyType_GetSlot(Py_tp_basicsize)` return-value handling is under-specified (the offered alternative is the trap, not the safe path)

Section: §2.A / §3 "abi3 portability" — quote: "Access it via
`obj.get_type().getattr("__basicsize__")` ... or `PyType_GetSlot(ty, Py_tp_basicsize)`; both are
abi3-safe."

What's wrong: The two access paths are presented as interchangeable, but `PyType_GetSlot`
returns `*mut c_void`. For `Py_tp_basicsize` the returned "pointer" is actually the
`Py_ssize_t` basicsize value reinterpreted as a pointer (a documented CPython quirk), so it must
be cast `ptr as isize`/`as usize`, not dereferenced. An implementer who treats it like a real
pointer (deref, or `is_null` gating) gets garbage. The design gives no guidance on this, and the
ffi path requires `unsafe`.

Why: The design's preferred `getattr("__basicsize__")` path is clean and safe and is what the
existing tests already use conceptually (test_rust_span.py:473 reads `_fltk_cst_core_abi_layout`
off `type(src)`). Offering the raw-ffi alternative as co-equal "both abi3-safe" invites an
implementer to pick the footgun without the cast/`unsafe` caveat being stated.

Consequence: If the implementer takes the `PyType_GetSlot` branch and mishandles the
ssize-as-pointer return, the gate reads a wrong size — either spuriously rejecting genuine
foreign `SourceText` (breaking the legitimate cross-cdylib path, the obligation in §Requirements
item 1 and `test_with_source_unchecked_foreign_cdylib_works`) or spuriously accepting (defeating
the gate). Both defeat the fix.

Suggested fix: Recommend the `getattr("__basicsize__")` path as primary (it returns a Python int,
extract to `usize`, surface read failure as `TypeError` per §3's exotic-type bullet), and either
drop the `PyType_GetSlot` alternative or annotate it with the "return is `Py_ssize_t` cast to
pointer, must be `as usize`, requires `unsafe`" caveat.

### design-5 — Requirement item 1 ("accept genuine SourceText from a different compiled copy") has no NEW test that actually exercises the basicsize gate's accept-branch cross-cdylib

Section: §4.2 — quote: "`test_genuine_foreign_source_text_still_accepted`: build a
consumer-fixture node with a source-bearing span, read `node.span`, assert the source survives".

What's wrong: The design's only new cross-cdylib non-regression test reads `node.span` (the
`span_to_pyobject` → `_with_source_unchecked` outward path). That is good, but it overlaps almost
exactly with the *existing* `test_source_bearing_span_reads_from_consumer_cdylib`
(test_rust_span.py:777) and `test_with_source_unchecked_foreign_cdylib_works`
(test_rust_span.py:399), neither of which the design acknowledges (see design-1). More
importantly, the binding obligation is that a genuine foreign `SourceText` *passes the new
basicsize gate*. None of these tests can distinguish "passed because basicsize matched" from
"passed because the gate was never reached / mis-ordered" — they only assert the end-to-end
source survives.

Why: The design adds a gate whose accept-branch correctness for cross-cdylib is the whole
"don't break the real use case" requirement. The proposed test asserts the *outcome* but not
that the *new gate specifically* admitted the genuine object — so a bug where the gate is
accidentally bypassed (e.g. cache-seeding §2.B admits before basicsize, or the gate is added on
the wrong branch) could still pass.

Consequence: Lower-severity than design-1/2 because the existing foreign-cdylib tests already
provide real coverage of the accept path end-to-end (so the requirement is not *un*tested). But
the design presents §4.2 as the guard "against the fix being too strict" while it largely
duplicates existing coverage and does not pin the new gate's behavior specifically. Risk: a
mis-placed or mis-ordered gate passes CI.

Suggested fix: Note that existing tests at test_rust_span.py:399/777 already cover the genuine
foreign accept path (reuse, don't duplicate). For the *new* gate specifically, add a focused
assertion that the foreign `SourceText`'s `__basicsize__` equals the native layout value (the
gate's precondition) so a future change to either side that breaks the equality is caught at the
gate, not only end-to-end.

### design-6 — §2.B cache-seeding fix is correct but the design doesn't note the existing cache-hit branch must also be re-derived, not just the seeding precondition

Section: §2.B — quote: "a type is offered to `get_or_init` only after passing the `tp_basicsize`
gate (§2.A) *in addition to* `check_abi_pair`. The cache-hit branch then stays sound — pointer
identity to a basicsize-validated type is genuine provenance."

What's wrong: The reasoning is sound *given* that nothing forged ever gets into the cell. The
design correctly makes basicsize a precondition for `get_or_init` (cross_cdylib.rs:97). But it
does not state that the cache-hit `cast_unchecked` branch (cross_cdylib.rs:82-91) is left
unchanged and relies entirely on the invariant "only basicsize-validated types are ever cached."
That invariant is only true if the basicsize gate is placed *before* the `get_or_init` call AND
the gate is never skipped on any path that can populate the cell. This is a correct but
delicate ordering constraint the design states only implicitly.

Why: The whole point of §2.B is to close the residual at exploration.md:211-214 (a forged type
seeding the cache, after which instances bypass even `check_abi_pair`). If an implementer places
the basicsize check after `get_or_init`, or only inside the cache-miss arm without making it a
precondition of seeding, a forged type that passes `check_abi_pair` (copied attrs, no slots →
basicsize 32) would *fail* basicsize so this particular forge can't seed — but the design's
own honest residual (padded slots forge, basicsize 24) *would* pass basicsize, seed the cache,
and then every later instance of that padded type hits the cache-hit `cast_unchecked` (UB).

Consequence: The cache-seeding residual is narrowed to exactly the same padded-forge residual as
the direct path (consistent with §2.A's honesty) — but only if seeding ordering is correct. If
ordering is wrong, the broader pre-fix residual (any `check_abi_pair`-passing forge seeds)
remains. The design should make the ordering invariant explicit so the implementer cannot get it
subtly wrong.

Suggested fix: In §2.B, state the invariant explicitly: "the basicsize gate must be evaluated
before `get_or_init` and must be the gating condition for seeding, so the cache cell can only
ever hold a basicsize-validated type; the cache-hit branch (82-91) is then left unchanged." Note
that the padded-forge residual extends to the cache path identically (it can seed), matching
§2.A — currently §2.B reads as if it closes the cache residual fully.

---

## Requirements coverage map

- Spec obligation 1 (gate rejecting pure-Python forge, accepting genuine foreign SourceText):
  covered by §2.A + §2.B. Accept-branch testing is thin/duplicative (design-5); reject-branch
  ordering vs existing pinned tests is unaddressed (design-1).
- Spec obligation 2 (subprocess-isolated regression test): covered by §4.1
  `test_forged_source_text_raises_type_error`. Sound. Padded-forge test is problematic (design-2).
- CLAUDE.md no-rename / no-annotation-churn: respected (§2.D, verified — no signature/name change).
