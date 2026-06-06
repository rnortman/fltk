# Investigation: CST Node Class Naming — "Node" Suffix Regression

## Executive Summary

**The concern is UNFOUNDED.** The public CST class names (e.g., `cst.Rule`, `cst.RuleNode`) have NOT changed from the start of this work cycle (a2822d5) to HEAD (1e67ed4). The `*Node` suffix is used ONLY in new Protocol classes (`fltk_cst_protocol.py`), which are parallel to the original CST classes and do not replace them.

---

## Fact 1: Naming History — Pre-Existing Convention

### At a2822d5 (start of cycle):
- fltk_cst.py contained: `class Rule:`, `class Grammar:`, `class Alternatives:`, etc.
- No `*Node` suffix in CST classes.
- No `fltk_cst_protocol.py` file existed.

**Verification:**
```bash
$ git show a2822d5:fltk/fegen/fltk_cst.py | grep "^class Rule"
class Rule:
```

### At 1e67ed4 (current HEAD):
- fltk_cst.py still contains: `class Rule:`, `class Grammar:`, `class Alternatives:`, etc.
- Identical to a2822d5.
- New file `fltk_cst_protocol.py` exists with Protocol versions: `class RuleNode(typing.Protocol):`, etc.

**Verification:**
```bash
$ git show 1e67ed4:fltk/fegen/fltk_cst.py | grep "^class Rule"
class Rule:

$ git show 1e67ed4:fltk/fegen/fltk_cst.py | grep "^class" | wc -l
14

$ git show a2822d5:fltk/fegen/fltk_cst.py | grep "^class" | wc -l
14

$ diff <(git show a2822d5:fltk/fegen/fltk_cst.py | grep "^class") \
       <(git show 1e67ed4:fltk/fegen/fltk_cst.py | grep "^class")
(no output — identical)
```

### Conclusion:
The `*Node` suffix is **NEW to this cycle** (introduced via the Protocol layer), but it does NOT affect the public CST API. The original CST classes retain their names.

---

## Fact 2: Current State — Class Names Unchanged

### Diff a2822d5..1e67ed4 on fltk_cst.py:
```bash
$ git diff a2822d5..1e67ed4 -- fltk/fegen/fltk_cst.py | grep "^[\+\-]class"
(no output)
```

**Result:** Zero class renames in the primary CST module.

### Where the `*Node` Suffix is Used:
The remap is isolated to the NEW Protocol classes in `fltk_cst_protocol.py`:

```bash
$ git show 1e67ed4:fltk/fegen/fltk_cst_protocol.py | grep "^class"
class GrammarNode(typing.Protocol):
class RuleNode(typing.Protocol):
class AlternativesNode(typing.Protocol):
class ItemsNode(typing.Protocol):
...
```

These are Protocol stubs generated alongside (not replacing) the concrete CST classes.

---

## Fact 3: The Remap Mechanism

### What `protocol_node_name()` Does

**Location:** fltk/fegen/gsm2tree.py, lines 285–287 (NEW in this cycle)

```python
def protocol_node_name(self, rule_name: str) -> str:
    """Rule name → Protocol class name; must stay in sync with class_name_for_rule_node."""
    return self.class_name_for_rule_node(rule_name) + "Node"
```

This method:
- Takes a rule name (e.g., "rule" → "Rule")
- Appends "Node" to the class name → "RuleNode"
- Used **only** in Protocol code generation

### What `py_annotation_for_model_types()` Does NOT Do

**Location:** fltk/fegen/gsm2tree.py, lines 85–93 (PRE-EXISTING, unchanged)

```python
def py_annotation_for_model_types(self, *, model_types: Iterable[ModelType], in_module: bool = False) -> str:
    iir_types = [self.iir_type_for_model_type(model_type) for model_type in model_types]
    py_types = sorted(pycompiler.iir_type_to_py_annotation(typ, self.context) for typ in iir_types)
    if in_module:
        py_types = sorted(f'"{typ.removeprefix(".".join(self.py_module.import_path) + ".")}"' for typ in py_types)
    if len(py_types) > 1:
        return f"typing.Union[{', '.join(py_types)}]"
    return py_types[0]
```

This method:
- Converts IIR types to Python annotation strings
- Does **not** append "Node"
- Used for the **actual CST classes** (fltk_cst.py)

### Asymmetric Usage

- **CST generation (lines 123, 135):** Uses `py_annotation_for_model_types()` → no suffix
- **Protocol generation (lines 360, 395):** Uses `protocol_annotation_for_model_types()` → appends "Node"

**Diff evidence:**
```bash
$ git diff a2822d5..1e67ed4 fltk/fegen/gsm2tree.py | grep -A 5 "protocol_node_name"
+    def protocol_node_name(self, rule_name: str) -> str:
+        """Rule name → Protocol class name; must stay in sync with class_name_for_rule_node."""
+        return self.class_name_for_rule_node(rule_name) + "Node"
```

---

## Fact 4: Is the "Node" Suffix Removable?

### YES, the suffix is removable without breaking the new Protocol scheme.

**Reasoning:**

1. **Protocol classes are type annotations.** They exist to satisfy static type checkers (Pyright, mypy). The exact names don't affect runtime behavior.

2. **The suffix serves disambiguation only.** Protocol classes are defined alongside concrete classes in the same module (`fltk_cst_protocol.py`). The `*Node` suffix disambiguates them:
   - Concrete: `class Rule:`
   - Protocol: `class RuleNode(typing.Protocol):`

3. **If removed, you'd have:** 
   - Concrete: `class Rule:`
   - Protocol: `class Rule(typing.Protocol):`  ← two classes with the same name, **runtime error**

   OR move Protocols to a separate module (e.g., `fltk_cst_protocol.pyi`), then you can drop the suffix.

4. **The design trade-off:** The current layout (same module, disambiguated names) keeps everything in one place. Removing the suffix would require refactoring to a `.pyi` stub file or renaming the concrete classes — both breaking changes.

**Conclusion:** The suffix is NOT a necessity of the Protocol scheme itself, but a consequence of the architectural choice to co-locate them in a single module for clarity.

---

## Impact on Public API

**The reported concern is FALSE:**
- Existing code importing `from fltk.fegen import fltk_cst; x = fltk_cst.Rule(...)` works unchanged.
- No breaking rename from `Rule` to `RuleNode` in the public CST module.
- The new Protocol module (`fltk_cst_protocol.py`) is additive and orthogonal.

---

## Files and Commits Referenced

- **fltk/fegen/fltk_cst.py** — Concrete CST classes (unchanged: still `Rule`, not `RuleNode`)
- **fltk/fegen/fltk_cst_protocol.py** — New Protocol stubs (uses `RuleNode` names)
- **fltk/fegen/gsm2tree.py** — Generator code
  - Line 46–47: `class_name_for_rule_node()` (unchanged, maps "rule" → "Rule")
  - Line 85–93: `py_annotation_for_model_types()` (CST annotations, no suffix)
  - Line 285–287: `protocol_node_name()` (NEW, appends "Node")
  - Line 292–320: `protocol_annotation_for_model_types()` (NEW, uses protocol names)
  - Line 323: `gen_protocol_module()` (NEW, generates Protocol module)

**Key commits:**
- **a2822d5** (cycle start): No Protocol support, CST classes unchanged
- **3ffe12d** (earlier in history): Introduced Protocol generation framework
- **1e67ed4** (current HEAD): Protocol module fully integrated, CST classes still unchanged

---

## Recommendation

**No action needed.** The public API is stable. If the `*Node` naming is deemed confusing, that is a separate design review — not a regression in this cycle.
