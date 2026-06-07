## quality findings — native span / native constructors / source-loss fix / gencode

Commit range: f8fdb53..1b54878

---

### quality-1

**File:line:** `crates/fltk-cst-core/src/span.rs:140–150` (`source_as_py`) and `:157–168` (`text_str`)

**Issue:** Both `source_as_py` and `text_str` are `pub` functions added to `Span` in this diff but are never called anywhere in the codebase — not in the generator, not in generated code, not in tests. `source_as_py` was the originally-planned approach for cross-cdylib source preservation; the cross-cdylib type-mismatch bug forced a switch to `source_full_text_str` + `get_source_text_type` instead. `text_str` has no caller at all.

**Consequence:** Both methods expand the permanently-committed public API surface of `fltk-cst-core` with no consumer. Downstream Rust crates that depend on this rlib will see them as stable API. Future maintainers trying to understand the source-preservation strategy will be confused by `source_as_py` (which sounds like the right approach but cannot work due to the cross-cdylib issue) sitting alongside `source_full_text_str` (which is the actual approach). The dead methods will propagate into every downstream crate's autocomplete and docs.

**Fix:** Remove `text_str` and `source_as_py` from `span.rs`. If `source_as_py` needs to stay as a hint for future work (e.g., if the cross-cdylib issue is ever resolved via `Span::with_source_arc`), add a doc comment explaining exactly why it cannot be used yet and a `TODO(slug)` linking to `TODO.md`.

---

### quality-2

**File:line:** `fltk/fegen/gsm2tree_rs.py:392`

**Issue:** The comment `# Note: py is always needed when has_span (source_as_py requires py token).` is wrong. `source_as_py` is not called in the generated `to_pyobject` code — `py` is needed because `get_source_text_type(py)` is called when the span has source. The comment references the abandoned approach (quality-1 above).

**Consequence:** The comment will mislead anyone who reads the generator code trying to understand why `py` is not underscored when `has_span`. It becomes more confusing if `source_as_py` is removed (quality-1 fix), leaving a dangling reference.

**Fix:** Replace with: `# Note: py is always needed when has_span because get_source_text_type(py) is called in the source-bearing branch.`

---

### quality-3

**File:line:** `fltk/fegen/fltk2gsm.py:24–37` (`_span_text`)

**Issue:** `_span_text` was added as a transitional compatibility shim: if `span.text()` returns `None` (sourceless Python-backend span), fall back to `self.terminals[span.start:span.end]`. The docstring says the fallback is needed "until [fltk_parser.py] is regenerated with source-bearing spans." But `fltk_parser.py` has already been regenerated (it now emits `Span.with_source(...)` in every terminal match), making the `return self.terminals[span.start:span.end]` branch dead code. There is no `TODO(slug)` entry marking this for removal.

**Consequence:** Every new `visit_*` method added to `Cst2Gsm` must use `_span_text` instead of a direct terminals slice (the comment doesn't say this requirement is permanent or transient). If the shim is never cleaned up, it becomes the permanent pattern even though it serves no purpose. Future callers will copy the pattern without understanding whether it's still needed.

**Fix:** Now that `fltk_parser.py` is regenerated, remove `_span_text` and revert the three call sites back to `self.terminals[span.start:span.end]`. If bootstrap compatibility with a pre-regen parser is still required for some path, add a `TODO(slug)` entry in `TODO.md` with the specific removal trigger.

---

### quality-4

**File:line:** `fltk/fegen/gsm2parser.py:262–265` (`_make_span_expr`)

**Issue:** The `_make_span_expr` helper constructs a class method call via `VarByName(name="fltk.fegen.pyrt.span.Span", ...)` — a stringly-typed dotted module path used as a "variable name" that the Python codegen emits verbatim. The `TerminalSpanType` is already registered in the type registry with module `("fltk", "fegen", "pyrt", "span")` and name `"Span"`. The helper bypasses that registry and hardcodes the path as a string literal instead of deriving it from the registered type info.

**Consequence:** If the `Span` module path ever changes (e.g., the backend-selector module is moved or renamed), this string must be updated manually with no type-system or registry enforcement pointing to it. The pre-existing uses of `VarByName` in this file all used simple identifiers (`"pos"`, `"result"`, etc.); this introduces the new pattern of using dotted module paths as names, which will propagate to any future `_make_X_expr` helper that needs a cross-module class reference.

**Fix:** Either (a) derive the path from the registry: look up `self.TerminalSpanType` in `self.context.python_type_registry` to get the `TypeInfo`, then construct the qualified name as `f"{'.'.join(type_info.module.path)}.{type_info.name}"`; or (b) store the qualified class name as a class constant on `ParserGenerator` (e.g., `_SPAN_CLASS_EXPR`) derived once from the registered type info so it's a single update point.

---

### quality-5

**File:line:** `Makefile:63` (`TODO(gencode-poc-fltkg)`)

**Issue:** The `gencode` target contains `# TODO(gencode-poc-fltkg): src/cst_generated.rs is generated from a hand-built PoC grammar...` but there is no corresponding entry in `TODO.md`. This violates the project's two-piece TODO system (CLAUDE.md: "Adding a TODO requires both an entry in `TODO.md` and a `TODO(slug)` comment at the relevant location").

**Consequence:** The TODO system is the only tracking mechanism for deferred work. A slug with no `TODO.md` entry is invisible to anyone scanning the master list for open work. The gencode reproducibility contract has a permanent manual exception (the PoC grammar) that will be forgotten as a tracked item.

**Fix:** Add a `TODO.md` entry for `gencode-poc-fltkg` describing the work: creating a `.fltkg` source file for the PoC grammar so `make gencode` can regenerate `src/cst_generated.rs` from a first-class grammar source rather than an inline Python function.

---

### quality-6

**File:line:** `fltk/fegen/gsm2tree_rs.py:518` (generator); reflected in all generated `*Child` types

**Issue:** `children_native()` is generated to return `&Vec<(LabelType, ChildEnum)>` instead of `&[(LabelType, ChildEnum)]`. Returning `&Vec` exposes the concrete container type rather than a slice, which is non-idiomatic Rust (clippy lint `clippy::ptr_arg` flags `&Vec<T>` return types; the lint suppression was not added here).

**Consequence:** Every generated node type exposes `&Vec` as a permanent API shape. Downstream Rust code that pattern-matches on the return type (e.g., `let v: &Vec<_> = node.children_native()`) will be coupled to the concrete type. Changing to `&[...]` later is a breaking API change. The pattern will also propagate: new node types generated from new grammars will all have the same issue.

**Fix:** Change the generator line to emit `pub fn children_native(&self) -> &[(label_type, enum_name)]` and the body to `self.children.as_slice()`. `Vec<T>` coerces to `&[T]` via `Deref`, so no generated call sites break.
