# Error-handling review: rust-cst-pyi (46a6639..c78a014)

Style: concise, precise, no padding. Audience: smart LLM/human.

---

## errhandling-1

**File:** `fltk/fegen/genparser.py:312-320`

**Broken path:** `gen_rust_cst` calls `_parse_grammar_raw(grammar_file)` and
`gsm2tree_rs.RustCstGenerator(grammar)` and `gen.generate_pyi(protocol_module)` and
`gen.generate()` — all four are outside any `try`/`except`.

`_parse_grammar_raw` calls `_read_and_parse_grammar`, which can raise (read failure,
grammar parse failure); those paths exit via `typer.Exit(1)` with messages. That part
is handled. But `RustCstGenerator.__init__` raises `ValueError` on invalid rule/label
identifiers, and `generate_pyi` / `generate` raise `RuntimeError` on missing models or
empty-model rules (`_rule_info`, `gsm2tree_rs.py:74-86`). Both propagate unhandled to
typer, which prints a raw traceback and exits non-zero with no CLI-friendly message.

**Why:** No `try`/`except` wraps the generator construction or the generation calls.
The existing handling only covers `output_file.write_text(src)` (line 322–325) and
`stub_path.write_text(pyi_text)` (lines 330–333).

**Consequence:** A malformed grammar (invalid identifier, or a grammar rule with an
empty model) produces a Python traceback on stderr instead of a clean `"Error: ..."` 
message and `Exit(1)`. The on-call engineer sees a Python stack frame rather than a
diagnostic pointing to the grammar file or rule name. The `ValueError` from the
identifier check does include the rule/label name, but it is displayed as a raw
exception rather than a structured CLI error.

**What must change:** Wrap `RustCstGenerator(grammar)`, `gen.generate_pyi(...)`, and
`gen.generate()` in a `try`/`except (ValueError, RuntimeError) as e` block; emit
`typer.echo(f"Error: {e}", err=True)` and `raise typer.Exit(1) from e`. This matches
the pattern already used for `_read_and_parse_grammar` failures elsewhere in the file.

---

## errhandling-2

**File:** `tests/test_fltk_native_stub.py:30-36`

**Broken path:** `_try_import_fegen_cst()` catches `except Exception` and returns `None`.

```python
def _try_import_fegen_cst() -> ModuleType | None:
    try:
        import fltk._native.fegen_cst as fc
        return fc
    except Exception:
        return None
```

**Why:** A bare `except Exception` swallows all import errors — `ImportError`,
`ModuleNotFoundError`, and also `AttributeError`, `RuntimeError`, or any Rust
panic-turned-PyO3-exception that fires during module initialization. These are
qualitatively different:

- `ModuleNotFoundError` / `ImportError` — extension not built yet. Correct to skip.
- Any other exception — the extension is importable but broken (e.g. a PyO3
  initialization panic, a missing `fltk._native` dep, ABI mismatch). Silently
  returning `None` causes all `@skip_if_no_native` tests to be silently skipped
  rather than failing loudly at the import site.

**Consequence:** A broken-but-present `fltk._native.fegen_cst` silently skips all B4
runtime-agreement tests. On-call has no signal that the extension exists but is
broken; CI shows "5 skipped" rather than a test failure. The condition under which
this fires (broken build artifact) is exactly when the tests are most needed.

**What must change:** Narrow the catch to `(ImportError, ModuleNotFoundError)`. Any
other exception from the import should propagate (or at minimum be logged with the
exception text so CI output is diagnosable). Example:

```python
try:
    import fltk._native.fegen_cst as fc
    return fc
except (ImportError, ModuleNotFoundError):
    return None
```

---

## errhandling-3

**File:** `tests/test_fltk_native_stub.py:57-64`

**Broken path:** `_stub_class_names()` uses `isinstance(node.parent, ast.Module)` where
`node.parent` is a dynamically injected attribute, but this function calls `ast.walk`
without first running the parent-annotation loop.

```python
def _stub_class_names() -> list[str]:
    tree = _parse_stub()
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and isinstance(node.parent, ast.Module)
        # type: ignore[attr-defined]
    ]
```

The parent-annotation loop (`child.parent = node`) only runs inside
`_stub_classes_with_members()`, not in `_stub_class_names()`. `_stub_class_names()`
creates its own fresh `tree` from `_parse_stub()` and iterates that tree. On the fresh
tree, `ast.ClassDef` nodes have no `.parent` attribute; accessing `node.parent` raises
`AttributeError`.

**Why:** Two separate `_parse_stub()` calls produce two separate trees. The
parent-annotation is on the tree created in `_stub_classes_with_members()`; the
`_stub_class_names()` function builds a fresh tree and walks it without annotating it.

**Consequence:** Any call to `_stub_class_names()` raises `AttributeError` at runtime.
This function is not called by any of the four test classes in this file (they all use
`_stub_classes_with_members()` or `_stub_top_level_names()`), so the crash is latent.
If a future test calls it, it will raise with no diagnostic message pointing to the
missing annotation step.

**What must change:** Either (a) annotate parents in `_stub_class_names()` before
walking, the same way `_stub_classes_with_members()` does; or (b) extract the
parse-and-annotate step into a shared helper so both functions receive an already-
annotated tree. The `# type: ignore[attr-defined]` comment does not suppress runtime
`AttributeError`; it is a static-analysis suppression only.

---

No other findings. The `.pyi` generation error paths in `gsm2tree_rs.py` (identifier
validation → `ValueError`, empty-model → `RuntimeError`, missing model → `RuntimeError`)
are all properly raised with full context. The `genparser.py` file-write error paths are
correctly wrapped. The `_KNOWN_RUNTIME_EXTRAS` allowlist is explicit and documented.
The `_try_import_fegen_cst` skip pattern mirrors `pyright_available` style as intended
except for the overbroad catch (errhandling-2 above).
