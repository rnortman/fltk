# Judge verdict — design review

Concise. Precise. Source-backed. Audience: smart LLM/human.

Phase: design. Doc: `design.md` (vs `requirements.md`, `notes-design-design-reviewer.md`).
Round 1. 8 findings, all dispositioned Fixed. No added-TODOs walk (design phase; the two
TODOs are design-doc forward-reminders, judged under Other findings as design-8).

## Other findings walk

### design-1 — Fixed
Claim: AC5 as written (`test_fltk2gsm_against_rust_fegen_cst`, "run the real `fltk2gsm.py`")
is unachievable. `fltk2gsm.py:4` statically binds `from fltk.fegen import fltk_cst as cst`;
making `cst.*` resolve to the PyO3 classes needs either a re-export (out of scope, req
line 27) or a `fltk2gsm.py` edit (forbidden, req line 116). Consequence: the single binding
contract verification for the Rust backend (req lines 99, 131) goes undischarged.
Source verified: `fltk2gsm.py:4` static, no parameter/monkeypatch seam; consumer ops are
exactly `cst.Items.Label.NO_WS`, `children[::2]`, `children[1::2]`, `children[-1]`, tuple
unpack `sep_label, _ = children[0]`, `isinstance(item, cst.Item)` (fltk2gsm.py:36-66). PyO3
`fegen_cst.Item` ≠ dataclass `fltk_cst.Item` → `isinstance`/label `==` against the dataclass
module fail. Consequence real and central.
Fix present: design.md:514-534 reframes AC5 to `test_rust_fegen_cst_contract` — hand-written
test exercising every API-Contract op directly against `fltk._native.fegen_cst` instances,
never through `fltk2gsm.Cst2Gsm`, with explicit "Why not the real fltk2gsm.py" rationale.
AC7 sweep (544-550) uses the same op set. `TODO(rust-cst-fltk-reexport)` (594-606) records
the residual real-consumer gap.
Assessment: this is the reviewer's own suggested fix (i). The binding interface is the API
Contract (req line 116), fully exercised by the hand-written op set across all 14 classes /
12 items; the literal test vehicle is not binding. The forced scope narrowing (real consumer
not run on Rust) is not buried — it is stated with rationale and a logged TODO. Accept.

### design-2 — Fixed
Claim: AC2/AC3 require a non-FLTK importable `fltk._native.<submodule>` that does not exist;
design under-scopes it as a "test fixture" when it is committed Phase-4 build work (generated
`.rs` + manual lib.rs edit). Consequence: every Tier-2 AC silently degrades to skip-when-absent.
Source verified: lib.rs has only `cst_generated` (top-level, lib.rs:31) and `cst_fegen`
(submodule, lib.rs:35-49). No non-FLTK importable submodule. Consequence real.
Fix present: design.md:484-498 names the artifact as a committed deliverable —
`fltk/fegen/test_data/phase4_roundtrip.fltkg`, `src/phase4_roundtrip_cst.rs`,
`fltk._native.phase4_roundtrip_cst`, lib.rs wiring; CI wires before pytest; a CI lane that
skips every Tier-2 test is a failure signal (500-502).
Assessment: addresses the consequence. Accept.

### design-3 — Fixed
Claim: design cites "lib.rs:30-49" as the submodule pattern, conflating `cst_generated`
(top-level, NOT importable) with `cst_fegen` (importable submodule). Consequence: bug if
`cst_generated` is reused as fixture — `import_module("fltk._native.cst_generated")` fails.
Source verified: lib.rs:31 registers `cst_generated` on `m` directly; only lib.rs:35-49
builds the submodule with explicit `sys.modules` insert (lib.rs:42-44). Citation conflation real.
Fix present: design.md:54-62 "Template caveat — copy `fegen_cst`, not `cst_generated`",
corrected citation to lib.rs:35-49, explicit "Do not cite lib.rs:30-49".
Assessment: accurate, addresses the consequence. Accept.

### design-4 — Fixed
Claim (verification note): Rust path's `isinstance(obj, type)` filter drops module objects;
design justifies dropping `__builtins__` for the Python path but not why dropping modules on
the Rust path is safe. Consequence: low; future top-level non-class public name would diverge
silently between paths.
Source verified: parser_globals seed (plumbing.py:118-126) already supplies
`fltk`/`terminalsrc`/`typing`/`Span`/`Optional`; line 127 `update(cst_globals)` injects all
incl. `__builtins__`. Reasoning holds.
Fix present: design.md:228-239 "Contract: public's CST contribution ... is class names only",
pinning the intent for both paths. Accept.

### design-5 — Fixed
Claim: `_load_rust_cst_classes`'s `except Exception` masks real init-time bugs as "backend
unavailable". Consequence: low-to-moderate; misdirects debugging. AC4 needs only ImportError.
Source verified: AC4 (req line 60, design.md:295-300) requires hard-error on missing/unloadable
artifact; `ModuleNotFoundError` ⊂ `ImportError`; ABI mismatch surfaces as `ImportError`.
Fix present: design.md:247-254 `except ImportError as exc: ... from exc` with comment; Edge
Cases 420-427 updated, "broad except is deliberate" defense dropped. Accept.

### design-6 — Fixed
Claim: `make rust-cst` cannot turn a fresh grammar into a loadable submodule without the
manual lib.rs edit; target name implies a one-shot pipeline the targets don't deliver.
Consequence: moderate; implementer expects `make rust-cst GRAMMAR=new` to yield an importable
module and it won't.
Source verified: maturin compiles only what lib.rs mod-includes (design Option A/E); lib.rs
wiring is the manual step (design.md:151, 373-379). Consequence real.
Fix present: design.md:346-371 renamed `rebuild-native-wired`, "Deliberately NOT named
rust-cst" note, explicit 3-step new-grammar sequence; AC6 (535-543) states prerequisite
committed wiring and that the test verifies recompile-of-already-wired-tree. Accept.

### design-7 — Fixed
Claim (verification note): Rust path injects top-level `*_Label` aliases the Python path
nests; backends' `parser_globals` keys not identical. Consequence: low; benign (distinct,
unreferenced names).
Source verified by reviewer against gsm2tree_rs.py:142/466 (`{class_name}_Label` suffix),
referenced only via `#[classattr] Label`. Holds.
Fix present: design.md:404-409 "Backend-parity note" flags the inert asymmetry. Accept.

### design-8 — Fixed
Claim (process): `TODO(rust-cst-standalone-so)` needs the matching `TODO.md` entry per CLAUDE.md
two-piece convention; ensure the Option-B deferral maps to the same slug, not a second TODO.
Fix present: design.md:580-606 records both slugs (`rust-cst-standalone-so`,
`rust-cst-fltk-reexport`), maps the Option-B deferral to the same slug (592), and states the
dual-piece obligation (604-606).
TODO rubric (both are design-doc forward-reminders, legitimately deferred):
- `rust-cst-standalone-so`: Q1 yes (avoids full-crate rebuild per grammar). Q2 yes — Option B
  (generator change) or D (workspace restructure); out of Phase 4 scope per req line 29. → design-deferred, correct.
- `rust-cst-fltk-reexport`: Q1 yes (real-consumer verification). Q2 yes — needs a re-export
  seam + scope-boundary change (req line 27 out of scope). → design-deferred, correct.
Assessment: both pass the rubric as design-cycle-deferred; obligation recorded. Accept.

## Disputed items

None.

## Approved

8 findings: 8 Fixed verified (design-1 the binding AC5 reframe; design-2/3/6 build-mechanism
scoping; design-4/7 backend-parity contract notes; design-5 catch-narrowing; design-8 TODO
two-piece convention). Every disposition adopts the reviewer's own suggested fix; every
consequence source-confirmed; every edit present in design.md.

---

## Verdict: APPROVED

All 8 dispositions acceptable. Consequences real and source-backed; fixes present and address
them. design-1's reframe correctly discharges the binding API Contract (req line 116) via a
hand-written op set forced by the out-of-scope re-export (req 27) and fltk2gsm immutability
(req 116) constraints, with the residual real-consumer gap logged as TODO(rust-cst-fltk-reexport).
No scope-N pile; no fundamental disagreement.
