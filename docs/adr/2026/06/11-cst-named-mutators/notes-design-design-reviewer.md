# Design review findings: cst-named-mutators

Style: concise, precise, complete, unambiguous. No padding. All docs in this workflow follow this style.

Verified against source at base 7ddec4a. Claims checked and confirmed accurate (not findings): `_RESERVED_LABELS` at `gsm2tree_rs.py:24-26`; `_children_getter` at 875; `_generic_child` wiring point at 790; `generate_pyi` at 127 with `_pyi_annotation_for_model_types` machinery; `_span_getter_setter` lock-discipline comments at 836-851; `_label_from_pyobject_match` error texts (`gsm2tree_rs.py:934, 948-949`) and `extract_from_pyobject` child-type text (597) quoted verbatim-correctly; native `push_child`/`extend_children`/`append_<lbl>`/`extend_<lbl>` exist in the plain impl; registry functions `get_or_insert_with`/`register_if_absent`/`force_register` exist and the registry is a weak-valued `WeakValueDictionary` keyed by arc address (`registry.rs:32-34, 50-106`); `gsm2tree.py` refs (children field 258-260, append/extend 268-290, `child_fn` appended at 306, `_protocol_class_for_model` at 623, TYPE_CHECKING guard 179-200); `TODO.md:23` entry exists; collision reasoning holds (all per-label names are `append_`/`extend_`/`children_`/`child_`/`maybe_`-prefixed on both surfaces; no prefix can produce `insert`, `remove_at`, `replace_at`, `clear`, `insert_child`, `remove_child`, `replace_child`, or `clear_children`); all test files named in §4 exist.

## design-1: §2.6 regenerated-artifact list is incomplete

Quote: "Regenerated committed artifacts (regen → `make fix` → commit, per CLAUDE.md): `fltk/fegen/fltk_cst.py`, `fltk/fegen/fltk_cst_protocol.py`, `src/cst_fegen.rs`, `fltk/_native/fegen_cst.pyi`, `tests/rust_cst_fixture/src/cst.rs`."

What's wrong: `gsm2tree.py` and `gsm2tree_rs.py` changes affect every generated CST module, not just the five listed. The `gencode` Makefile target (Makefile:147-186) also regenerates: Python CST + protocol for bootstrap (`fltk/fegen/bootstrap_cst.py`, `bootstrap_cst_protocol.py`), toy (`fltk/unparse/toy_cst.py`, `toy_cst_protocol.py`), and unparsefmt (`fltk/unparse/unparsefmt_cst.py`, `unparsefmt_cst_protocol.py`); Rust CST for `src/cst_generated.rs` (PoC grammar), `tests/rust_cst_fegen/src/cst.rs` (Makefile:178 — "must match src/cst_fegen.rs"), `tests/rust_parser_fixture/src/cst.rs` (Makefile:182), and `crates/fltk-cst-spike/src/cst.rs` (cp of cst_generated.rs, Makefile:185).

Consequence: an implementer who regenerates only the listed files commits drift between the generators and ~8 committed artifacts. `make check` cheat-detection (regen-then-diff) and the rust_cst_fegen staleness check fail; if the implementer instead "fixes" by hand-editing, generated code diverges from generator output.

Suggested fix: replace the explicit list with "run `make gencode`; all generated CST/protocol/pyi artifacts it covers change" and cite the Makefile target, or enumerate the full set.

## design-2: span-type acceptance is asymmetric; "Mirror of Rust behavior" claim is inaccurate

Quote (§2.2): "Span types are resolved lazily — `terminalsrc.Span` always; `fltk._native.Span` only via `sys.modules.get(...)` ... Mirror of Rust behavior: each backend accepts its own node classes and rejects the other backend's."

What's wrong: under this design the Python backend accepts BOTH span types, but Rust accepts only native spans. `extract_span` (`crates/fltk-cst-core/src/cross_cdylib.rs:256-281`) succeeds only for the local `Span` pyclass or a cross-cdylib `fltk._native.Span`; a pure-Python `terminalsrc.Span` falls through `extract_from_pyobject`'s span branch (`gsm2tree_rs.py:575`) to the generic `"{ClassName}: unsupported child type Span"` TypeError. So for the input "the other backend's span type", the backends diverge: Python accepts, Rust raises TypeError. The asymmetry is forced by representation (Rust stores a native `Span` struct; Python trees legitimately hold native spans because the `pyrt.span` backend-selector can select `fltk._native.Span`), but the design presents the validation rule as symmetric and never states the divergence.

Consequence: request "Verification expectations" requires identical error cases cross-backend; a parity-test author following §2.2's "mirror" framing will write a shared rejects-foreign-span test that fails on the Python backend — or the divergence ships undocumented in new public API whose §2.2 selling point is pinned exact-parity behavior.

Suggested fix: state explicitly that span acceptance is asymmetric (Python: both span types; Rust: native only), justify via the backend-selector, and exclude cross-backend span hand-in from the exact-parity test matrix.

## design-3: accepted i64-overflow divergence contradicts the request's "must match" index requirement

Quote (§3): "Indices beyond `i64`: Rust extraction raises `OverflowError`; Python clamps (`insert`) or raises `IndexError`. Documented, deliberately untested divergence."

What's wrong: request.md "Fix shape" — "Index semantics (negative indices? out-of-range errors) must match between backends and be pinned by shared tests." The design resolves this as an accepted divergence (§5: "i64 index-overflow divergence accepted") rather than surfacing it as a deviation from a stated requirement. A cheap conforming alternative exists: accept the index as `&Bound<PyAny>`, try `extract::<i64>()`, and on overflow clamp by sign (insert) / raise the same IndexError (remove_at/replace_at).

Consequence: exception type differs cross-backend (`OverflowError` vs `IndexError`/silent clamp) for the same operation sequence, violating the letter of the requirement; downstream code catching `IndexError` portably breaks on Rust for this edge. Practically negligible (no tree has 2^63 children), but it is a requirements deviation presented as a settled judgment call — the judge/requirements owner should ratify it, not inherit it.

## design-4: §4.3 GC-sanity test cannot fail — it does not exercise `clear()` at all

Quote (§4.3): "GC sanity: after `clear()` with no surviving Python references, a weakref to a former child handle dies (registry self-eviction)."

What's wrong: the registry is weak-valued (`registry.rs:32-34`); the parent's `Arc` keeps the child's *data* alive, never its Python *handle*. A handle with no strong Python references is collected — and its weakref dies — whether or not `clear()` was called. The test as specified passes identically with `clear()` deleted, so it pins nothing about the §2.5 removal/registry interaction it is meant to verify.

Consequence: false confidence in the §2.5 "no new corruption pathway" claim; the property actually worth observing (after `clear()` + handle drop, the registry entry is gone and the node data is freed) is untested.

Suggested fix: assert via `registry::snapshot` (exposed, `registry.rs:137`) that the child's entry is absent after `clear()` + handle drop; or drop the test item.

No other findings. Requirements coverage is otherwise complete: naming rationale (§2.1), collision verification (§2.1), lock invariant (§2.3), native-mutator decision (§2.3), registry/identity analysis (§2.5) and identity tests (§4.3), cross-backend parity tests (§4.2), suite gates (§4.5) all map to request items; internal consistency holds elsewhere; scope is disciplined (no proxy, no getter-semantics change, old append/extend untouched).
