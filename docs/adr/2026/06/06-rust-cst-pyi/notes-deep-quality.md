Style: concise, precise, no padding. Audience: smart LLM/human.

---

**quality-1**

`fltk/fegen/gsm2tree.py:184` — `gen_py_module` adds `pyreg.Module(("fltk", "_native"))` to the concrete CST module's runtime imports (not TYPE_CHECKING-guarded). `pygen.module()` emits a bare `import fltk._native` statement (`fltk/pygen.py:22-30`). The protocol generator correctly gates it with `if typing.TYPE_CHECKING:` (`gsm2tree.py:476-484`), but the concrete module generator does not.

Verified: `import fltk.fegen.fltk_cst` now pulls `fltk._native` into `sys.modules` unconditionally (confirmed by runtime check). Before this diff, `fltk_cst.py` had no `import fltk._native` at the top level; the extension was loaded lazily and with a `try/except` fallback via `fltk.fegen.pyrt.span`. Now it fails hard on import if the Rust extension is absent.

**Consequence.** Any environment that imports a generated concrete CST module without having built the Rust extension (pure-Python CI, downstream users on the pure-Python backend, `make check` before `maturin develop`) now gets an `ImportError` or `ModuleNotFoundError` instead of the graceful span-selector fallback. The pattern will propagate: every downstream grammar that regenerates its concrete CST module will also acquire the hard runtime dependency.

**Fix.** Mirror the protocol generator: guard the `fltk._native` import under `if typing.TYPE_CHECKING:` in `gen_py_module`. The annotation `terminalsrc.Span | fltk._native.Span` is lazy under `from __future__ import annotations` (already emitted), so the guard is sufficient for pyright. If a runtime reference is needed (it isn't: the concrete module default-constructs `UnknownSpan` from `terminalsrc`, not from `fltk._native`), keep the try/except indirection via `fltk.fegen.pyrt.span` instead.

---

**quality-2**

`fltk/fegen/gsm2tree_rs.py:205` — `_pyi_annotation_for_model_types` declares `model_types: object` to suppress the pyright error at the call site, then uses `# type: ignore[arg-type]` on the forwarding call to `protocol_annotation_for_model_types(model_types=..., ...)` (`gsm2tree_rs.py:215`). The actual constraint is `Iterable[ModelType]`. Declaring `object` and suppressing the ignore silences the type system at both the parameter declaration and the forwarding call.

**Consequence.** Future callers of `_pyi_annotation_for_model_types` with the wrong type get no type error at the call site; future refactoring of `ModelType` or `protocol_annotation_for_model_types`'s signature silently breaks this path. The `type: ignore` will not be revisited because it appears to be suppressing a known-good call.

**Fix.** Import `ModelType` and `Iterable` and declare the parameter correctly: `model_types: Iterable[ModelType]`. Remove both the `object` declaration and the `# type: ignore[arg-type]`.

---

**quality-3**

`fltk/fegen/gsm2tree_rs.py:184,193` — Inside the per-label accessor loop in `generate_pyi`, `python_label = label.upper()` is assigned and then immediately `del python_label` with the comment `# only used for documentation`. It is not used for anything: it doesn't appear in any `lines.append` call, any format string, or any conditional in that loop body. The five `lines.append` calls in between use only `label` (lowercase) and `lann`. The `del` does not prevent the value from existing during iteration; it just removes the name at the end of each iteration.

**Consequence.** The variable assignment + deletion is dead code that misleads maintainers into thinking the ALL_CAPS label name is needed for something. When `append_{label}` method names need to change (e.g. to `append_{python_label}`), someone may incorrectly rely on `python_label` being available without checking it is deleted.

**Fix.** Remove both `python_label = label.upper()` and `del python_label`.

---

**quality-4**

`tests/test_fltk_native_stub.py:57-64` — `_stub_class_names()` is defined but never called anywhere in the file (confirmed by grep). It accesses `node.parent` (an attribute not present on AST nodes by default) without first running the parent-annotation walk that `_stub_classes_with_members()` performs at lines 75-78. If `_stub_class_names()` were called, every `node.parent` access would raise `AttributeError` with a misleading error.

The comment at line 74 ("annotate parents for `_stub_class_names()` above; also used here") suggests the function was intended to be called from `_stub_classes_with_members()`, but it is not: `_stub_classes_with_members()` does its own top-level `ClassDef` filter inline.

**Consequence.** Dead code with a latent bug: if anyone adds a call to `_stub_class_names()` (e.g. to refactor `test_runtime_classes_in_stub`), it silently returns wrong results or raises. The comment in `_stub_classes_with_members()` implies a relationship that does not exist.

**Fix.** Remove `_stub_class_names()` entirely. If a top-level-class-names helper is needed, either inline it (as the existing code does) or fix the parent-annotation dependency explicitly before using `.parent`.
