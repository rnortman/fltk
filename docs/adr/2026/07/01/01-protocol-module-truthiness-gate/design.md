# Design: TODO(protocol-module-truthiness-gate) burndown

Requirements: `request.md` (this directory). Exploration: `exploration.md` (this directory; base commit 8fd5ecf). All line citations below re-verified directly at HEAD c03a801; the only drift from the exploration is TODO.md, whose entry now lives at `TODO.md:55-57`.

## 1. Root cause / context

`CstGenerator._protocol_class_for_model` (`fltk/fegen/gsm2tree.py:915`) decides whether a
protocol node class gets the precise discriminant

```python
if rule_name and self.py_module.import_path:
    klass.body.append(pygen.stmt(f"kind: typing.Literal[NodeKind.{member}] = NodeKind.{member}"))
else:
    klass.body.append(pygen.stmt("kind: object"))
```

`py_module` is dual-used: its real job is concrete-CST emission (type registration at
`gsm2tree.py:76`, same-module annotation stripping at `gsm2tree.py:90`), and it is *also* a
truthiness sentinel for the protocol `kind` discriminant. The protocol-emission path never reads
`py_module`'s actual value (exploration, "Does `py_module` serve purposes in the protocol path
beyond the truthiness gate?" — checked exhaustively: `protocol_annotation_for_model_types` and
every other helper `gen_protocol_module` assembles are `py_module`-free). Only the truthiness
matters, and it silently degrades output: a `Builtins`-backed generator (`import_path=()`, falsy —
`fltk/iir/py/reg.py:11-16`) emits `kind: object` with no error.

The Rust backend pays for this today: `RustCstGenerator.generate_protocol`
(`fltk/fegen/gsm2tree_rs.py:426-453`) cannot reuse its own `self._py_gen` (deliberately
`Builtins`-backed for `.rs`/`.pyi` generation, `gsm2tree_rs.py:177-181`), so it constructs a
throwaway `CstGenerator(py_module=pyreg.Module(["_protocol"]), context=create_default_context())`
purely to make the sentinel truthy — re-running the full per-rule model derivation
(`gsm2tree.py:43-44`) and allocating a fresh compiler context whose type registrations are dead
work (exploration confirms the throwaway context is observed by nothing).

Exactly two non-test call sites reach protocol emission: `genparser.py:248` (real user-supplied
module, gate truthy for free) and `gsm2tree_rs.py:453` (the workaround). Requirements verdict: Do —
replace the sentinel with an explicit parameter; this net-deletes the workaround rather than
relabeling it.

## 2. Proposed approach

### 2.1 `fltk/fegen/gsm2tree.py` — explicit `emit_kind_literal` parameter

Add a keyword-only parameter, threaded through the protocol-emission chain:

- `gen_protocol_module(self, *, emit_kind_literal: bool = True) -> ast.Module`
- `gen_protocol_module_text(self, *, emit_kind_literal: bool = True) -> str` (forwards)
- `_protocol_class_for_model_with_assignments(self, class_name, model, rule_name, *, emit_kind_literal: bool)` — required keyword on the internal helpers (no default), so the threading stays explicit and a future internal caller must choose.
- `_protocol_class_for_model(self, class_name, model, rule_name, *, emit_kind_literal: bool)`

The gate becomes:

```python
if rule_name and emit_kind_literal:
```

The `rule_name and` guard is kept as-is (out of scope; the only call path always passes a real
rule name). The `else: kind: object` arm is kept as the explicit `emit_kind_literal=False` form —
the requirements chose a parameter, not outright deletion of the degraded form, and the parameter
gives out-of-tree callers a documented escape hatch instead of an accidental one. Delete the
`TODO(protocol-module-truthiness-gate)` comment block (`gsm2tree.py:910-914`); replace with a
short comment stating the discriminant is controlled by `emit_kind_literal` and that `py_module`
plays no role in protocol output.

**Default `True` is the deliberate choice.** The `Literal` discriminant is always valid protocol
output: `gen_protocol_module` unconditionally emits the module-level `NodeKind` enum with a member
per rule (`gsm2tree.py:747`), so every `Literal[NodeKind.X]` reference resolves. Defaulting `False`
would recreate the trap in a new shape (every caller must remember to opt in or silently get
degraded output). Default `True` also keeps both production callers source-compatible per the
requirements ("a defaulted keyword keeps both source-compatible").

This is a behavior change for one hypothetical caller class: an out-of-tree `Builtins`-backed
`CstGenerator` calling `gen_protocol_module*` would now get the precise `Literal` form instead of
`kind: object`. That is the trap being fixed, not a regression — the degraded form was documented
at the gate as a silent failure mode, and the `Literal` form is strictly more precise. Callers who
genuinely want the degraded form pass `emit_kind_literal=False`. Called out here per CLAUDE.md's
out-of-tree-consumer policy as a deliberate decision.

### 2.2 `fltk/fegen/gsm2tree_rs.py` — delete the workaround

`RustCstGenerator.generate_protocol` becomes:

```python
return self._py_gen.gen_protocol_module_text()
```

Delete the throwaway `CstGenerator` construction (lines 445-449) and rewrite the docstring's
"Implementation note" paragraph (lines 435-443), which documents the workaround being removed.
Keep the byte-identity paragraph (shared rendering formula with the Python path).

Why reuse is byte-identical to the throwaway:

- Same grammar object: `self._py_gen` and the throwaway were both built from
  `grammar_with_trivia` (`gsm2tree_rs.py:176-182`), so `rule_models` (iteration order and content)
  are identical.
- Context differences are inert: protocol emission consults the context only via
  `pycompiler.iir_type_to_py_annotation` for library types (Span), which resolves through
  default registrations present in every `create_default_context()`; the rule-type registrations
  `self._py_gen` accumulated under `Builtins` are not on that path (exploration §"Does `py_module`
  serve purposes...").
- Protocol emission performs no registry writes, so reusing `self._py_gen` has no side effects on
  subsequent `.rs`/`.pyi` generation.

The existing cross-path byte-identity test (`fltk/fegen/test_genparser.py:599-635`, Rust
`--protocol-output` vs Python `generate --protocol`) is the guardrail for all of the above.

### 2.3 Bookkeeping

- Delete the `## \`protocol-module-truthiness-gate\`` entry from `TODO.md` (lines 55-57). This
  also moots that entry's known error (it misnames the containing method as
  `_protocol_class_for_model_with_assignments`; the gate is in `_protocol_class_for_model`).
- Update the stale test docstring at `tests/test_gsm2tree_rs.py:1132-1135`, which describes the
  placeholder workaround.
- Update the one direct caller of the private helper: the `TestMutatorsEmittedPyProtocol` fixture
  (`tests/test_gsm2tree_py.py:496`) calls `gen._protocol_class_for_model("Bar", model, "bar")` and
  would raise `TypeError` under the required keyword. Change it to pass `emit_kind_literal=True` —
  matching the new public default; that class's tests assert only mutator stubs and method
  ordering, never the `kind` line, so assertions are unaffected (the fixture's generator is
  `Builtins`-backed via `tests/gsm2tree_helpers.py:69`, so its emitted `kind` line changes from
  `object` to the `Literal` form, which nothing asserts on). This is the only direct caller of
  either private helper outside `gsm2tree.py` (checked at HEAD c03a801; the exploration's caller
  sweep covered only `gen_protocol_module*` and `CstGenerator(...)` sites).
- No other `TODO(protocol-module-truthiness-gate)` markers exist (exploration; ADR docs under
  `docs/adr/2026/06/30-codegen-protocol-pyi-outputs/` are immutable history and stay untouched).

## 3. Edge cases / failure modes

- **`emit_kind_literal=False` output validity**: `NodeKind` is still emitted unconditionally, so
  the degraded module remains self-consistent (it just loses per-class `kind` narrowing). No
  in-tree caller passes `False`; the arm exists as the explicit form of the old degraded output.
- **Empty `rule_name`**: unchanged — the `rule_name and` guard still short-circuits to
  `kind: object`. Only reachable if a caller invokes the private helper directly with `""`.
- **Context coupling from `_py_gen` reuse**: protocol emission is read-only with respect to the
  context and `py_module`. A future change that *reads* either is caught by the byte-identity
  test (`test_genparser.py:599`) and the new py_module-independence test (§4 test 2); a future
  change that *writes* shared state is caught by the new same-instance reuse test (§4 test 4) —
  the fresh-generator-per-invocation tests alone would stay green on that failure mode.
- **Out-of-tree `Builtins`-backed callers**: output changes from `kind: object` to `Literal` (see
  §2.1 — deliberate, an upgrade, escape hatch provided).
- **Determinism**: cross-instance determinism is covered by the existing test
  (`tests/test_gsm2tree_rs.py:1144-1147`), but that test builds two fresh `RustCstGenerator`
  instances and calls `generate_protocol()` once each — it never reuses one instance, so it does
  not exercise the new state-sharing surface (one `_py_gen` serving `.rs`/`.pyi` emission and
  repeated protocol emission). New test 4 (§4) pins same-instance reuse directly.

## 4. Test plan

TDD order: add/adjust tests first, confirm the new ones fail, then implement.

New tests (1-3 in `fltk/fegen/test_cst_protocol.py`, next to the existing protocol-generator
suite; 4 in `tests/test_gsm2tree_rs.py`):

1. **Trap regression**: a `Builtins`-backed `CstGenerator` emits `kind: typing.Literal[NodeKind.*]`
   (and no `kind: object`) from `gen_protocol_module_text()` with defaults. Fails today.
2. **`py_module` independence**: protocol text from a `Builtins`-backed generator is byte-identical
   to protocol text from a real-module-backed generator over the same grammar. Pins the invariant
   that `py_module` plays no role in protocol output. Fails today.
3. **Explicit opt-out**: `gen_protocol_module_text(emit_kind_literal=False)` emits `kind: object`
   for every node class and no `Literal[NodeKind.` occurrences. Fails today (unknown keyword
   argument); exercises the parameter actually gating.
4. **Same-instance `_py_gen` reuse** (next to `TestGenerateProtocol`): on a single
   `RustCstGenerator`, call `generate_protocol()` twice —
   interleaved with a `generate_pyi`/`generate_rs` call — and assert both protocol outputs are
   byte-identical. Pins that protocol emission neither mutates nor is affected by the shared
   `_py_gen`/context state, which the existing cross-instance test (see §3) cannot catch.

Existing tests that must keep passing unchanged (they are the guardrails):

- `fltk/fegen/test_genparser.py:599-635` — Rust/Python cross-path byte-identity + Literal-form
  assertions; now also guards the `_py_gen` reuse.
- `fltk/fegen/test_genparser.py:274-388` — `--protocol` / `--protocol-only` byte-identity variants.
- `tests/test_gsm2tree_rs.py:1111-1147` — `generate_protocol` shape, Literal-form, and
  cross-instance determinism tests (docstring at 1132-1135 updated per §2.3; assertions
  unchanged).
- `fltk/fegen/test_cst_protocol.py` — real-module protocol suite; unaffected.
- `tests/test_gsm2tree_py.py:233-337` (`TestProtocolModuleAll`) — `Builtins`-backed via
  `tests/gsm2tree_helpers.py:69` (not real-module): its generated module content flips from
  `kind: object` to the `Literal` form under the new default, but every assertion inspects only
  `__all__` and module structure, which the parameter does not affect — passes unchanged.
- `tests/test_gsm2tree_py.py:488-547` (`TestMutatorsEmittedPyProtocol`) — fixture updated per §2.3
  to pass `emit_kind_literal=True`; assertions unchanged.

## 5. Open questions

None. The requirements fix the approach (explicit `emit_kind_literal` parameter, defaulted for
source compatibility); the judgment calls — default value and keeping the degraded arm (§2.1),
and the keyword passed by the direct-helper test fixture (§2.3) — are resolved with rationale.
