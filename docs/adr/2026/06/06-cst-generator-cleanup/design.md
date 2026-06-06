# Design: cst-generator-cleanup (sub-tasks A, B, C)

Concise. Precise. No padding. Audience: smart LLM/human. (Style note carried per author protocol.)

Scope: three independent-but-file-adjacent generator cleanups, all in
`fltk/fegen/gsm2tree.py`. Requirements are fixed by
`request.md`; this doc does not restate them, only the design. Where the request
is the spec, ambiguities are raised in Open Questions.

Sequencing (per request "Cross-cutting"): **B → C → A** for the code edits (do B
first so C extracts over corrected code; A is orthogonal and can land any time).
This doc presents them A/B/C for readability but the implementation order is B, C, A.

---

## Root cause / context

### Sub-task A — `_ProtocolLabelMember` leaks as public API

`gen_protocol_module` (`gsm2tree.py:471-499`) emits the helper sentinel class
`_ProtocolLabelMember` into every generated `*_cst_protocol.py` at module level
(`gsm2tree.py:488` → `_emit_protocol_label_member_class`, `:434-469`). The
generated module emits no `__all__` (confirmed: no `__all__` anywhere in
`gsm2tree`'s protocol-module emission, and none in the in-tree artifact
`fltk_cst_protocol.py`). With no `__all__`, the underscore-private helper is
pulled in by `from <mod> import *` and surfaces in IDE autocomplete. Generated
output is public API for out-of-tree consumers (CLAUDE.md), so this is a
de-facto-public leak of an internal. No in-tree code imports it by name; the only
references are the generated definition, the generator, and a test that lists it
as a module-level `ClassDef` (`test_cst_protocol.py:113`).

### Sub-task B — Python concrete backend is the lone label-free outlier

A **label-free node** is a rule whose only included items are `$`-disposition
literals/regexes with no label prefix (e.g. `foo := $"x" , $"y";`). This is the
*only* path to zero labels: rule references auto-label
(`fltk2gsm.py:94-96`), bare terminals default to SUPPRESS, and suppressed items
never reach `model.labels` (`gsm2tree.py:364-382`). No in-tree grammar produces
one (verified across all in-tree artifacts), but out-of-tree grammars can and do.

For a label-free node, three generated surfaces disagree on the label slot:

| surface | `Label` class? | slot type | runtime |
|---|---|---|---|
| Protocol (`_protocol_class_for_model`, `:553-583`) | no (`if labels:` guard) | `tuple[None, T]` | n/a |
| Rust (`gsm2tree_rs.py`, `_label_enum_block` returns `""`) | no | opaque `None` | `None` |
| **Python concrete (`py_class_for_model`, `:200-348`)** | **yes — empty memberless `enum.Enum`** | **`tuple[Optional[Label], T]`** | `None` |

The concrete generator emits the `Label` enum and `Optional[Label]`
unconditionally (`:202-212`, `:231`, `:243`, `:251`, `:257`) regardless of label
presence. The runtime label slot is always `None` for label-free nodes (no
`append_<label>` helpers exist; the generic `append` defaults `label=None`,
`:241-247`). So the Protocol's `None` is the precise type, Rust agrees, and the
concrete backend is the outlier: it emits a dead, uninhabited `Foo.Label` symbol
and an imprecise annotation. This is a genuine cross-backend divergence
(CLAUDE.md load-bearing) and a drop-in-replacement hazard — Python-backend code
can reference `Foo.Label`, which does not exist on the Rust backend.

The original `TODO(cst-protocol-label-free)` (`:556-561`) proposed the opposite
(add a vacuous `Label` to the Protocol). The exploration confirms that direction
is wrong: a `_NoLabel = None` alias is a no-op (`None | None = None`), and the
vacuous-Label-on-Protocol direction widens the already-correct Protocol toward
the broken concrete backend. The spikes (`spike-label-free-pyright.md`,
`spike-label-free-rust.md`) empirically validate making the concrete backend
match the Protocol/Rust reference instead.

### Sub-task C — parallel per-label "quintet" loops

`py_class_for_model` (`:273-345`) and `_protocol_class_for_model` (`:585-613`)
each emit the per-label quintet — `append_<l>`, `extend_<l>`, `children_<l>`,
`child_<l>`, `maybe_<l>` — in parallel `for label in labels:` loops. The loops
share structure (same five accessors, same order, same per-label annotation
inputs) but differ in method *bodies*: the concrete loop emits real bodies
(including the `typing.cast` in `children_<l>` when `len(model.types) > 1`,
`:297-306`), the Protocol loop emits `...` for every body. Adding or renaming an
accessor today requires editing both loops. The exploration
(`expl-cst-protocol-generator-refactor.md`) triaged full generator unification as
**net-negative** (7+ structural divergences in the class-level frame; an awkward
multi-mode helper) and the request **rejects** it. Only the quintet loop is a
clean extraction candidate (~40 lines).

---

## Proposed approach

All edits in `fltk/fegen/gsm2tree.py`. No change to `gsm2tree_rs.py` or to the
Protocol generator's existing label conditionals (those are the reference).

### A — emit `__all__` in the protocol module

In `gen_protocol_module` (`:471-499`), after the module body is fully built,
compute the public-symbol list and prepend an `__all__` assignment near the top
of the module body (after the imports / `from __future__` line). Public symbols:

- every Protocol node class name: `self.protocol_node_name(rule)` for
  `rule in self.rule_models`;
- `"NodeKind"`, `"Span"`, `"CstModule"`.

Excluded: `_ProtocolLabelMember` (and any future underscore helper). The class
**stays defined in-module** — `__all__` suppresses only wildcard/autocomplete
leakage; explicit `from <mod> import _ProtocolLabelMember` still works, and the
post-class sentinel assignments (`:515`) that reference it by bare name are
unaffected.

Emit via `pygen.stmt('__all__ = [...]')` with a **sorted** member list so output
is stable across regenerations and independent of grammar ordering. Build the
list from the same names the generator already computes, so it cannot drift from
the actual emitted classes.

Self-containment preserved: no new imports (option (b) — moving the class to a
new `pyrt.bridge` module — is rejected by the request; it would add a runtime
import dependency to every generated module and `pyrt.bridge` does not exist).

Interface touched: `gen_protocol_module` only. No signature changes.

### B — make the concrete generator match Protocol/Rust for label-free nodes

In `py_class_for_model` (`:200-271`), introduce the same `if labels:` conditional
the Protocol generator already uses, scoped to exactly the zero-label branch so
label-bearing emission is byte-identical:

1. **`Label` enum** (`:202-212`): emit only when `labels` is non-empty. When
   empty, emit no nested `Label` class and no `_emit_label_canonical_name_assignments`
   for it (the assignment loop already no-ops on empty `labels`, `:348`).
2. **`children` field** (`:230-233`): when label-free, emit
   `children: list[tuple[None, {child_annotation}]] = dataclasses.field(default_factory=list)`.
3. **`append` / `extend` `label` param** (`:243`, `:251`): when label-free,
   annotate `label: None = None` (mirror the Protocol's `label_annotation`
   pattern at `:563`).
4. **`child()` return** (`:257`): when label-free, `tuple[None, {child_annotation}]`.

The per-label quintet loop (`:273-345`) already no-ops on empty `labels` — no
change needed there beyond what C extracts.

Mirror the Protocol generator's existing branch *exactly* (same `label_annotation
= "typing.Optional[Label]" if labels else "None"` shape) so the two generators
stay in lockstep. The Protocol and Rust generators are the reference and are not
touched.

Public-API note (deliberate, favorable, per request): this removes the generated
`Foo.Label` symbol and narrows the label-free `children`/`child()`/`append`/
`extend` annotations from `Optional[Label]`/`Label`-bearing to `None`. Justified:
the removed symbol is an empty, uninhabited, unreferenced enum; the change makes
the Python backend match the Rust backend, improving drop-in compatibility. Zero
in-tree churn (no in-tree label-free node); out-of-tree label-free grammars are
affected favorably.

Out of scope (do not touch): the pre-existing cross-module `kind`/`NodeKind`
nominal mismatch (the spike's residual direct-structural pyright error), handled
in production by the `cast(CstModule, ...)` boundary.

### C — extract the shared quintet loop (narrow only)

After B lands, extract the parallel per-label loops into one helper, e.g.:

```
def _emit_label_quintet(
    self,
    *,
    class_name: str,
    labels: list[str],
    label_type_annotation: Callable[[str], str],
    body_for: Callable[[str, str, str], list[ast.stmt]] | <body-strategy>,
) -> list[ast.FunctionDef]:
```

The helper returns `list[ast.FunctionDef]` (pure; each caller appends into its own
class body) rather than mutating a passed-in body — this keeps it testable in
isolation and matches the return-a-list shape of `py_class_for_model`.

The helper owns what is identical across both generators: the `for label in
labels:` iteration, the five accessor names and their order, and the function
signatures' *shape* (parameter/return annotation slots filled from the per-label
annotation). It is parameterized by what legitimately differs:

- the per-label child annotation resolver (`py_annotation_for_model_types` with
  `in_module=True` precomputed into `child_annotation_by_labels` for the concrete
  side; `protocol_annotation_for_model_types` for the Protocol side);
- the **method-body emitter**: concrete bodies (real statements, including the
  `children_<l>` `typing.cast` when `len(model.types) > 1`) vs Protocol bodies
  (all `...`).

Both `py_class_for_model` and `_protocol_class_for_model` call the helper and
append the returned function defs into their class bodies. The class-level frame
(outer class, `Label` class, `kind`/`span`/`children` fields, base classes,
annotation-resolver functions, post-class assignments) stays separate in each
generator — explicitly NOT unified.

Guardrail (per request): if the extraction starts requiring more than ~2 strategy
parameters, or starts obscuring either call site, STOP and raise it as an open
question rather than forcing it. Target ~40 lines saved.

Constraint: generated output (both modules) byte-identical before/after for all
in-tree grammars — pure refactor. Because C runs after B, the extracted helper
reflects B's corrected zero-label behavior (for label-free nodes the loop
produces zero functions on both sides, so the helper is exercised only on
label-bearing nodes — byte-identity is on the label-bearing path).

### Cleanup (all three)

- Remove `TODO.md` entries: `cst-protocol-label-free`, `cst-protocol-generator-refactor`,
  `protocol-label-member-private`.
- Remove code comments: `TODO(cst-protocol-label-free)` (`:556-561`),
  `TODO(cst-protocol-generator-refactor)` (`:399-401`), and the
  `protocol-label-member-private` paragraph in the `_emit_protocol_label_member_class`
  docstring (`:443-445`).
- Leave the `protocol-label-member-bridge-unify` TODO and its docstring paragraph
  (`:447-449`, `TODO.md:71-73`) as-is — separate won't-do, not in this scope.
- Regenerate all in-tree CST/Protocol artifacts, then run `make fix` before commit
  (generated code is not ruff-clean from the generator, by design).

---

## Edge cases / failure modes

- **A — name drift.** If `__all__` is hand-listed it could fall out of sync with
  emitted classes. Mitigation: build `__all__` from the same `rule_models`
  iteration the class emission uses, plus the three fixed names — single source.
- **A — `__all__` ordering nondeterminism.** Set/dict iteration could reorder
  across runs. Mitigation: emit in a deterministic order (rule order or sorted).
- **A — test at `test_cst_protocol.py:113`.** The test scans `ast.ClassDef`
  nodes; `_ProtocolLabelMember` is still a `ClassDef`, so the scan is unaffected
  (request says "verify"). The new `__all__` is an `ast.Assign`, not a
  `ClassDef`, so `class_defs` is unchanged. Confirm the suite passes; no edit
  expected.
- **B — empty enum currently passes pyright.** The dead enum is legal today
  (spike: 0 errors); removing it cannot regress the concrete module — spike
  confirms the post-fix module passes pyright and imports.
- **B — label-bearing regression risk.** The change must be gated strictly on
  `if labels:`. A new generator test (below) plus byte-diff of in-tree
  label-bearing artifacts catches any leakage into the label-bearing path.
- **B — `list` invariance.** `list[tuple[None, T]]` is not a subtype of
  `list[tuple[Optional[Label], T]]`. This is the intended narrowing; out-of-tree
  callers annotating label-free `children` as `Optional[Label]` must update. This
  is the deliberate, called-out public-API change.
- **C — non-byte-identical output.** The refactor could subtly reorder or alter
  emitted accessors. Mitigation: diff in-tree concrete and Protocol artifacts;
  require zero diff on label-bearing nodes. If the helper can't achieve
  byte-identity within ~2 strategy params, escalate per guardrail.
- **C / B sequencing.** Doing C before B would extract over the buggy zero-label
  concrete code and force a re-extraction after B. Enforced order: B then C.

---

## Test plan

After this work the following tests exist (generator-level, AST-based, matching
the existing `test_cst_protocol.py` style):

- **A — `__all__` contents.** New test: `gen_protocol_module()` produces a
  module-level `__all__` whose members equal {all Protocol node names, `NodeKind`,
  `Span`, `CstModule`} and exclude `_ProtocolLabelMember`. Assert by locating the
  `ast.Assign` to `__all__` and parsing its list literal.
- **A — leak suppression (optional, stronger).** Assert `_ProtocolLabelMember`
  is NOT in `__all__` while still present as a `ClassDef` (still importable by
  name).
- **A — existing scan unaffected.** `test_protocol_module_has_one_class_per_rule`
  (`:100-114`) continues to pass unchanged (`_ProtocolLabelMember` still a
  `ClassDef`).
- **B — label-free concrete shape.** New TDD test: build a generator over a
  grammar with a zero-label rule (`foo := $"x" , $"y";`), call
  `py_class_for_model`, assert the emitted class has **no** nested `Label`
  `ClassDef`, `children` annotated `list[tuple[None, T]]`, `child()` returning
  `tuple[None, T]`, and `append`/`extend` `label: None = None`.
- **B — label-bearing unchanged.** Assert a label-bearing rule still emits the
  `Label` enum and `Optional[Label]` (guards against the conditional leaking).
- **C — byte-identity.** Regenerate in-tree concrete and Protocol artifacts and
  assert zero diff against committed artifacts for all label-bearing nodes (the
  pure-refactor proof). Existing `test_protocol_node_has_required_members`
  (`:117-154`) continues to assert the full quintet is present per label.
- **Whole-suite + static checks:** `uv run pytest && uv run ruff check . &&
  uv run pyright` green after regen + `make fix`.

---

## Open questions

None blocking. One implementation-time escalation point (not a user-judgment
call): per the request guardrail, if C's quintet extraction cannot stay within
~2 strategy parameters and readable call sites, stop and surface it rather than
forcing the abstraction.
