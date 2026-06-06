# Exploration: TODO(protocol-label-member-private) — `_ProtocolLabelMember` visibility

Concise. Precise. No fluff, no prescriptions. Facts and source-ground-truth only.

---

## Claim verification

### Is `_ProtocolLabelMember` emitted as a module-level class in the generated protocol module?

**Yes — confirmed.**

`gsm2tree.py:488`:
```python
module.body.extend(self._emit_protocol_label_member_class())
```
called inside `gen_protocol_module` (`gsm2tree.py:471`). The class is emitted unconditionally before any rule's Protocol class.

In the generated artifact `fltk/fegen/fltk_cst_protocol.py:57-77`, the class appears at module level:
```python
class _ProtocolLabelMember:
    _fltk_canonical_name: str
    def __init__(self, canonical_name: str) -> None: ...
    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...
    def __repr__(self) -> str: ...
```

### Does the generated protocol module have any `__all__`?

**No.** Neither `fltk_cst_protocol.py` nor `gen_protocol_module` (`gsm2tree.py:471-499`) emit or reference `__all__`. The `grep -rn "__all__" fltk/fegen/` hit that mentions `__all__` is only the TODO comment at `gsm2tree.py:444`, not an actual emission. The one real `__all__` in the tree is `fltk/fegen/pyrt/span.py:24` — unrelated.

### Does `_ProtocolLabelMember` appear in wildcard imports anywhere in-tree?

**No wildcard imports from protocol modules exist in the repo.** `grep -rn "from.*import \*"` across all `.py` files returns zero results. All in-tree imports of `fltk_cst_protocol` use the `as cstp` alias (`test_cst_protocol.py:200,281,295,358,398`). The risk is IDE autocompletion and downstream `from foo_cst_protocol import *` patterns — not current in-tree usage.

### Does `_ProtocolLabelMember` get imported elsewhere?

Only three files reference it:
- `fltk/fegen/fltk_cst_protocol.py` — generated output, definition + 28 assignment sites (e.g. line 105: `Grammar.Label.RULE = _ProtocolLabelMember("Grammar.Label.RULE")`)
- `fltk/fegen/gsm2tree.py` — generator, emits the class via `ast.parse` at line 451
- `fltk/fegen/test_cst_protocol.py:113` — test explicitly adds `"_ProtocolLabelMember"` to `expected_node_names` as a known module-level class

No code imports `_ProtocolLabelMember` by name from the protocol module; all uses are internal to the generated file via bare name reference in the post-class assignment statements (line 515 in `gsm2tree.py`).

---

## Option (a): emit `__all__` — feasibility

`gen_protocol_module` (`gsm2tree.py:471-499`) builds the module body as a list of `ast.stmt`. Inserting a `__all__ = [...]` assignment is straightforward: collect the intended public names (all `Protocol` class names, `NodeKind`, `Span`, `CstModule`), emit an `ast.Assign` node at the top of the module body.

**Blast radius:**
- Generated file changes (new `__all__` line in every `*_cst_protocol.py`).
- `test_cst_protocol.py:113` checks `class_defs` by scanning `ast.ClassDef` nodes, not by inspecting `__all__`; it would not need to change for correctness, but may need updating if the test intent evolves.
- No downstream breaking change: `__all__` suppresses wildcard-import leakage but does not remove the name from the module namespace. Code doing `from foo_cst_protocol import _ProtocolLabelMember` would still work (though no in-tree code does this).
- `NodeKind` also has no leading underscore but is intended public; `__all__` would need to include it.

**Self-containment:** fully preserved; no new imports required.

---

## Option (b): move `_ProtocolLabelMember` to `fltk.fegen.pyrt.bridge` — feasibility

**`fltk.fegen.pyrt.bridge` does not exist.** The `pyrt` package contains only `errors.py`, `memo.py`, `span.py`, `span_protocol.py`, `terminalsrc.py`, and `test_memo.py`. There is no `bridge.py` or `bridge/` directory.

Creating `fltk.fegen.pyrt.bridge` and moving the class there would require:

1. Creating the new module (new file, new public install surface).
2. `gen_protocol_module` currently emits `import fltk.fegen.pyrt.terminalsrc` (`gsm2tree.py:478`). Adding `import fltk.fegen.pyrt.bridge` would be a new generated import, coupling every generated `*_cst_protocol.py` to the new module.
3. The generated post-class assignments (`SomeNode.Label.X = _ProtocolLabelMember(...)`, `gsm2tree.py:515`) reference `_ProtocolLabelMember` as a bare name. After moving the class to `bridge`, the generated code would need either `from fltk.fegen.pyrt.bridge import _ProtocolLabelMember` (putting an underscore-prefixed name in the import list, which is unusual but not wrong) or an alias import.
4. **Self-containment broken for generated modules**: downstream consumers copying or embedding the generated protocol file without the FLTK runtime would gain a new hard dependency on `fltk.fegen.pyrt.bridge`. Currently `fltk_cst_protocol.py` only depends on `fltk.fegen.pyrt.terminalsrc`.
5. The `_emit_cross_backend_eq_hash` / `_emit_protocol_label_member_class` duplication noted in `TODO(protocol-label-member-bridge-unify)` (`gsm2tree.py:447`) is a separate concern but interacts: moving to `bridge` could be done simultaneously with unifying the two bridge implementations, but the scope grows.

**Blast radius:** new runtime package file, changed generated import in every `*_cst_protocol.py`, test at `test_cst_protocol.py:113` may need updating (class no longer defined in module body — though it would still appear as an import), downstream consumers gain a new transitive dependency.

---

## Key differences between options

| Factor | Option (a) `__all__` | Option (b) move to `pyrt.bridge` |
|---|---|---|
| `_ProtocolLabelMember` in module namespace | Yes (accessible by explicit import) | No (not defined there at all) |
| New file required | No | Yes (`fltk/fegen/pyrt/bridge.py`) |
| Generated file changes | `__all__` line added | New import + no class def |
| Self-containment of generated module | Preserved | Broken (new runtime dep) |
| Test change required | No (test checks `ClassDef` nodes, not `__all__`) | Yes (`_ProtocolLabelMember` no longer a `ClassDef` in the module body) |
| Downstream breakage risk | None (name still importable) | Low but nonzero (new transitive dep on `pyrt.bridge`) |

---

## Open factual questions

- Whether downstream consumers currently do `from *_cst_protocol import *` (not visible in-tree; the risk is latent, not confirmed).
- Whether the `TODO(protocol-label-member-bridge-unify)` work is a prerequisite or co-requisite for option (b).
