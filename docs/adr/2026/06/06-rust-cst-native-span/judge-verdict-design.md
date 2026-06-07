# Judge verdict — design review (rust-cst-native-span)

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Phase: design. Doc: `docs/adr/2026/06/06-rust-cst-native-span/design.md`. Base 6fd32e7. Round 1.
Notes: `notes-design-design-reviewer.md` (6 findings). Dispositions: `dispositions-design.md`.
Design phase → no added-TODOs walk; all findings walked below.

## Findings walk

### design-1 — Fixed
Claim: design treats children-getter mutation as having no in-repo consumer, but generated parsers/the parser generator mutate via the getter. Consequence: Rust-backend parse drops children silently; AC8/parse-path fail.
Verification: `fltk_parser.py:114,224,280,300,312,317,416,517` emit `result.children.extend(item.result.children)`; emitter `gsm2parser.py:497,501,715` (`...fld.children.method.extend.call(...children.move())`). Real and load-bearing.
Disposition: §2.3 rewritten — `children` getter no longer mutation-safe; `gsm2parser.py` brought in scope to route merging through node `extend`/`append` (native `Vec`); §5 "Won't-Do/no consumer" removed. Design §2.3/§3 reflect this.
Assessment: finding correct, fix addresses the consequence at the named surface. Accept.

### design-2 — Fixed
Claim: §2.6 `text_or_raise()` does not work under both backends; reads are child spans (not `node.span`); current Python-backend child spans are sourceless. Consequence: migration raises `ValueError` under Python backend immediately; not independent of parse-path stage.
Verification: `fltk2gsm.py:25-26,146-147,150-151` read `child_name()`/`child_value()` (child spans). `terminalsrc.py:38` `_source` defaults `None`; `:55-56` `text_or_raise()` raises "has no source". Both sub-claims true.
Disposition: §2.6 reframed as children-surface; staging "independent" claim removed; sourced child spans (parse-path §2.5) stated as prerequisite under BOTH backends; §4 item-7 made dependent. Design §2.5/§2.6/§5 consistent.
Assessment: finding correct, fix grounded and complete. Accept.

### design-3 — Fixed (premise rejected; residual applied)
Claim (reviewer): `src/cst_generated.rs`/`src/cst_fegen.rs` are hand-written; §2.8 regen won't reproduce them; they keep `PyObject` after regen → audit/grep gate fail.
Authoritative note + my verification: premise FALSE. Both files carry the generator's exact preamble (`UNKNOWN_SPAN_CACHE: GILOnceCell` + imports, byte-identical to known-generated `tests/rust_cst_fixture/src/cst.rs:1-9`). `Makefile:53-55` `gen-rust-cst` → `genparser.py:281` `RustCstGenerator(grammar).generate()`. Files are GENERATED.
Reviewer's consequence does not follow: "edit generator, regenerate" is the correct mechanism for all four files. Responder correctly rejected; reviewer's "hand-edit two files" remedy rejected on a false premise.
Residual (responder applied, valid): committed disk has drifted from HEAD's generator. Confirmed: generator emits the eq fast-path variable literally `other_kind` for all enums (`gsm2tree_rs.py:157`, shared template `_emit_rust_cross_backend_eq_hash`); committed `src/cst_generated.rs:87,333,834` show `other_label` in label-enum eq blocks → produced by an earlier generator. §2.8 amended to regen from grammars (not byte-equality to disk) with §4 item-2 grep gate as the correctness check.
Assessment: responder is right against the reviewer (source-backed), and the residual is real and correctly handled. Accept.

### design-4 — Fixed
Claim: `Py<ChildNode>` storage cannot satisfy the pure-Rust native-state acceptance (no `Python::with_gil`/init) since `Py<T>` needs a `Python` token; design punted to "user judgment." Consequence: central deliverable undefined for child nodes; §4 test-1 unwritable.
Verification: requirements §"Native node state" 2nd bullet is an acceptance criterion, not the `children-container-shape` open question. `Py<T>` construction requires a token — correct.
Disposition: §2.3 commits to native `Box<ChildNode>` enum as required representation; `Py<…>` only at binding boundary; identity concern moved to scoped TODO; §4 test-1 de-conditionalized. Design §2.3/§4 reflect this.
Assessment: finding correct, fix makes the acceptance satisfiable. Accept.

### design-5 — Fixed
Claim: adding `rlib` with default features pulls `pyo3/extension-module` transitively into a downstream pyo3 crate → double-activation; the given `fltk-native = { path = "../.." }` snippet IS the failure mode. Consequence: downstream link failure; hard build requirement blocked.
Verification: `Cargo.toml:8,11,12` (`crate-type=["cdylib"]`, `extension-module=["pyo3/extension-module"]`, `default=["extension-module"]`). `span.rs:66-68` fields `pub(crate)`; `with_source` is `#[pymethods]` (`:98-99,117`) not cross-crate callable. Correct.
Disposition: §2.1 adopts split `fltk-cst-core` rlib (no `extension-module`), downstream dep `default-features = false`; split costed up front. Design §2.1/§3 reflect this.
Assessment: finding correct, fix is the safe structure and matches the design-4/-6 native-core pressure. Accept.

### design-6 — Fixed
Claim: §2.4 asserts native equality recursion but doesn't define how native eq is invoked on `Py<ChildNode>` without GIL or Python `.eq()`. Consequence: equality either routes through Python `.eq()` (fails acceptance) or needs GIL (fails pure-Rust goal).
Verification: current `_eq_method` uses `self.children.bind(py).eq(...)`/`self.span.bind(py).eq(...)` (Python, GIL-bound) — matches `gsm2tree_rs.py` eq path. Correct.
Disposition: resolved via the same native-enum change as design-4 — structural `PartialEq` on the node enum in `fltk-cst-core`, no `Py<T>` borrow, no Python `.eq()`. Design §2.4 references the native `PartialEq`.
Assessment: finding correct; fix coherent with the shared root decision. Accept.

## Disputed items

None. All six dispositions source-backed and acceptable. design-3's Won't-Do-of-premise is the correct outcome (reviewer premise false per authoritative note + verified generator preamble/`make gen-rust-cst`); design-1/-2/-4/-5/-6 are real findings accepted as Fixed with grounded design rewrites unified around a single decision (native `Box<ChildNode>` enum, split `fltk-cst-core` crate, parser-generator routes mutation through node methods).

`TODO(rust-cst-child-node-identity)` (design-4 residual): tracks Python child-object identity stability, an opt-in boundary `Py` cache layered "only if a real consumer needs it." Not silent deferral of created breakage — value equality / `.kind` / `.text()` unaffected; native-state acceptance does not depend on it; "done" is checkable (identity test across getter calls). Acceptable for a design-phase TODO.

## Approved

6 findings: 5 real findings (design-1, -2, -4, -5, -6) Fixed-verified; 1 (design-3) premise correctly rejected with a valid residual correction applied.

---

## Verdict: APPROVED

All six dispositions acceptable. Every reviewer fact re-verified against source; design-3's false "hand-written" premise confirmed false (generator preamble byte-match + `make gen-rust-cst` → `RustCstGenerator`; authoritative note concurs), and the responder's residual drift correction (regen-from-grammar, grep-gate as correctness check) is sound.
