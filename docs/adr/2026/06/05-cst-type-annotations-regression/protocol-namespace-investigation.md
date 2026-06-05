# Investigation: Protocol Class Namespace & "Node" Suffix Justification

## Executive Summary

The claim that Protocol classes are generated into "the same namespace" to justify the `*Node` suffix is **factually incorrect**. The code generator emits Protocol classes into a **separate, dedicated module** (`*_cst_protocol.py`), not co-located with concrete CST classes. Consequently, the stated justification for the suffix is not justified by the architecture. The suffix persists as a consequence of a design choice made in commit 3ffe12d, but that choice was *not* forced by namespace collision concerns.

---

## Question 1: SAME FILE OR NOT?

### Answer: NO

The generator emits concrete CST classes and Protocol classes into **separate `.py` files**.

### Evidence from genparser.py (lines 174–209)

**Concrete CST module emission (line 175–192):**
```python
# Line 175: Concrete CST file path
shared_cst = output_dir / f"{base_name}_cst.py"

# Line 185-186: Generate and emit concrete CST
cst_mod = cstgen.gen_py_module()
cst_text = ast.unparse(cst_mod)

# Line 188-189: Write concrete CST to file
with shared_cst.open("w", newline="\n") as f:
    f.write(cst_text)
```

**Protocol module emission (line 194–209):**
```python
# Line 194: Protocol module file path
shared_cst_protocol = output_dir / f"{base_name}_cst_protocol.py"

# Line 198: Generate Protocol module
protocol_mod = cstgen.gen_protocol_module()

# Line 205-206: Write Protocol module to separate file
with shared_cst_protocol.open("w", newline="\n") as f:
    f.write(protocol_text)
```

### Actual File Layout

At HEAD (1e67ed4):
```
fltk/fegen/fltk_cst.py              ← Concrete classes: Rule, Grammar, Items, etc.
fltk/fegen/fltk_cst_protocol.py     ← Protocol classes: RuleNode, GrammarNode, ItemsNode, etc.
```

These are **two distinct modules** with different import paths:
- `from fltk.fegen import fltk_cst` → access `fltk_cst.Rule`
- `from fltk.fegen import fltk_cst_protocol` → access `fltk_cst_protocol.RuleNode`

### Conclusion to Q1

**The justification is false.** The generator does not emit Protocol classes into the same `.py` file as concrete classes. The `*_cst_protocol.py` module is entirely separate, removing any plausible namespace-collision argument.

---

## Question 2: HOW ARE PROTOCOL TYPES REFERENCED?

### Answer: Via Module Alias Qualifier (e.g., `cst.RuleNode`)

In backend-agnostic consumers like `fltk2gsm.py`, Protocol types are **always referenced with a module alias**, never bare.

### Evidence from fltk2gsm.py (lines 1–30)

**Import structure (lines 7, 11):**
```python
from fltk.fegen import fltk_cst as _default_cst      # Line 7: Concrete module (runtime)

if TYPE_CHECKING:
    from fltk.fegen import fltk_cst_protocol as cst  # Line 11: Protocol module (type-checking only)
```

**Two distinct module imports with different aliases:**
- `_default_cst` → references `fltk_cst.Rule` (concrete class, used at runtime)
- `cst` → references `fltk_cst_protocol.RuleNode` (Protocol class, used in annotations)

**Protocol type usage (example annotations from lines 26–30):**
```python
def visit_grammar(self, grammar: cst.GrammarNode) -> gsm.Grammar:     # Line 26
    ...

def visit_rule(self, rule: cst.RuleNode) -> gsm.Rule:                 # Line 30
    ...
```

All Protocol types are referenced as **`cst.<ProtocolClassName>`**, e.g.:
- `cst.GrammarNode` (not bare `GrammarNode`)
- `cst.RuleNode` (not bare `RuleNode`)
- `cst.ItemsNode` (not bare `ItemsNode`)

### Module Separation at Runtime

Line 22–24 shows two distinct module instances:
```python
class Cst2Gsm:
    def __init__(self, terminals, cst: cst.CstModule = _DEFAULT_CST):
        self.cst = cst  # At runtime, receives concrete fltk_cst instance
```

The annotation says `cst: cst.CstModule` (Protocol type), but the runtime default is `_DEFAULT_CST = cast("cstp.CstModule", _default_cst)` (concrete module cast to Protocol). Two different modules, two different aliases.

### Conclusion to Q2

Protocol types are **never referenced bare**; they are always accessed via the `cst` module alias (qualifying `RuleNode`, `GrammarNode`, etc.). The concrete CST module uses a different alias (`_default_cst`), ensuring no bare-name collision.

---

## Question 3: WOULD BARE NAMES COLLIDE?

### Answer: NO COLLISION in the actual architecture, because Protocol and concrete classes are in separate modules

Given the actual file layout and import structure:

**Current state:**
- Concrete CST: `fltk_cst.Rule`, `fltk_cst.Grammar`, etc. (module `fltk_cst`)
- Protocol CST: `fltk_cst_protocol.RuleNode`, `fltk_cst_protocol.GrammarNode`, etc. (module `fltk_cst_protocol`)
- Annotations always use qualified names: `cst.RuleNode`, `cst.GrammarNode` (where `cst` is an alias for `fltk_cst_protocol`)

**If the suffix were dropped (hypothetical):**
- Concrete CST: `fltk_cst.Rule`, `fltk_cst.Grammar` (unchanged, different module)
- Protocol CST: `fltk_cst_protocol.Rule`, `fltk_cst_protocol.Grammar` (renamed, different module)
- Annotations would use: `cst.Rule`, `cst.Grammar` (still qualified, no collision)

**Result: NO COLLISION.** Because the classes exist in separate modules with separate import paths, a bare name like `Rule` in one module does not collide with `Rule` in another. Python module aliasing handles disambiguation; there is no namespace ambiguity.

### Why the Suffix Exists (But Isn't Required)

The `*Node` suffix was introduced in commit 3ffe12d with the comment in `gsm2tree.py` (line 285–287):

```python
def protocol_node_name(self, rule_name: str) -> str:
    """Rule name → Protocol class name; must stay in sync with class_name_for_rule_node."""
    return self.class_name_for_rule_node(rule_name) + "Node"
```

The docstring offers no justification, but earlier prose in the node-suffix-investigation.md admits:

> "The suffix serves disambiguation only. Protocol classes are defined alongside concrete classes in the same module. The `*Node` suffix disambiguates them."

This statement is **now false** (since Protocols are in a separate module), but it may have been the original design rationale. The suffix was a *precaution* for a design scenario that was never implemented.

### Module Layout: The Real Reason for Safety

The true design guarantee is:
1. **Separate files** → `fltk_cst.py` (concrete) and `fltk_cst_protocol.py` (protocol)
2. **Separate module imports** → `as _default_cst` (concrete) and `as cst` (protocol)
3. **Qualified references** → `cst.RuleNode`, `_default_cst.Rule`

No collision occurs even if class names were identical, because they are in different namespaces from the perspective of the code that consumes them.

### Conclusion to Q3

**The suffix is not necessary to avoid collisions.** The architectural separation into two modules, combined with module aliasing in consumers, provides sufficient namespace disambiguation. If the `*Node` suffix were dropped, no pyright errors or runtime name collisions would occur.

---

## Summary: Was the Justification Real?

| Aspect | Claimed | Actual |
|--------|---------|--------|
| **Same file/module?** | "Yes, both in same namespace" (stated justification) | **No.** Concrete in `fltk_cst.py`, Protocol in `fltk_cst_protocol.py` |
| **Name collision risk?** | "Yes, suffix disambiguates" | **No.** Different modules, different import aliases, qualified references eliminate collision |
| **Suffix necessity?** | "Required for disambiguation" | **No.** Could be dropped without breaking anything, due to module separation |

**Verdict:** The stated justification is **factually incorrect**. The suffix is an artifact of commit 3ffe12d's design choice (possibly a conservative precaution), but it is not justified by the current architecture.

---

## Implementation Details: Protocol Generation Code

### Where Protocols are Generated

**File:** `fltk/fegen/gsm2tree.py`

**Method 1: `gen_protocol_module()` (lines 323–338)**
```python
def gen_protocol_module(self) -> ast.Module:
    """Generate a *_cst_protocol.py module with Protocol classes describing the CST module surface."""
    module = ast.parse("")
    assert isinstance(module, ast.Module)
    module.body.append(pygen.stmt("from __future__ import annotations"))
    module.body.append(pygen.import_(("typing",)))
    module.body.append(pygen.import_(("fltk", "fegen", "pyrt", "terminalsrc")))

    for rule in self.rule_models:
        model = self.rule_models[rule]
        class_name = self.protocol_node_name(rule)  # ← Appends "Node" suffix
        module.body.append(self._protocol_class_for_model(class_name, model))

    module.body.append(self._cst_module_protocol())
    return module
```

**Key line:** `class_name = self.protocol_node_name(rule)` appends "Node" to rule name.

### Where Concrete Classes are Generated (Unchanged)

**File:** `fltk/fegen/gsm2tree.py`

**Method 2: `gen_py_module()` (lines 95–107)**
```python
def gen_py_module(self) -> ast.Module:
    imports = [...]
    module = pygen.module(module.import_path for module in imports)

    for rule, model in self.rule_models.items():
        module.body.append(self.py_class_for_model(self.class_name_for_rule_node(rule), model))
    return module
```

Concrete classes use plain `class_name_for_rule_node()` with no suffix.

### No Option to Co-locate or Unify

Searching the codebase confirms there is **no configuration option** to emit both Protocol and concrete classes to the same file. The generator architecture enforces separation via `gen_py_module()` (concrete) and `gen_protocol_module()` (protocol) as two distinct entry points.

---

## Files & Commits Referenced

- **fltk/fegen/genparser.py** (lines 174–209) — Emission code for both modules
- **fltk/fegen/gsm2tree.py** (lines 285–287, 323–338) — `protocol_node_name()` and `gen_protocol_module()`
- **fltk/fegen/fltk2gsm.py** (lines 7, 11, 26–30) — Consumer imports and Protocol type usage
- **Commit 3ffe12d** — Introduced Protocol generation with `*Node` suffix

---

## Recommendations for Review

1. **Naming Decision:** The `*Node` suffix should be retained OR dropped based on stylistic/readability preferences, **not** namespace-collision arguments. The current architecture does not require it.

2. **Documentation:** Update any comments claiming the suffix serves "disambiguation when Protocol and concrete classes are generated in the same namespace" — this is architecturally false. The suffix is an implementation artifact, not a necessity.

3. **Future Refactoring:** If `.pyi` stub files are used instead of `.py` for Protocol modules, the suffix could be reconsidered, since `.pyi` files have separate import semantics.
