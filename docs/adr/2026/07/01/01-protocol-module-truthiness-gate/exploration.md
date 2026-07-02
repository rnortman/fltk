# Exploration: TODO(protocol-module-truthiness-gate)

Base commit: 8fd5ecf.

## TODO marker locations

- Code comment: `fltk/fegen/gsm2tree.py:910-914` (single occurrence; immediately precedes the gate itself).
- Master list entry: `TODO.md:101-103` (heading `## \`protocol-module-truthiness-gate\``).
- Historical references (pre-existing, from the review chain that produced this TODO, not new occurrences to burn down): `docs/adr/2026/06/30-codegen-protocol-pyi-outputs/dispositions-deep.md:38`, `docs/adr/2026/06/30-codegen-protocol-pyi-outputs/notes-deep-quality.md:104`, `docs/adr/2026/06/30-codegen-protocol-pyi-outputs/judge-verdict-deep.md:11-12,52`.

No other `TODO(protocol-module-truthiness-gate)` comments exist anywhere in the tree (checked with a recursive grep over the whole repo).

Note: a stray, git-untracked directory `.claude/worktrees/agent-ab295be24eef6e7ce/` contains a full duplicate checkout of the repo (leftover from an earlier agent run) and surfaces in naive greps for `CstGenerator(`/`gen_protocol_module`. It is not part of the tracked source tree (`git ls-files .claude/worktrees` returns nothing) and every finding below is drawn only from the real tree.

## Does the gate exist as described?

Yes, exactly as cited. `fltk/fegen/gsm2tree.py:885-919` (`_protocol_class_for_model`):

```python
885: def _protocol_class_for_model(self, class_name: str, model: ItemsModel, rule_name: str) -> ast.ClassDef:
...
910:        # TODO(protocol-module-truthiness-gate): this gates the Literal discriminant on
911:        # py_module.import_path truthiness, dual-using py_module as both the concrete-CST module
912:        # path and a truthiness sentinel.  A Builtins-backed CstGenerator (empty import_path) silently
913:        # emits the degraded `kind: object` form; RustCstGenerator.generate_protocol works around this
914:        # with a non-empty placeholder py_module.  Replace with an explicit flag so callers opt in.
915:        if rule_name and self.py_module.import_path:
916:            member = self.node_kind_member_name(rule_name)
917:            klass.body.append(pygen.stmt(f"kind: typing.Literal[NodeKind.{member}] = NodeKind.{member}"))
918:        else:
919:            klass.body.append(pygen.stmt("kind: object"))
```

`pyreg.Module` (`fltk/iir/py/reg.py:11-16`) is `@dataclass(frozen=True, eq=True)` with a single field `import_path: Sequence[str]`, and `Builtins: Final = Module(import_path=())` — an empty tuple, which is falsy. So a `Builtins`-backed `CstGenerator` does make `self.py_module.import_path` falsy and hits the `else` branch (degraded `kind: object`).

**Location discrepancy**: the TODO.md entry and the ADR's `dispositions-deep.md`/`notes-deep-quality.md` attribute the gate to `_protocol_class_for_model_with_assignments` (`fltk/fegen/gsm2tree.py:819-834`). That method does not contain the gate; it only calls `_protocol_class_for_model` at line 826, and the gate itself lives inside `_protocol_class_for_model` (defined at line 885, gate at line 915). The inline code comment (910-914) is correctly attached at the actual gate site; only the TODO.md prose and two ADR docs misname the enclosing method. `judge-verdict-deep.md:11-12` cites `gsm2tree.py:910` for "the gate", which is the comment's first line, not the `if` statement itself (line 915) — a similarly loose but not wrong citation (910 is part of the same 5-line comment block immediately above the gate).

## Does the placeholder workaround exist as described?

Yes. `fltk/fegen/gsm2tree_rs.py:426-453` (`RustCstGenerator.generate_protocol`):

```python
426: def generate_protocol(self) -> str:
...
435:    Implementation note (design §1.2): ``CstGenerator.gen_protocol_module`` gates the per-rule
436:    ``kind: typing.Literal[NodeKind.*]`` discriminant on ``py_module.import_path`` being truthy,
437:    falling back to the degraded ``kind: object`` form otherwise.  The existing ``self._py_gen``
438:    is built with ``pyreg.Builtins`` (an empty, falsy ``import_path``) and backs ``.rs`` / ``.pyi``
439:    generation, so it is NOT reused here.  Instead a dedicated ``CstGenerator`` is constructed with
440:    a non-empty placeholder ``py_module`` so the ``Literal`` discriminant is emitted.  The
441:    ``import_path`` value never appears in protocol output — only its truthiness gates the
442:    discriminant — so any non-empty placeholder yields identical bytes and the caller need not
443:    supply a CST module name.
444:    """
445:    protocol_gen = CstGenerator(
446:        grammar=self.grammar,
447:        py_module=pyreg.Module(["_protocol"]),
448:        context=create_default_context(),
449:    )
450:    return protocol_gen.gen_protocol_module_text()
```

`self._py_gen` (used for `.rs`/`.pyi` generation) is constructed at `fltk/fegen/gsm2tree_rs.py:177-181` with `py_module=pyreg.Builtins`. `generate_protocol` does not reuse `self._py_gen`; it builds a second, throwaway `CstGenerator` (fresh `context=create_default_context()`, i.e. not even sharing the outer context) solely so `self.py_module.import_path` is truthy when `gen_protocol_module_text` runs.

## All callers of `CstGenerator(...)` / `gen_protocol_module` / `gen_protocol_module_text`, and what `py_module` they pass

`gen_protocol_module`/`gen_protocol_module_text` callers (excluding tests and the stray worktree):
- `fltk/fegen/genparser.py:248` — `cstgen.gen_protocol_module_text()`, where `cstgen` was built at line 221: `gsm2tree.CstGenerator(grammar=grammar, py_module=cst_module, context=create_default_context())`, and `cst_module = pyreg.Module(cst_module_name.split("."))` (line 220) — a real, user-supplied, non-empty module path (e.g. `mylang.cst`). This is the Python `generate --protocol`/`--protocol-only` CLI path (`fltk/fegen/genparser.py:127-260`). Here the gate is truthy *for free* — no workaround needed, because this caller's `py_module` is legitimately non-empty for its other purpose (annotating the concrete `_cst.py` module).
- `fltk/fegen/gsm2tree_rs.py:453` — `protocol_gen.gen_protocol_module_text()` on the throwaway `protocol_gen` described above (the workaround).

All other `CstGenerator(...)` construction sites in the non-test tree:
- `fltk/plumbing.py:109` — `py_module=pyreg.Builtins` (does not call `gen_protocol_module`/`_text`; only used for `gen_py_module`/parser generation in `generate_parser`).
- `fltk/fegen/bootstrap.py:478` — `py_module=cst_module` (a real module, bootstrap self-hosting; does not call the protocol methods).
- `fltk/fegen/genparser.py:94` (`generate_parser` function) — `py_module=cst_module`, a real module; does not call the protocol methods (only `gen_py_module` via `ParserGenerator`).
- `fltk/fegen/gsm2tree_rs.py:177-181` (`RustCstGenerator.__init__`, i.e. `self._py_gen`) — `py_module=pyreg.Builtins`; used only for `.rs`/`.pyi` generation (`_rule_info`, `_pyi_annotation_for_model_types`, etc.), never for `gen_protocol_module*`.
- Every test-file `CstGenerator(...)` call (e.g. `fltk/fegen/test_gsm2tree.py:13`, `fltk/fegen/test_gsm2parser.py:29`, the dozen `test_regression_*.py`/`test_leading_separators.py`/`test_trivia_capture.py`/`test_trailing_character_bug.py` files, `tests/gsm2tree_helpers.py:69`, `tests/test_nullable_loop_guard.py:707`) passes `py_module=pyreg.Builtins` and does not touch the protocol path.
- `fltk/fegen/test_cst_protocol.py:63,72-73` — `py_module=cst_module` (a real module) feeding `gen_protocol_module()`; this is the test suite for the protocol generator itself, and it deliberately uses a non-empty module (i.e. the tests never exercise the `Builtins`/degraded path at all).
- `fltk/iir/test_context.py:148,151,188,191` — real `cst_module`(s); unrelated to protocol generation (tests type-registry isolation across contexts).

So in the entire non-test tree, `gen_protocol_module`/`gen_protocol_module_text` is reached from exactly two call sites (`genparser.py:248` and `gsm2tree_rs.py:453`), and only the Rust-backend one needs the placeholder, precisely because `RustCstGenerator._py_gen` (its only naturally-available `CstGenerator`) is intentionally `Builtins`-backed for its primary job (`.rs`/`.pyi` generation, which is backend-agnostic and has no real Python CST module to name).

## Does `py_module` serve purposes in the protocol path beyond the truthiness gate?

No — checked exhaustively. `self.py_module` is referenced exactly 3 times in `fltk/fegen/gsm2tree.py`:
- Line 36: `self.py_module = py_module` (assignment in `__init__`).
- Line 76 (`iir_type_for_rule`): `self.context.python_type_registry.register_type(pyreg.TypeInfo(typ=typ, module=self.py_module, name=name))` — registers rule types under `self.py_module` in the *compiler context's* type registry.
- Line 90 (`py_annotation_for_model_types`, used for `gen_py_module`/concrete-CST and parser annotation, *not* for the protocol path): `f'"{typ.removeprefix(".".join(self.py_module.import_path) + ".")}"'` — strips the module's own import path prefix off same-module type references.
- Line 915: the truthiness gate itself.

The protocol-path annotation method, `protocol_annotation_for_model_types` (`fltk/fegen/gsm2tree.py:658-688`), does **not** reference `self.py_module` at all — it emits bare/quoted Protocol class names (`protocol_node_name`, itself just `class_name_for_rule_node`, `gsm2tree.py:649-656`) and library-type annotations via `pycompiler.iir_type_to_py_annotation`/`typemodel.lookup_type`, none of which consult `py_module`. Likewise `_node_kind_enum`, `_emit_node_kind_canonical_name_assignments`, `_protocol_span_class`, `_cst_module_protocol`, and `_emit_protocol_label_member_class` (the other pieces `gen_protocol_module` assembles, `gsm2tree.py:719-798`) take no `py_module`-derived input.

The placeholder `CstGenerator` in `generate_protocol` (`gsm2tree_rs.py:445-449`) does still execute `__init__`'s `model_for_rule` pass over every rule (`gsm2tree.py:43-44`) and, if any rule's model happens to call `iir_type_for_rule`, registers types into its *own freshly-created* `context.python_type_registry` (line 76) under the placeholder module — but that registry is `create_default_context()` (line 448), a throwaway distinct from `self.context`/`self._py_gen`'s context, so this registration is never observed by anything else; it is dead work, not a second live use of the placeholder value. Confirms the docstring's claim that "the `import_path` value never appears in protocol output — only its truthiness gates the discriminant."

## Would an explicit parameter eliminate the workaround?

Based on the above: yes, structurally. Since (a) `self.py_module` has no other reader anywhere in the protocol-emission call graph and (b) the only two real (non-test) callers of `gen_protocol_module*` already differ exactly along this axis — `genparser.py:248`'s `cstgen` has a real, non-empty `py_module` for its other (concrete-CST) job and would pass `emit_kind_literal=True`, while `gsm2tree_rs.py`'s only naturally-available generator (`self._py_gen`, `Builtins`-backed) would pass `emit_kind_literal=True` explicitly and call `self._py_gen.gen_protocol_module_text()` directly — an explicit boolean parameter would let `generate_protocol` reuse `self._py_gen` and delete the second `CstGenerator` construction (including its redundant `create_default_context()` and full rule-model re-derivation) entirely, rather than merely relabeling the same two-generator structure.

## Summary of facts

- Gate exists as described at `fltk/fegen/gsm2tree.py:915` (`if rule_name and self.py_module.import_path:`), inside `_protocol_class_for_model` (not `_protocol_class_for_model_with_assignments`, which TODO.md and two ADR docs misname as the containing method; the inline code comment at lines 910-914 is correctly sited).
- Placeholder workaround exists as described at `fltk/fegen/gsm2tree_rs.py:445-453`, constructing a second `CstGenerator(py_module=pyreg.Module(["_protocol"]), context=create_default_context())` distinct from `self._py_gen` (`py_module=pyreg.Builtins`, `gsm2tree_rs.py:177-181`) used for all other Rust/`.pyi` generation.
- Exactly two non-test call sites reach `gen_protocol_module`/`gen_protocol_module_text`: `genparser.py:248` (real module, gate naturally true) and `gsm2tree_rs.py:453` (the workaround).
- `py_module` has exactly one other live use in `CstGenerator` (`iir_type_for_rule`/`py_annotation_for_model_types`, both concrete-CST-only, `gsm2tree.py:76,90`); the protocol-emission path (`protocol_annotation_for_model_types` and everything else `gen_protocol_module` calls) never reads `self.py_module`, confirming the placeholder's `import_path` value is inert and only its truthiness matters.
- An explicit `emit_kind_literal`-style boolean parameter would not just rename the gate but would let `generate_protocol` drop the second `CstGenerator` construction and reuse `self._py_gen` directly, since nothing else in the protocol path depends on `py_module`'s actual value.
