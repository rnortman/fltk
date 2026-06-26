# Quality review notes — pure-python-span-native-probe

Commit reviewed: `ab38ec777920f4761f124e56b3cedc995acee46a`
Design inputs: `design.md`, `design-delta-python-rust-isolation.md`

---

## quality-1

**File:** `fltk/fegen/gsm2parser.py:146–151`

**Issue:** The `_source_text_init` expression uses a module-level `VarByName` to reference
`fltk.fegen.pyrt.terminalsrc`, but types it as `self.SourceTextType` instead of
`iir.Type.make(cname="module")`.

```python
_source_text_init = iir.MethodAccess(
    "SourceText",
    iir.VarByName(
        name="fltk.fegen.pyrt.terminalsrc",
        typ=self.SourceTextType,   # ← names the MODULE, but typed as SourceText
        ...
    ),
).call(text=..., filename=...)
```

The established convention for module-reference `VarByName`s throughout the codebase is
`typ=iir.Type.make(cname="module")` — used at five sites in `fltk/unparse/gsm2unparser.py`
(lines 366, 375, 390, 960, 1760) whenever a VarByName refers to a module rather than a value.
`_make_span_expr` in the same file does it differently again: the span VarByName uses the full
dotted class path (`name="fltk.fegen.pyrt.terminalsrc.Span"`) typed as the class's IIR type —
correctly, because that VarByName IS the class reference.  In `_source_text_init` the VarByName
names the MODULE, so `typ=self.SourceTextType` is semantically wrong.

**Consequence:** The IIR `typ` field on the module VarByName misrepresents what the expression
denotes.  If the IIR compiler uses `typ` for sub-expression type inference (e.g., to determine
the return type of the enclosing `MethodAccess`), it gets the wrong answer.  More broadly,
this establishes a third pattern for emitting fixed constructor calls — module VarByName typed
as the class, module VarByName typed as `"module"`, full-path class VarByName — in a generator
that already has two.  Future contributors adding construction sites will pick one of these
inconsistent examples.

**Fix:** Replace `typ=self.SourceTextType` with `typ=iir.Type.make(cname="module")` to match
the module-VarByName convention, OR refactor to use the same full-path class VarByName pattern
`_make_span_expr` uses: `iir.VarByName(name="fltk.fegen.pyrt.terminalsrc.SourceText",
typ=self.SourceTextType, ...)` followed by `.call(text=..., filename=...)`.  Either removes
the third competing pattern.

---

## quality-2

**File:** `fltk/fegen/test_cst_protocol.py:271–274` (`test_committed_protocol_source_names_no_native_no_selector`)

**Issue:** The protocol-module check uses a broad substring search:

```python
assert "fltk._native" not in PROTOCOL_MODULE.read_text()
```

The companion test `test_committed_cst_source_imports_no_native_no_selector` (same file,
~line 315) uses the more targeted line-level import check:

```python
native_imports = [ln for ln in lines if ln.strip() == "import fltk._native"]
assert not native_imports, ...
```

These two tests guard the same property (no `fltk._native` reference in generated output)
but with different precision.

**Consequence:** The broad `in` search fails if `fltk._native` appears anywhere in the
protocol module — including explanatory comments, docstrings, or string literals.  A developer
who adds a comment like `# formerly had fltk._native.Span here` to the generated protocol will
trigger a CI failure with no obvious cause.  The two tests in the same file already diverge
in methodology, which signals to a reader that they're testing different things when they're
testing the same thing.

**Fix:** Replace the broad search with line-level import checks matching the CST test:

```python
lines = PROTOCOL_MODULE.read_text().splitlines()
native_imports = [ln for ln in lines if ln.strip() == "import fltk._native"]
assert not native_imports, "Protocol module must not import fltk._native"
selector_imports = [ln for ln in lines if ln.strip() == "import fltk.fegen.pyrt.span"]
assert not selector_imports, "Protocol module must not import the span selector"
```

---

## quality-3

**File:** `fltk/fegen/genparser.py:21` and `fltk/plumbing.py:649`

**Issue:** Two different mechanisms are used to insert `from __future__ import annotations`
into generated parsers.

`genparser.py` (committed parser files) uses the code-generator's text-level helper:
```python
parser_mod.body.insert(0, pygen.stmt("from __future__ import annotations"))
```

`plumbing.py` (in-memory exec'd parsers) uses raw AST construction:
```python
future_import = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
parser_module = ast.fix_missing_locations(ast.Module(body=[future_import, parser_class_ast], ...))
```

Additionally, `plumbing.py`'s `ast.alias` omits `asname=None`, while the identical
construction in `gsm2unparser.py` (line 1845) passes it explicitly:
`ast.alias(name="annotations", asname=None)`.

**Consequence:** Two code paths that must stay in sync use divergent styles.  If the future
import ever needs to change (e.g., adding a second `__future__` import for 3.13 compatibility,
or adding source-location metadata), both paths must be updated independently, in two
different coding idioms, with no mechanical link to remind a maintainer.  The style
inconsistency also makes the diff harder to audit: a reader verifying "both parsers get the
same future import" must mentally translate between the two representations.

**Fix:** Factor out a small shared helper (e.g., `_make_future_annotations_import() ->
ast.ImportFrom`) used by both `genparser.py` and `plumbing.py`, or at minimum make
`plumbing.py` use the same `ast.ImportFrom(..., names=[ast.alias(name="annotations",
asname=None)])` form as `gsm2unparser.py`.

---

## Assessment: `src/lib.rs` gencode drift (`fltk._native.LineColPos`)

The implementation log deliberately excludes a pre-existing `src/lib.rs` drift that drops the
`fltk._native.LineColPos` export.  This change does not introduce the drift; it was present at
base commit `49e9701`.

Leaving it out-of-scope is the right call for this change.  The dropped export is a Rust-side
detail orthogonal to the Python pipeline isolation goals.  No code path introduced or modified
here invokes `fltk._native.LineColPos` as an importable runtime name; the `SpanProtocol`
`line_col()` return annotation (`terminalsrc.LineColPos | None`) refers to the Python type
throughout.  The `TODO(spanprotocol-native-linecol)` is properly recorded in both `TODO.md`
and `span_protocol.py`, and the design-delta (D5.2/D8) explicitly bounds the gap.

The one latent risk worth noting: the `fltk/_native/__init__.pyi` stub still declares
`LineColPos` (for pyright), so static analysis accepts `from fltk._native import LineColPos`
even though the runtime `.so` does not export it.  If any downstream consumer or test imports
that name, they get an `AttributeError` at runtime that `make check` would not catch.  The
risk is real but contained to callers of `.line_col()` on native spans who try to import the
return type class — a narrow path.  The proper closure is the `spanprotocol-native-linecol`
TODO; deferring it is reasonable here.
