# Request: cst-generator-cleanup (combines 3 TODOs)

Style: concise, precise, no padding, no preamble. Audience: smart LLM/human.

**Type of work:** generator cleanup — all in `fltk/fegen/gsm2tree.py`. Three small, related changes to the CST/Protocol generators, bundled into one design+implementation so they don't conflict on the same file. Treat as three sub-tasks (A, B, C). They are independent enough that any one could be dropped, but they share the file and the per-label "quintet" emission machinery, so a single coherent design is wanted.

**CRITICAL — generated code is public API.** Generated CST/Protocol output is consumed by out-of-tree apps (see CLAUDE.md). Do not rename generated public symbols or churn the annotation surface beyond what each sub-task explicitly requires. Symbol *removal* (sub-task B) is a deliberate, called-out decision, justified below.

---

## Sub-task A — `protocol-label-member-private`: stop leaking `_ProtocolLabelMember`

**Problem.** `gen_protocol_module` (`gsm2tree.py:471-499`) emits a module-level class `_ProtocolLabelMember` into the generated public protocol module (e.g. `fltk_cst_protocol.py:57-77`). The generated module has no `__all__`, so the underscore-private helper is reachable by `from <mod> import *` and shows in IDE autocomplete — a de-facto-public leak of an internal.

**Fix shape (chosen): option (a) — emit `__all__`.** Add a module-level `__all__` to the generated protocol module listing only intended public symbols (all Protocol node classes, `NodeKind`, `Span`, `CstModule`), excluding `_ProtocolLabelMember`. Do NOT move the class to a new module (option b is rejected — it breaks the generated module's self-containment by adding a runtime import dependency every consumer inherits).

**Constraints.** Keep the generated module self-contained (no new imports). `__all__` must include `NodeKind`/`Span`/`CstModule` and every Protocol class but not `_ProtocolLabelMember`. `_ProtocolLabelMember` stays defined in-module (still importable by explicit name; only wildcard/autocomplete leakage is suppressed). `test_cst_protocol.py:113` currently lists `_ProtocolLabelMember` among expected module-level `ClassDef`s by AST scan — it still IS a ClassDef, so that scan is unaffected; verify.

---

## Sub-task B — `cst-protocol-label-free`: fix the Python *concrete* backend (REFRAMED — opposite direction from the original TODO)

**Problem.** For a *label-free* node — a rule whose only included items are `$`-disposition literals/regexes with no label prefix (e.g. `foo := $"x" , $"y";`; rule references auto-label, bare terminals suppress, so this is the only path) — three generated surfaces disagree:

| | `Label` class? | label-slot type | runtime value |
|---|---|---|---|
| Protocol (`_protocol_class_for_model`) | no (guarded `if labels:`) | `tuple[None, T]` | n/a |
| Rust backend (`gsm2tree_rs.py`) | no (`_label_enum_block` returns `""`) | opaque `None` | `None` |
| **Python concrete (`py_class_for_model`)** | **yes — an empty, memberless `enum.Enum`** | **`tuple[Optional[Label], T]`** | `None` |

The label slot is always `None` at runtime for label-free nodes (no `append_<label>` helpers exist). So the Protocol's `None` is the precise type and Rust agrees; the **Python concrete backend is the lone outlier** emitting a dead uninhabited `Label` enum and the imprecise `Optional[Label]` annotation. This is a genuine cross-backend divergence (CLAUDE.md load-bearing), and it means pure-Python-backend code can reference a vestigial `Foo.Label` that does not exist on the Rust backend — a drop-in-replacement hazard.

**The original TODO had the fix backwards** (it proposed adding a vacuous `Label` to the *Protocol*). Do the opposite: make the concrete backend match the already-correct Protocol + Rust behavior.

**Fix shape (chosen).** In `py_class_for_model` (`gsm2tree.py`, label/children emission ~202-247), add the same `if labels:` conditional the Protocol generator already has (`_protocol_class_for_model`, ~527-563): when the model has no labels, (1) do NOT emit the nested `Label` enum, and (2) emit `children: list[tuple[None, T]]`, `child() -> tuple[None, T]`, and `label: None = None` on `append`/`extend` — matching the Protocol. The Protocol generator and Rust generator are the reference; **neither needs changing.**

**Empirically validated (see `spike-label-free-pyright.md`, `spike-label-free-rust.md`):** after this change the concrete module passes pyright (0 errors), imports, and the label-free `children`/`child()` mismatch against the Protocol disappears. The only residual direct-structural pyright error is a pre-existing, label-independent cross-module `kind`/`NodeKind` nominal mismatch handled in production by the `cast(CstModule, ...)` boundary — **out of scope here, do not touch it.**

**Public-API note (deliberate, favorable).** This *removes* the generated `Foo.Label` symbol and *narrows* the label-free `children` annotation. Justified: the removed symbol is an empty, uninhabited, unreferenced enum, and the change makes the Python backend *match* the Rust backend, improving cross-backend drop-in compatibility. No in-tree grammar produces a label-free node, so in-tree churn is zero; only out-of-tree label-free grammars are affected, and favorably.

**Constraints.** Label-*bearing* nodes must be byte-identical before/after (only the zero-label branch changes). Mirror the Protocol generator's existing conditional exactly so the two stay in lockstep. Good TDD candidate: add a generator test that a zero-label rule (e.g. `foo := $"x" , $"y";`) yields a concrete class with NO `Label` and `tuple[None, T]`.

---

## Sub-task C — `cst-protocol-generator-refactor` (NARROW version only)

**Problem.** `py_class_for_model` and `_protocol_class_for_model` both emit the per-label "quintet" of accessors (`append_<l>`, `extend_<l>`, `children_<l>`, `child_<l>`, `maybe_<l>`) in parallel loops; adding/altering an accessor means editing both. The full unification of these two generators was triaged as **net-negative** (7+ structural divergences → an awkward multi-mode helper) and is explicitly REJECTED.

**Fix shape (chosen): narrow extraction only.** Extract *just* the shared per-label quintet-loop scaffolding into one helper that both generators call, parameterized by what legitimately differs (the per-method body emitter / annotations). Target ~40 lines saved. Do NOT attempt to unify the class-level structure, the Label-class emission, field declarations, base classes, or the annotation-resolver functions — those stay separate. If, while implementing, the extraction starts requiring more than ~2 strategy parameters or starts obscuring either call site, STOP and raise it as an open question rather than forcing it.

**Constraints.** Generated output (both concrete and Protocol modules) must be byte-identical before/after for all in-tree grammars — this is a pure refactor. Coordinate with sub-task B: B changes the zero-label branch of the concrete generator's quintet/field emission, so sequence B and C so the extracted helper reflects B's post-fix behavior (suggest: do B first, then extract C over the corrected code).

---

## Cross-cutting

**Load-bearing constraints (all sub-tasks).**
- Single file: `fltk/fegen/gsm2tree.py` (plus generated artifacts + tests). Rust generator (`gsm2tree_rs.py`) and the Protocol generator's existing conditionals are the *reference* — do not change their behavior.
- Regenerate all in-tree CST/Protocol artifacts and confirm: label-bearing nodes byte-identical (A, C); only label-free concrete nodes change (B); `__all__` added to protocol modules (A).
- After regen run `make fix` before committing (generated code isn't ruff-clean from the generator).

**Non-goals.** Full generator unification (C is narrow only). Any change to the Rust backend. Touching the pre-existing cross-module `kind`/`NodeKind` mismatch. Adding a vacuous `Label` to the Protocol (wrong direction).

**Verification.** `uv run pytest && uv run ruff check . && uv run pyright`; regenerate and diff in-tree artifacts per above; new generator tests for B (zero-label concrete shape) and A (`__all__` contents); C proven byte-identical. Remove `TODO.md` entries for all three slugs and the code comments: `TODO(cst-protocol-label-free)` (Protocol generator, ~556-561), `TODO(cst-protocol-generator-refactor)` (~399-401), and the `protocol-label-member-private` paragraph in the `_emit_protocol_label_member_class` docstring (`gsm2tree.py:443-445`). (The `protocol-label-member-bridge-unify` paragraph in that same docstring is being removed separately as a won't-do — leave whatever the current file state is.)

**Explorations in this dir:** `expl-protocol-label-member-private.md` (A), `expl-cst-protocol-label-free.md` + `expl-label-free-followup.md` + `spike-label-free-pyright.md` + `spike-label-free-rust.md` (B), `expl-cst-protocol-generator-refactor.md` (C).
