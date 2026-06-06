## Slop prepass — commit 60a9019

### slop-1
**File:** `fltk/fegen/gsm2tree.py:1207`
**Quote:** `"""Return the Protocol class name for a CST node (e.g. 'grammar' -> 'GrammarNode')."""`
**Problem:** Self-explanatory docstring restating the function name and its implementation. `protocol_node_name` already says exactly this; the example adds nothing not obvious from the signature and adjacent code.
**Consequence:** LLM-narration smell on generated infrastructure code; a reviewer scanning for intent gets noise instead of signal.
**Fix:** Remove the docstring, or replace with a non-obvious constraint ("Rule names are converted to PascalCase then suffixed with 'Node'; must stay in sync with `class_name_for_rule_node`.").

---

### slop-2
**File:** `fltk/fegen/gsm2tree.py:1210`
**Quote:** `"""Like py_annotation_for_model_types but emits Protocol node names (<Name>Node) for rule refs."""`
**Problem:** Docstring is a comparison to another function rather than a description of invariants or intent. "Like X but Y" is a definition-by-diff, useful only while writing the code; it doesn't help a future reader who hasn't just read X.
**Consequence:** Reads as in-progress notes left in production code.
**Fix:** Describe the contract directly: "Return a Python type annotation string for `model_types`, using `<Name>Node` for rule references (Protocol classes) and library-type annotations for everything else."

---

### slop-3
**File:** `fltk/fegen/gsm2tree.py:1227–1243`
**Quote:**
```python
def gen_protocol_module(self) -> ast.Module:
    """Generate a *_cst_protocol.py module with Protocol classes describing the CST module surface."""
    module = ast.parse("")
    assert isinstance(module, ast.Module)  # noqa: S101
    # from __future__ import annotations (must be first; defers annotation evaluation)
    module.body.append(pygen.stmt("from __future__ import annotations"))
```
**Problem:** The inline comment `# from __future__ import annotations (must be first; defers annotation evaluation)` is a narration comment — it restates what the immediately following line of code does and why, turning the code into a self-annotated transcript rather than clean code.
**Consequence:** LLM writing tell; inline comment is noisier than the code itself.
**Fix:** Remove the comment. The `from __future__ import annotations` call is self-evident; the constraint ("must be first") is already encoded by its position being appended before all other statements.

---

### slop-4
**File:** `fltk/fegen/gsm2tree.py:1263–1272`
**Quote:**
```python
        # span: fltk.fegen.pyrt.terminalsrc.Span
        klass.body.append(pygen.stmt("span: fltk.fegen.pyrt.terminalsrc.Span"))

        child_annotation = self.protocol_annotation_for_model_types(model_types=model.types)

        # children: list[tuple[<Label> | None, <ChildType>]]
        if labels:
            klass.body.append(pygen.stmt(f"children: list[tuple[typing.Optional[Label], {child_annotation}]]"))
        else:
            klass.body.append(pygen.stmt(f"children: list[tuple[None, {child_annotation}]]"))
```
**Problem:** Both inline comments (`# span: ...` and `# children: list[...]`) restate the string literal that immediately follows. They add zero information.
**Consequence:** Canonical LLM-narration tell; a reviewer sees the author explaining their own code to themselves.
**Fix:** Delete both comments.

---

### slop-5
**File:** `fltk/fegen/gsm2tree.py:1276–1296`
**Quote:**
```python
        # append
        append_fn = pygen.function(...)
        ...
        # extend
        extend_fn = pygen.function(...)
        ...
        # child
        ...
        child_fn = pygen.function("child", ...)
        ...
        # Per-label methods
        for label in labels:
```
**Problem:** Section comments `# append`, `# extend`, `# child`, `# Per-label methods` restate the variable name or the method name being built. None describe intent or non-obvious structure.
**Consequence:** Adds visual noise without aiding comprehension; pattern of LLM narrating its own loop.
**Fix:** Remove all four comments. The variable names and `pygen.function` calls are self-documenting.

---

### slop-6
**File:** `fltk/fegen/genparser.py:1176–1178`
**Quote:**
```python
    # Generate companion Protocol module
    shared_cst_protocol = output_dir / f"{base_name}_cst_protocol.py"
    if verbose:
        typer.echo("Generating CST Protocol module...")
```
**Problem:** `# Generate companion Protocol module` restates the variable name `shared_cst_protocol` and the echo message below it. The comment is a caption for a two-line block that already captions itself.
**Consequence:** Mild narration; unremarkable on its own but part of a broader pattern of over-commenting in this diff.
**Fix:** Remove the comment.

---

### slop-7
**File:** `fltk/plumbing.py:1763–1766`, `fltk/plumbing.py:1776–1782`, `fltk/unparse/genunparser.py:1841–1843`, `fltk/test_plumbing.py:1812–1814`, `fltk/fegen/genparser.py:1160–1162`
**Quote (representative):**
```python
        # result.result is a concrete fltk_cst.Grammar; cast to GrammarNode to satisfy the
        # visit_grammar annotation. The nested-Label nominal mismatch applies here too
        # (same as the default _default_cst binding in Cst2Gsm.__init__).
        return cst2gsm.visit_grammar(cast("cstp.GrammarNode", result.result))
```
**Problem:** The same cast explanation appears five times across five files with nearly identical wording. The explanation is legitimate for one canonical site; repeating it verbatim at every call site is LLM copy-paste narration. Subsequent sites say "same pattern as plumbing.py" — i.e., they explicitly cross-reference instead of documenting the local contract.
**Consequence:** Reviewer must read the same paragraph five times; "same pattern as" cross-references add fragility (if plumbing.py changes, the cross-references go stale). Strongly reads as generated content.
**Fix:** Keep the explanation at `_DEFAULT_CST` in `fltk2gsm.py` (where the constraint lives). At call sites, a one-liner suffices: `# nominal nested-Label mismatch; see _DEFAULT_CST in fltk2gsm.py` — or no comment, since `cast` at a function-call boundary is self-explanatory when the Protocol is well-named.

---

### slop-8
**File:** `fltk/fegen/test_cst_protocol.py:1404`
**Quote:** `def run_pyright(file_path: pathlib.Path, *, pyright_available: bool) -> list[dict]:  # type: ignore[type-arg]`
**Problem:** `# type: ignore[type-arg]` on a module-level helper suppresses a type error rather than fixing it. `list[dict]` is missing its type parameters, which is the error being suppressed. This is a silent fallback that hides an imprecision in the return type.
**Consequence:** The return type is unspecified; callers downstream doing `d.get("severity")` etc. operate on `Any`-keyed dicts without type safety. The `type: ignore` is a "just in case" suppression with no explanation of why the proper type (e.g. `list[dict[str, Any]]`) cannot be used.
**Fix:** Replace `list[dict]` with `list[dict[str, Any]]` (importing `Any` from `typing`) and remove the `type: ignore`.
