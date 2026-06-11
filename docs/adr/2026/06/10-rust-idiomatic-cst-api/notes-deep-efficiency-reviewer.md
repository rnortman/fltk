# Efficiency review — Phase 2 (idiomatic native CST surface)

Reviewed: 7e39dfb..fb8852f (HEAD fb8852f). Scope: Phase 2 only; Phase 3–4 absences excluded.
Style note: concise, precise, complete, unambiguous; audience smart LLM/human.

## efficiency-1: native `child_<lbl>` / `maybe_<lbl>` allocate a temporary `Vec` per call

- `fltk/fegen/gsm2tree_rs.py:1162,1181,1226,1246`; emitted into all five generated outputs
  (e.g. `src/cst_fegen.rs:362,383` — 64 `let matching: Vec<_>` sites in that file alone).
- For single-node-typed and span-typed labels, the emitted `child_<lbl>` and `maybe_<lbl>`
  bodies do `let matching: Vec<_> = self.children.iter().filter(...).collect();` solely to
  count and take the first element. The union-label branches of the **same generator function**
  already use the alloc-free shape: match on `(iter.next(), iter.next())`, recount with
  `.count()` only on the error path.
- **Consequence**: a heap allocation plus a full O(children) filter pass on every successful
  call, on the GIL-free data-struct API the design (§4.5) designates as the hot path for future
  generated Rust parsers and downstream Rust traversal. Cost is per-call and scales with node
  fan-out × call frequency. The `traverse` benchmark added this change does not exercise these
  paths (it only uses `children_<lbl>`, which is lazy and fine), so the cost is unmeasured by
  the §6 item 8 gate. The existing `rust-cst-accessor-clone-efficiency` TODO covers only the
  pymethod (handle) side — this new native-side allocation is untracked.
- Fix: emit the union-label shape for all three label kinds:
  `let mut it = self.children.iter().filter(...); match (it.next(), it.next())` —
  `(Some(..), None)` → type-check + `Ok`; anything else → recount only for the error.
  `maybe_<lbl>` analogously with a `(None, _)` arm. Success path becomes zero-alloc and
  short-circuits one element past the match instead of scanning all children into a Vec.

## efficiency-2: `extend_<lbl>` emits a per-item `push` loop instead of `Vec::extend`

- `fltk/fegen/gsm2tree_rs.py:1300–1340` (all three label-kind branches emit
  `for child in children { self.children.push(...) }`); mirrored in all generated outputs.
- The generic native `extend_children` in the same impl correctly uses
  `self.children.extend(other.children.iter().cloned())`, which pre-reserves via `size_hint`.
  The per-label bulk mutator forgoes the reserve and pays a capacity check per element.
- **Consequence**: incremental reallocations and per-element growth checks on the bulk
  child-append path — the API the future Rust parser (R4) is expected to use for sized inputs
  (Vec/slice iterators). Small constant today; pure waste, and the fix is a one-line emit change.
- Fix: emit
  `self.children.extend(children.into_iter().map(|c| (Some(Label::X), Enum::Variant(c.into()))));`
  (span/union analogs likewise).

## efficiency-3 (generator-time): class-name→rule-name reverse map rebuilt per node block

- `fltk/fegen/gsm2tree_rs.py:1086–1087`: `_native_per_label_methods` builds `rule_name_map`
  (dict comprehension over all `rule_models`) on every invocation — once per labeled rule —
  making this step O(rules²). The lookup is unnecessary: the caller `_node_block` already has
  `rule_name` in scope (used at line 620). Additionally `_label_type_info` (line 1054)
  recomputes `_child_variants_for_rule(rule_name)` once per **label**, duplicating the result
  `_node_block` computed at line 620 for the same rule.
- **Consequence**: regen-time only; negligible at current grammar sizes, quadratic ceiling on
  large grammars. Dead work either way.
- Fix: pass `rule_name` (and optionally the precomputed `(child_classes, has_span)`) from
  `_node_block` into `_native_per_label_methods` / `_label_type_info`; delete `rule_name_map`
  and the `rule_name is None` fallback at line ~1090 — which currently degrades to a guessed
  "assume multi-variant" `(f"&{enum_name}", None, 2)` on a lookup miss; passing the name
  directly removes that silently-wrong branch too.

No other findings. `CstError` is allocation-free (`&'static str` fields). `Span`'s manual
`Debug` elides source text (avoids formatting whole inputs) — correct call. `children_<lbl>`
iterators are lazy, zero-alloc. Generic `child()` matches on the slice without allocating.
Derived `Debug` on node structs recurses through `Shared` (whole-subtree formatting), but that
is inherent to `Debug` and design-acknowledged (§5 reference cycles). The criterion benchmark
uses `iter_batched` with an Arc-bump clone for setup — sound methodology; its gap (not covering
the allocating accessors) is noted under efficiency-1.
