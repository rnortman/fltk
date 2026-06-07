# Correctness checkpoint notes — Rust CST native span/children

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Scope: commits 60f5c3f..f2bf59b (base 6fd32e7, HEAD f2bf59b). Increments 1–4
(§2.1 split crate, §2.2 native span field, §2.3 native children/child enum,
§2.5-partial gsm2parser child-mutation + extend_children).

State verified this session:
- `maturin develop` (root) + `tests/rust_cst_fegen` fixture rebuild from current
  generator: both succeed (warnings only — unreachable `_ => false` arms in
  single-variant child enums; benign).
- Directly relevant Python tests pass: `tests/test_gsm2tree_rs.py`,
  `tests/test_rust_cst_poc.py`, `tests/test_fegen_rust_cst.py` (275 passed).
- Full `uv run pytest`: 1 failed, 399 passed (run `-x`). The one failure is
  `correctness-1` below; reproduced after a fresh `fegen_rust_cst` rebuild, so not
  a stale-artifact artifact.

---

## correctness-1 — Rust-backend fegen parse path regressed: span setter rejects the span the parser produces

File: `fltk/fegen/gsm2tree_rs.py:495-518` (span getter/setter, `extract_span`
preamble `:153-179`) vs `fltk/fegen/gsm2parser.py` (still constructs
`fltk.fegen.pyrt.terminalsrc.Span` for `node.span`, e.g. via `TerminalSpanType`
at `:475-480, :514-521`).

What's wrong: Increment 2 (§2.2) changed the generated node `span` field from
`#[pyo3(get, set)] span: PyObject` (base 6fd32e7, `gsm2tree_rs.py:290-291` —
accepts *any* Python object) to a native `span: Span` with a strict `#[setter]`
that routes through `extract_span()`. `extract_span()` accepts only a native
`fltk._native.Span` (fast-path local-cdylib `extract::<Span>()`, or slow-path
`isinstance` against the imported `fltk._native.Span` type). It rejects a Python
`fltk.fegen.pyrt.terminalsrc.Span`. The parser generator was NOT updated to emit
native spans (§2.5 source-bearing parse path is deferred — implementation-log
increment 4 confirms `span.py:14` still `SourceText = None`). So generated parsers
still execute `result.span = terminalsrc.Span(...)`, which the new setter rejects.

Why: trace — `parse_grammar(..., rust_fegen_cst_module="fegen_rust_cst")` →
parser constructs each node with `span=Construct(TerminalSpanType, ...)` →
node `__new__`/`set_span` calls `extract_span(py, terminalsrc.Span)` →
`extract::<Span>()` fails (different type) and `isinstance(obj,
fltk._native.Span)` is false (a `terminalsrc.Span` is not a native Span) →
`PyTypeError::new_err("expected fltk._native.Span, got Span")`.

Consequence: parsing ANY input with the Rust CST backend (the
`rust_fegen_cst_module`/`rust_cst_module` path) raises `TypeError` at the first
node construction. `tests/test_clean_protocol_consumer_api.py::test_fltk2gsm_behavioral_equivalence`
(AC9, both-backend equivalence) fails. This is a *regression relative to base
6fd32e7*: at base, `span: PyObject` accepted `terminalsrc.Span`, so the
Rust-backend parse path worked. The increment-2 log labels this class of failure
"pre-existing failures (parse-path tests, fegen rust backend) unchanged" — that
characterization is inaccurate for the setter-induced break: increment 2 newly
*tightened* the setter while the parser still feeds it the old type. The break is
internally consistent with the design's deferral of §2.5 (and the USER DECISION
allowing incremental sequencing), but it is a live regression, not a no-op
deferral: the Rust backend cannot parse until §2.5 lands. If stages 1–2 are meant
to be independently shippable, the design's own gate ("fltk2gsm stays
Python-backend-only until stage 3") is violated by leaving an AC9 test that
exercises the Rust backend in the suite and red.

Suggested fix: land §2.5 (parser emits `fltk._native.Span` / `Span.with_source`
under the Rust backend, gated by `backend-with-source-signature`) before relying
on the Rust parse path; OR, until then, mark `test_fltk2gsm_behavioral_equivalence`'s
Rust-backend arm xfail with a `TODO(backend-with-source-signature)` reference so
the suite reflects the documented deferral rather than a silent red. No
code-logic fix to the increments themselves is implied — the setter tightening is
correct per §2.2; the gap is the un-migrated parser generator.

---

## correctness-2 — generic `append`/`extend` silently drop an unrecognized label (cross-backend divergence)

File: `fltk/fegen/gsm2tree_rs.py:589-607` (`_label_from_pyobject_match`), used by
`_generic_append` (`:569-587`) and `_generic_extend` (`:609-636`).

What's wrong: the native label-coercion match does
`if let Ok(native_lbl) = lbl.bind(py).extract::<<Name>_Label>() { Some(..) } else
{ None }`. When the caller passes a label object the node's native label enum
cannot extract, the arm falls through to `None` — the label is silently dropped
and the child is stored as unlabeled. The Python backend
(`gsm2tree.py:239-253`) stores whatever label object was passed verbatim
(`self.children.append((label, child))`), so the stored `(label, child)` pair
differs across backends for the same call.

Why: data-flow — a non-extractable `label: Option<PyObject>` → `None` →
`children.push((None, child))`. Equality (`children_<label>`/`child_<label>`
filter by native enum `==`) then never matches; the child becomes invisible to
its intended label accessor under the Rust backend but visible under Python.

Consequence: an out-of-tree consumer calling the *generic* `node.append(child,
label=...)` / `node.extend(children, label=...)` with a label value that does not
round-trip to the node's native label enum (e.g. a wrong-rule label, or a label
passed as a bare string/int) gets divergent behavior: Python backend stores and
later filters on it; Rust backend silently un-labels it. Violates the
cross-backend behavioral-equivalence requirement (§"Behavioral equivalence",
child-accessor results). Not exercised by generated parsers (they use
`append_<label>` / `append` / `extend_children` exclusively — verified by grep
over `fltk_parser.py`), so no in-tree test catches it; it is a latent public-API
divergence. The §3 edge-case design text says a child type not in the rule's
model "must fail loudly"; the analogous unrecognized-*label* case instead fails
silently.

Suggested fix: in the `Some(lbl)` arm, on extraction failure raise
`PyTypeError` naming the rule and the expected label enum, mirroring
`extract_from_pyobject`'s child-type error path, rather than coercing to `None`.

---

## Items checked, no finding

- §2.5 child-mutation rewrite (`gsm2parser.py:495-500, :709-713`): both
  `inline_to_parent` sites pass `other=...result.move()` to `extend_children`,
  whose param type is the parent node type. Verified type-consistent: both inline
  sites build the sub-result with `result_type = node_type` (the parent's type) —
  `gen_subexpression_parser` `:460,:467` and `gen_alternatives_parser` `:624,:627`.
  No type mismatch; `extend_children(other: PyRef<ClassName>)` matches.
- `extend_children` (`gsm2tree_rs.py:638-653`, Python `gsm2tree.py:255-261`):
  copies `(label, child)` preserving labels via native clone; equivalent to the
  Python `self.children.extend(other.children)`. Old getter-mutation drop-bug
  (rebuilt throwaway PyList) is genuinely fixed.
- `child_<label>` / `maybe_<label>` count loops (`:749-813`): early `break` at
  `count==2` leaves `found` = first match; `child_` then errors on `count != 1`,
  `maybe_` errors on `count > 1`. Off-by-one / control flow correct.
- `_eq_method` (`:817-829`): native structural equality (`self == &*other_node`)
  via derived/manual `PartialEq` on node + child enum + `Span`; no Python `.eq()`
  on stored state. `NotImplemented` for non-matching type. Correct.
- Span `PartialEq`/`Hash` (`crates/fltk-cst-core/src/span.rs:80-93`): value
  equality on `(start, end)` only; sentinel == source-bearing at same offsets.
  Matches design §3 "value semantics preserved".
- No-PyObject audit: grep over the four generated `.rs` files shows every node
  struct field is `span: Span` / `children: Vec<(Option<Label>, Child)>`; no
  residual `PyObject`/`Py<PyList>` node state; no `UNKNOWN_SPAN_CACHE` in
  generated code (only a stale explanatory comment in `src/lib.rs:10-16`, and the
  retained-but-unread `crate::UNKNOWN_SPAN` static — dead for generated code, not
  a correctness bug).
- Known accepted limitation (documented, not a finding): span getter
  (`:498-511`) and child `Span` `to_pyobject` (`:371`) reconstruct
  `fltk._native.Span(start, end)` *sourceless*, so `.text()` through the
  Python boundary returns None/raises until §2.5/§2.6 attach source. Tracked by
  the design as deferred; consistent with implementation-log increment 2/4
  deviations.
