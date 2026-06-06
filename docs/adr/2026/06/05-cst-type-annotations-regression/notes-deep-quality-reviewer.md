Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

## quality-1

**File:line** `fltk/fegen/genparser.py:62`, `fltk/plumbing.py:148,176`, `fltk/unparse/genunparser.py:50`, `fltk/test_plumbing.py:581`

**Issue** `cast("cstp.GrammarNode", result.result)` repeated at five call sites. `result.result` is typed `Any` (`ParseResult.cst: Any | None`, `plumbing_types.py:30`). The cast is needed because `visit_grammar` now requires `cstp.GrammarNode` — but the root cause is that `ParseResult.cst` remains `Any`. The cast is a workaround scattered across callers rather than a fix at the source.

The fix belongs one level up: `ParseResult.cst` should be typed as `cstp.GrammarNode | None` (or generically `T | None`) so callers don't cast individually. Under `TYPE_CHECKING` the typed `cst` field costs nothing at runtime (the concrete value is unchanged). Alternatively, `Cst2Gsm.visit_grammar` could accept `Any` and cast internally (single site). Either way, five scattered boundary casts is the wrong shape.

**Consequence** Every future `result.result` → `visit_grammar` call site must independently remember to cast, and a missed site silently passes `Any`, bypassing the type checking the whole change is designed to enable. The pattern propagates: any new call site copies the cast incantation or silently regresses.

**Fix** Add a typed overload or annotation to `ParseResult.cst` — concretely, make it `cstp.GrammarNode | None` under `TYPE_CHECKING` via a `TYPE_CHECKING` branch in `plumbing_types.py`, or make `ParseResult` generic (`class ParseResult(Generic[T]): cst: T | None`). Collapse all five call-site casts.

---

## quality-2

**File:line** `fltk/fegen/gsm2tree.py:296-306` (`protocol_annotation_for_model_types`)

**Issue** Rule-reference node names are emitted as quoted strings (`'"RuleNode"'`), then the list is `sorted()`. Sorting mixes quoted rule-node names (alphabetically by their quoted string representation, starting with `"`) with unquoted library-type annotations (`fltk.fegen.pyrt.terminalsrc.Span`). This silently depends on ASCII sort order putting `"` before `f` — which happens to work today but is an implicit assumption rather than a deliberate ordering contract. More importantly, rule names are wrapped in quotes (`'"RuleNode"'`) because `from __future__ import annotations` is present in the emitted module (making all annotations strings), but Span-path annotations are *not* quoted — so the two kinds have different quoting rules baked into the generation with no enforcement.

**Consequence** If the library-type annotation path ever produces a name starting with `"` (e.g. a quoted forward ref), the sort conflates the two categories. More likely: a future reader of `protocol_annotation_for_model_types` sees the inconsistent quoting (rule refs quoted, Span refs not) without any comment explaining that this asymmetry is load-bearing, and "normalizes" it — breaking the generated module.

**Fix** Add a comment explaining the quoting asymmetry is intentional: rule refs are forward-referenced (Protocol classes defined later in the same module) so they require quotes under `from __future__ import annotations`, while library imports are resolved at parse time. Or, since `from __future__ import annotations` makes all annotations lazy anyway, drop the explicit quotes on rule names — they are redundant when `from __future__ import annotations` is present, and the asymmetry disappears.

---

## quality-3

**File:line** `fltk/fegen/gsm2tree.py:303` (`parts = sorted(parts)`)

**Issue** Sorting the union members of a child annotation is a semantic choice — it makes the generated `typing.Union[..., ...]` member order deterministic across dict-iteration, but it also means the order does not reflect the grammar's declared alternative order. `typing.Union` is order-insensitive for type checking, but the generated file's textual diff will change whenever a rule's alternatives change ordering, making regeneration noisier.

This is a minor issue on its own, but coupled with quality-2 (the sort silently mixes quoted and unquoted strings), the sort is doing two jobs — deduplication-stable ordering and quote-normalization side-effect — without being explicit about either.

**Consequence** Low: generates noisier diffs when union member sets change. Not a correctness issue. But the sort is doing hidden work (masking the quoting inconsistency) that makes future changes fragile.

**Fix** Use a stable deduplicated list (e.g. `list(dict.fromkeys(parts))`) if determinism is the goal; if alphabetical order is desired, document it explicitly. Separate the deduplication concern from the ordering concern.

---

## quality-4

**File:line** `fltk/fegen/gsm2tree.py:349,368,370` — `children` annotation and `child()` return type use `typing.Optional[Label]` for label-bearing nodes but `None` for label-free nodes.

**Issue** For label-free nodes (no labels at all), `children` is typed `list[tuple[None, <child_union>]]` and `child()` returns `tuple[None, <child_union>]`. This is technically correct — all labels are `None` for those nodes — but it means the Protocol's `children` type for label-free nodes is not `list[tuple[None | X, Y]]`; it is `list[tuple[None, Y]]`, which is a narrower type. The concrete `fltk_cst.py` dataclass for these nodes uses `Label | None` in practice even though it may be vacuously `None`. This creates a subtle asymmetry: label-bearing nodes use `Optional[Label]` (which includes `None`), label-free nodes hardcode `None`. Both are "correct" but the asymmetry means Protocol consumers who write generic code over all node types see two different `children` tuple-element shapes.

**Consequence** Any utility that tries to write generic code over arbitrary `CstModule`-node `children` tuples must case-split on whether the node has labels, which is unknowable from the Protocol type alone. Not a current problem (no such generic utility exists today), but as the Protocol is used more widely this will surprise users.

**Fix** Consistently use `Label | None` for all nodes (introducing a trivially-vacuous `Label` class with no members for label-free nodes, or using a module-level `_NoLabel = None` alias). This is optional and low-priority but worth noting before the pattern propagates.

---

## quality-5

**File:line** `fltk/fegen/genparser.py:199-208`

**Issue** The protocol file is written without the `newline="\n"` parameter to `open()`. The existing CST file write (`genparser.py:175-186`) also lacks it. On Windows this would produce `\r\n` line endings in the generated file, causing spurious diffs and `make check` failures. This is a pre-existing issue in the CST write that the new protocol write copies.

**Consequence** Portability bug propagates: any developer on Windows sees regenerated files with `\r\n` endings that differ from the committed `\n` versions, triggering `make check` failures unrelated to their change.

**Fix** Open the output files with `newline="\n"` (or use `pathlib.Path.write_text(..., newline="\n")`). Fix both the existing CST write and the new protocol write together.
