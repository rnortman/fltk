# Judge verdict — interim review (rust-cst-native-span), round 2

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Phase: interim (intermediate; project deliberately unfinished — defer-as-TODO for not-yet-implemented design sections is acceptable). Base 6fd32e7..HEAD f8fdb53. Round 2 — APPROVED or ESCALATE only.
Rework commit: 622976c ("surface span-getter source-loss and parse-path regression with real TODOs + xfail"); 16 round-1-accepted findings not re-walked.
Round-1 verdict: REWORK on exactly two items — both the same lazy-responder failure (dispositioned `TODO(slug)` where the slug existed in neither `TODO.md` nor any code comment), with a legitimate underlying deferral that was merely unsurfaced.

## Disputed items (round 1) — re-walk

### errhandling-3 / quality-2 — TODO(rust-cst-span-getter-source-loss) [was: fabricated slug]
Round-1 fault: slug present only in `dispositions-interim.md`; no `TODO.md` entry, no code comment; surface worsened vs base (base returned the stored span object source-intact; new getter reconstructs `Span(start,end)` sourceless).
Remedy required: real TODO pair (entry + comment) OR the mechanical fix.
Verification of join key:
- `TODO.md:47` — `## rust-cst-span-getter-source-loss`, well-formed: states the worsened-vs-base fact, the consumer-visible consequence (`.text()`/`.has_source()` silently return None/False), the fix path (`pub fn source_text` + `with_source` on present source), the §2.5 prerequisite, and the location.
- Generator-source comment present at both emit sites the finding names: `gsm2tree_rs.py:384` (`_child_enum_block` `to_pyobject` Span arm) and `:518` (`_span_getter_setter` getter). Regenerated into all four `.rs` files.
Assessment: join key intact at both code sites + TODO.md. Deferral now visibly tracked, not silent. Rubric Q1 yes / Q2 (per round-1 walk) the fix is mechanical but the §2.5 prerequisite means it is correctly sequenced under the incremental USER DECISION (design §5). Remedy (b) applied in full. **Resolved.**

### checkpoint-correctness-1 — TODO(rust-cst-parse-path-native-span) [was: fabricated slug + silent red]
Round-1 fault: slug `backend-with-source-signature continuation` existed nowhere (the `backend-with-source-signature` TODO was removed in increment 5); AC9 `test_fltk2gsm_behavioral_equivalence` was live-red on the Rust arm with no xfail; Rust parse path is a regression this iteration created (strict setter now rejects `terminalsrc.Span`).
Remedy required (checkpoint reviewer's sanctioned form): mark the Rust arm `xfail` referencing a real TODO (entry + comment).
Verification:
- `TODO.md:51` — `## rust-cst-parse-path-native-span`, well-formed: states the regression (parser emits `terminalsrc.Span`; strict setter raises `TypeError`), the consequence (Rust backend cannot parse any input), the fix path (§2.5 parse-path source work), and the location.
- `test_clean_protocol_consumer_api.py:335` — `@pytest.mark.xfail(strict=True)` on `test_fltk2gsm_behavioral_equivalence` referencing the real slug. Five further `TestCrossBackendDualShapeDispatch` methods that depend on the `rust_items` fixture (previously ERRORing) given the same `strict=True` xfail; fixture docstring carries the slug (`:566`).
- Suite run (this review, post-`maturin develop`): `47 passed, 6 xfailed` — no errors, no silent reds. `strict=True` means any of these silently starting to pass becomes a hard failure, so the deferral self-unwinds when §2.5 lands.
Assessment: regression now surfaced exactly as the checkpoint reviewer prescribed. Deferral legitimate under the incremental USER DECISION; surfacing complete. **Resolved.**

## Approved

Round-1: 16 findings accepted (11 Fixed verified, 3 Won't-Do sound, 2 TODOs acceptable). Round-2: both round-1 disputed items resolved via real TODO pairs + strict xfail. No new dispositions introduced (HEAD diff vs a320715 is the rework: TODO.md +8, gsm2tree_rs.py +6, four regenerated `.rs`, the xfail markers, and the dispositions doc). Build clean; AC test file green (47 passed / 6 xfailed).

---

## Verdict: APPROVED

Both — and only — round-1 disputed items are fully remediated. Each fabricated slug is replaced by a real join key: a well-formed `TODO.md` entry plus `TODO(slug)` comments at the exact code sites the findings name (regenerated into all four `.rs` files), and the parse-path regression is surfaced via `strict=True` xfail on the AC9 test and five dependent tests. No silent red remains (47 passed, 6 xfailed, 0 errors). The deferrals themselves were already legitimate under the incremental USER DECISION (design §5); only their surfacing was missing in round 1, and it is now present. No remaining wrong disposition.
