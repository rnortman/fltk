# Phase 4 Runtime Integration: Design

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Scope and authority: this design realizes the requirements at
`docs/adr/2026/05/28-pyo3-phase4-runtime-integration/requirements.md`. It does not
restate them; it refers. Where requirements are authoritative (the API Contract, the
acceptance criteria, the resolved selection surface), this doc honors them and resolves
the design-owned questions (artifact build mechanism, module-name stability,
`register_classes` module-population mechanism, the consumer injection seam).

Framing (`requirements.md` "Framing", `notes-design-user.md`): FLTK is a framework for
generating parsers and CST that live in a **user application**, not in `fltk`. Users
control the module name and the build process. **The central capability of this phase is
backend selection**: when FLTK parses a grammar, the caller chooses the Rust CST backend
or the Python CST backend, and that selection reaches the *real* code that consumes CST
(`fltk2gsm.Cst2Gsm`, the fegen parser). Modifying those consumers to add the seam is in
scope. FLTK dogfooding its own `fegen` grammar is one secondary test case of the general
capability.

---

## Root Cause / Context

Two FLTK entry points construct and consume CST, and both are statically bound to the
Python dataclass backend:

1. **`plumbing.generate_parser`** (`plumbing.py:86-147`) — for an *arbitrary user
   grammar* — builds a Python AST with `gsm2tree.CstGenerator.gen_py_module()`
   (line 102), `exec()`s it into `cst_globals` (line 105), copies public names onto a
   fresh `types.ModuleType` (lines 108-111), registers it in `sys.modules` (line 112),
   and injects `cst_globals` into the parser's exec namespace (line 127). There is no way
   to swap in a pre-compiled Rust CST module.

2. **`plumbing.parse_grammar`** (`plumbing.py:34-60`) — FLTK's *own* fegen-grammar parse
   path — constructs `fltk_parser.Parser` (which builds Python `fltk_cst` nodes via 151
   fully-qualified `fltk.fegen.fltk_cst.*` references) and hands the resulting CST to
   `fltk2gsm.Cst2Gsm` (line 59), which is itself statically bound: `from fltk.fegen import
   fltk_cst as cst` (`fltk2gsm.py:4`), with `cst.Item`, `cst.Items.Label.NO_WS`,
   `isinstance(item, cst.Item)`, etc. throughout. The CST backend is hardwired to Python.

The deliverable: the caller CAN CHOOSE Rust or Python CST at *both* entry points. For (1)
this means importing a user-built standalone extension and reading its classes. For (2)
this means parsing the fegen grammar with a Rust fegen CST extension and running the
*real* `Cst2Gsm` against the Rust-backed nodes. Running the real consumer on the Rust
backend requires editing `Cst2Gsm` (and the fegen parser construction) to add a
backend-selection seam — explicitly in scope (`requirements.md` In Scope; this supersedes
the old "static consumers unmodified" constraint).

### Build-architecture constraint (shared by both paths)

The generated Rust references `crate::UNKNOWN_SPAN` (`gsm2tree_rs.py:127` emits
`use crate::UNKNOWN_SPAN;`; every `#[new]` uses `UNKNOWN_SPAN.get(py)`,
`gsm2tree_rs.py:232-235`). That symbol is `pub(crate) static UNKNOWN_SPAN` in `lib.rs:10`,
and `Cargo.toml:8` declares `crate-type = ["cdylib"]` only — no `rlib`. A separately
compiled extension cannot link `crate::UNKNOWN_SPAN`. The standalone-artifact requirement
forces resolving this, not deferring it.

### Key enabling fact: the only `crate::` coupling is the default `UnknownSpan` *value*

The generated node struct stores `span: PyObject` (`gsm2tree_rs.py:194`) and
`children: Py<PyList>` (`:196`) — both Python objects, not Rust-typed `Span`. Every span
operation (`__eq__`, `__repr__`) goes through `self.span.bind(py).eq(...)` / `.repr()`
(`gsm2tree_rs.py:426-432, 446-452`) — duck-typed Python dispatch. **A user extension never
links the Rust `Span` type.** The *sole* crate-internal dependency is the default sentinel
used when `span=None`: `UNKNOWN_SPAN.get(py)`. That sentinel is already exposed *as a
Python object* on the FLTK extension: `m.add("UnknownSpan", ...)` (`lib.rs:25`), importable
as `fltk._native.UnknownSpan`. So the default can be obtained at runtime with a plain
Python import — no Rust-level linkage. This makes a standalone user extension feasible
with a *localized generator change* rather than a build-system restructure.

---

## Resolved design questions

### artifact-build-mechanism → Option B (standalone user extension, runtime-import sentinel)

**Decision.** A user grammar's Rust CST is compiled into a **standalone Python extension
module that the user names, builds, and installs** — independent of FLTK's crate, FLTK's
`lib.rs`, and FLTK's module namespace. It depends on `fltk._native` only at *runtime* (for
`UnknownSpan` and, transitively, the `Span` type the parser constructs), never at *link*
time.

**Generator change.** `gsm2tree_rs.py` is modified to remove the `crate::` coupling:

- Drop `use crate::UNKNOWN_SPAN;` from `_preamble()` (`gsm2tree_rs.py:127`).
- In `_new_method()` (`gsm2tree_rs.py:225-243`), replace the `UNKNOWN_SPAN.get(py)`
  default with a runtime fetch of the sentinel from the FLTK extension, cached in a
  module-local `GILOnceCell<PyObject>` so the import cost is paid once per process:

  ```rust
  None => UNKNOWN_SPAN_CACHE
      .get_or_try_init(py, || -> PyResult<PyObject> {
          Ok(py.import("fltk._native")?.getattr("UnknownSpan")?.unbind())
      })?
      .clone_ref(py),
  ```

  with a file-level `static UNKNOWN_SPAN_CACHE: GILOnceCell<PyObject> = GILOnceCell::new();`
  emitted in the preamble (replacing the `use crate::UNKNOWN_SPAN;` line).

This is exploration Option B (line 138). Caching makes construction cost ~one `GILOnceCell`
read after the first call. The change is small and localized to two methods.

**Why this and not the alternatives** (exploration lines 130-144):
- **Option A/E (submodule of `fltk._native`) — rejected by the framing.** Makes the user's
  CST live under `fltk._native`, named by FLTK, requiring hand-edits to FLTK's `lib.rs` and
  a full rebuild per user grammar — the exact anti-pattern the framing names. (It remains a
  valid *internal* mechanism for FLTK's own fegen Rust CST fixture but is not the
  user-facing mechanism.)
- **Option C (export `UNKNOWN_SPAN` C-ABI / add `rlib`)** conflicts with `cdylib`-only and
  needs a second build product. Heavier than B for no benefit, since B needs no linkage.
- **Option D (shared `fltk-cst-common` rlib + Cargo workspace)** is a build-system
  restructure — the cleaner long-term answer *if* user extensions ever need to link
  Rust-level shared types (none today). Recorded as `TODO(rust-cst-shared-rlib)`.

**Build is the user's, not FLTK's.** The user writes their own `Cargo.toml`
(`crate-type = ["cdylib"]`), their own crate with a `#[pymodule]` whose init calls the
generated `register_classes`, and builds with their tool. FLTK provides: (1) the `.rs`
emitter (`gen-rust-cst`), (2) the `register_classes` contract, (3) documentation of the one
runtime dependency. FLTK does **not** dictate the user's crate layout, module name, or
build tool. FLTK's Makefile targets are for FLTK's own test/dogfooding artifacts only.

### module-name-stability → user-named importable module

**Decision.** The Rust backend (for `generate_parser`) is referenced by a **user-supplied
dotted module name** (e.g. `"mypkg.mygrammar_cst"`), the importable extension the user
built. It is not `fltk._native.<submodule>` and not the per-call
`fltk_grammar_{id(grammar)}` name.

For the **parser↔unparser coupling** (`cst_module_name` threaded `ParserResult` →
`generate_unparser`): Phase 4 keeps a per-call name `fltk_grammar_{id(grammar)}` for the
**CST module object** registered in `sys.modules` (the `types.ModuleType` the unparser
imports). The user's Rust module is the *source* of class objects; the per-call
`types.ModuleType` is the *binding target*. Rust path: import the user's module, read its
public classes, set them as attributes on a fresh `types.ModuleType("fltk_grammar_{id}")`,
register *that* in `sys.modules`. Coupling string unchanged for both backends.

### register-classes-module-type → user extension owns module creation (option (c))

The requirements pin the end state (classes on `sys.modules[cst_module_name]`) and leave
the population mechanism open (exploration Q5). `register_classes`'s signature is
`pub fn register_classes(module: &Bound<'_, PyModule>)` (`gsm2tree_rs.py:462`).

**Decision.** Phase 4 does **not** call `register_classes` from Python. The user's
extension calls it inside its own `#[pymodule]` init against its own module object (exactly
as `fltk._native`'s init calls `cst_fegen::register_classes(&fegen_sub)` at `lib.rs:36` for
FLTK's fegen fixture). By the time the Python runtime imports the user's module, it is
already populated. The runtime **reads classes off the imported user module** and copies
them onto the per-call `types.ModuleType`. This sidesteps Q5 (no Python-created module is
handed to `register_classes`). The runtime mechanism is plain attribute copy —
`setattr(cst_module, name, obj)` per public class.

### consumer-injection-seam → dependency injection of the CST namespace

The directive (Directive 2) and `requirements.md` ("Consumer injection seam") make
modifying the real consumers in scope. The seam is **dependency injection of the CST
namespace**, not module re-export and not runtime monkeypatching.

**`Cst2Gsm` (`fltk2gsm.py`).** Replace the module-level `from fltk.fegen import fltk_cst as
cst` (line 4) with an injected namespace held on the instance:

```python
from fltk.fegen import fltk_cst as _default_cst   # default backend

class Cst2Gsm:
    def __init__(self, terminals, cst=_default_cst):
        self.terminals = terminals
        self.cst = cst
```

Every bare `cst.X` reference in the methods (e.g. `cst.Items.Label.NO_WS` at line 37,
`isinstance(item, cst.Item)` at line 53, `cst.Disposition.Label.INCLUDE` at line 104)
becomes `self.cst.X`. The module-level `cst` alias is removed. `self.cst` is the namespace
object providing the node classes and their `.Label` attributes; for the Python backend it
is the `fltk_cst` module, for the Rust backend it is the imported fegen Rust extension
module (or a `types.ModuleType` populated from it — see below). The default keeps every
existing caller (`genparser.py:52`, `genunparser.py:45`, the existing tests) working with
**zero changes** and the same Python behavior.

**Why DI, not re-export.** A re-export (`fltk_cst.py` re-exporting from a Rust module)
would force a *single* global backend choice for the whole process and break the Python
default; it cannot offer per-call selection. DI lets the *same* `Cst2Gsm` source run
against either backend, chosen per call — which is exactly the requirement. The prior
design's `TODO(rust-cst-fltk-reexport)` deferral (and its hand-written-substitute dodge for
AC8) is **removed**; the real `Cst2Gsm` runs on both backends via this seam.

**The fegen parser path (`parse_grammar`).** `parse_grammar` selects a fegen CST backend
and must (a) construct fegen CST nodes with that backend's classes and (b) inject that
backend's namespace into `Cst2Gsm`. The committed Python `fltk_parser.Parser` constructs
nodes via hardcoded `fltk.fegen.fltk_cst.*` names (151 sites) and is a *generated* file.

**Decision: reuse the `generate_parser` Rust path against the fegen grammar at runtime.**
Rather than parameterize `fltk_parser.py`'s 151 references (rejected: editing a generated
file's references and re-running codegen for both backends), the Rust fegen path calls
`generate_parser(fegen_grammar, rust_cst_module=...)`, which already produces a
backend-correct parser: the generated parser constructs nodes from `parser_globals[ClassName]`,
which are the Rust classes read off the imported fegen extension. `parse_grammar` then runs
`Cst2Gsm(terminals, cst=pr.cst_module)` against the parser's output. The classes the parser
constructs and the classes injected into `Cst2Gsm` are the *same* Rust objects, so
`isinstance` dispatch in `Cst2Gsm` resolves (type-identity invariant).

`parse_grammar(rust_fegen_cst_module=...)` does:

```python
def parse_grammar(grammar_text, *, rust_fegen_cst_module=None):
    terminals = terminalsrc.TerminalSource(grammar_text)
    if rust_fegen_cst_module is None:
        parser = fltk_parser.Parser(terminalsrc=terminals)   # Python, unchanged
        cst_ns = _default_cst                                 # fltk_cst module
    else:
        # Rust backend: build a fegen parser bound to the Rust fegen CST module.
        fegen_grammar = _load_fegen_grammar()                 # the committed fegen GSM
        pr = generate_parser(fegen_grammar, rust_cst_module=rust_fegen_cst_module)
        parser = pr.parser_class(terminals)
        cst_ns = pr.cst_module                                # same Rust classes
    result = parser.apply__parse_grammar(0)
    # ... existing error handling ...
    cst2gsm = fltk2gsm.Cst2Gsm(terminals.terminals, cst=cst_ns)
    return cst2gsm.visit_grammar(result.result)
```

`pr.cst_module` is the per-call `types.ModuleType` whose attributes are the *same* Rust
class objects the generated parser constructs nodes from — so injecting it into `Cst2Gsm`
satisfies the type-identity invariant for `isinstance`/label dispatch. The Python path is
byte-for-byte unchanged when no Rust module is supplied.

`_load_fegen_grammar()` parses `fegen.fltkg` (the committed grammar source) via the Python
path once; it must avoid infinite recursion (it itself calls `parse_grammar` with the
default Python backend — terminating because the default path takes no Rust branch). The
fegen grammar is small and parsed once; cache it at module scope if cost matters.

---

## Proposed Approach

### Modified files

| File | Change |
|---|---|
| `fltk/plumbing.py` | Add `rust_cst_module` to `generate_parser`; factor CST-module population into a backend branch; add `_load_rust_cst_classes` + `RustBackendUnavailableError`. Add `rust_fegen_cst_module` (backend selector) to `parse_grammar`/`parse_grammar_file`; route to a Rust-backed fegen parser + inject the namespace into `Cst2Gsm`. Add `_load_fegen_grammar`. |
| `fltk/fegen/fltk2gsm.py` | Replace module-level `from fltk.fegen import fltk_cst as cst` with an injected `cst` namespace on `Cst2Gsm.__init__` (default = `fltk_cst` module). Change all `cst.X` → `self.cst.X`. |
| `fltk/fegen/gsm2tree_rs.py` | Remove `crate::UNKNOWN_SPAN` coupling: emit a module-local `GILOnceCell` sentinel cache + runtime import of `fltk._native.UnknownSpan` (two methods: `_preamble`, `_new_method`). Enables standalone user extensions. |
| `fltk/fegen/genparser.py` | Add a `gen-rust-cst` subcommand that **only emits `.rs` source** (no compile). |
| `Makefile` | Add targets for FLTK's *own* test artifacts: emit `.rs`, build `fltk._native`, build the standalone non-FLTK fixture extension, build the fegen Rust CST extension. Documented as FLTK-internal, not the user build recipe. |
| `src/cst_fegen.rs`, `src/cst_generated.rs` (regenerated) + `src/lib.rs` | Regenerate both committed generated `.rs` under the new sentinel scheme; verify FLTK's fegen Rust CST still works. (FLTK-internal only.) |
| `docs/` | A user-facing "Build a Rust CST extension for your grammar" guide. |

No changes to `plumbing_types.py` (no new `ParserResult` field), `gsm2tree.py`, or
`gsm2unparser.py`. The formatter CST modules (`unparsefmt_cst.py`, `toy_cst.py`,
`fmt_config.py`) are **not** modified — backend selection for the formatter pipeline is out
of scope (`requirements.md` Out of Scope); they remain Python-only.

**`gsm2tree_rs.py` is modified** — required by the standalone-artifact requirement. The
change is small, localized, and does not alter the Python-visible CST API. FLTK's own
`cst_fegen.rs` and `cst_generated.rs` must be regenerated and re-verified.

**`fltk2gsm.py` is modified** — required by the consumer-injection-seam requirement (the
real `Cst2Gsm` must run on both backends). The change is mechanical (`cst.` → `self.cst.`)
with a default-valued `__init__` parameter, so default behavior and all existing callers
are unaffected.

### `generate_parser` signature and Rust-backend path

```python
def generate_parser(
    grammar: gsm.Grammar,
    *,
    capture_trivia: bool = True,
    rust_cst_module: str | None = None,
) -> ParserResult:
    ...
```

- `rust_cst_module is None` → Python backend (default, current behavior exactly).
- `rust_cst_module` is a dotted module name → Rust backend; that module is imported and its
  public classes are read off it.

Replaces only steps (b)-(c) of the current flow. The `CstGenerator` is still constructed
(needed by `ParserGenerator`, `plumbing.py:114`); only `gen_py_module()` + `exec()` are
skipped:

```python
context = create_default_context(capture_trivia=capture_trivia)
grammar_with_trivia = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))
cstgen = gsm2tree.CstGenerator(grammar=grammar_with_trivia, py_module=pyreg.Builtins, context=context)

module_name = f"fltk_grammar_{id(grammar)}"
cst_module = types.ModuleType(module_name)

if rust_cst_module is None:
    cst_module_ast = cstgen.gen_py_module()
    cst_globals = {}
    exec(compile(cst_module_ast, "<cst_module>", "exec"), cst_globals)
    public = {k: v for k, v in cst_globals.items() if not k.startswith("_")}
else:
    public = _load_rust_cst_classes(rust_cst_module)  # hard-error on failure

for name, obj in public.items():
    setattr(cst_module, name, obj)
sys.modules[module_name] = cst_module

parser_globals.update(public)   # replaces `parser_globals.update(cst_globals)`
```

`public` is the single dict both backends produce; it feeds both the `types.ModuleType`
population and the parser-namespace injection.

**Contract: `public`'s CST contribution to `parser_globals` is class names only.** The
generated parser references `Span`, `terminalsrc`, `typing`, `fltk` from `parser_globals`'s
own seed (`plumbing.py:118-126`) and CST nodes only by class name. The Python path's
`public` additionally carries `dataclasses`/`enum`/`typing`/`fltk` module objects (harmless,
re-supplied by the seed); the Rust path's `isinstance(obj, type)` filter drops module
objects. Both are safe because the parser depends on the CST module only for class names.
AC1 is the guard.

```python
def _load_rust_cst_classes(module_name: str) -> dict[str, object]:
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        # ImportError covers ModuleNotFoundError (missing user module) and ABI /
        # Python-version mismatch on the .so. Deliberately NOT `except Exception`: a
        # genuine bug raised during the user extension's init must propagate as itself.
        raise RustBackendUnavailableError(module_name) from exc
    classes = {
        name: obj
        for name, obj in vars(module).items()
        if not name.startswith("_") and isinstance(obj, type)
    }
    if not classes:
        raise RustBackendUnavailableError(module_name, detail="module loaded but exposes no CST classes")
    return classes
```

The filter mirrors `plumbing.py:110` (`not name.startswith("_")`) and additionally restricts
to `type` objects. The Rust module's `__dict__` exposes the `*_Label` enum types at top
level (the Python backend nests them as `ClassName.Label`); including them is harmless (no
name collision, nothing references the top-level alias).

### `parse_grammar` backend selection (FLTK's fegen path)

As specified in "consumer-injection-seam → (i)" above. `parse_grammar` and
`parse_grammar_file` gain `rust_fegen_cst_module: str | None = None`. Default → current
Python path exactly. When supplied → build a Rust-backed fegen parser via the
`generate_parser` Rust path against the committed fegen grammar, parse with it, and run the
*real* `fltk2gsm.Cst2Gsm(terminals, cst=pr.cst_module)`. The same backend's classes are used
for construction and injection, so `isinstance`/label dispatch in `Cst2Gsm` resolves.

Hard-error: a missing/unloadable `rust_fegen_cst_module` raises `RustBackendUnavailableError`
(propagated from the `generate_parser` Rust path) — no Python fallback.

### Runtime dependency on `fltk._native` (consequence of Option B)

The user's extension imports `fltk._native` at first node construction (for `UnknownSpan`).
At runtime the process must have `fltk._native` importable. Already true for any FLTK
runtime, but now a documented contract for the user's extension. The `Span` objects the
parser writes are `fltk._native.Span` instances, stored opaquely. No version-pinning in
Phase 4 (`TODO(rust-cst-abi-pinning)`).

### Hard-error semantics

```python
class RustBackendUnavailableError(RuntimeError):
    """Raised when a Rust CST backend is selected but its module cannot be loaded."""
    def __init__(self, module_name: str, detail: str | None = None):
        self.module_name = module_name
        msg = f"Rust CST backend selected (module {module_name!r}) but unavailable"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)
```

Raised on user-module import failure or a loaded-but-empty module. The raise happens
**before** `sys.modules[module_name]` is set and before any parser exec — so AC4's
assertion (no Python-exec'd CST module registered, no parse) holds. The Python branch is
never entered when the Rust selector is supplied.

### `isinstance` / type-identity invariant

`generate_parser`/unparser: the class objects in `public` are the exact PyO3 type objects in
the user's imported extension, placed by reference onto `cst_module` and `parser_globals`.
The parser constructs from `parser_globals[ClassName]`; the unparser does
`from fltk_grammar_{id} import ClassName`, resolving to `cst_module.ClassName` — the same
object. `parse_grammar`/`Cst2Gsm`: the Rust fegen parser constructs from `pr.cst_module`'s
classes, and the *same* `pr.cst_module` is injected into `Cst2Gsm`, so
`isinstance(item, self.cst.Item)` dispatches correctly. Both hold for both backends.

### `genparser.py` emit subcommand

Add a Typer subcommand `gen-rust-cst` that emits `.rs` source only (no compile):

```python
@app.command(name="gen-rust-cst")
def gen_rust_cst(
    grammar_file: Annotated[Path, typer.Argument(...)],
    output_file: Annotated[Path, typer.Argument(help="Path to write the .rs source")],
) -> None:
    grammar = _parse_grammar_raw(grammar_file)
    src = gsm2tree_rs.RustCstGenerator(grammar).generate()
    output_file.write_text(src)
```

**Double-trivia caveat (exploration lines 246-248):** `parse_grammar_file` applies
`add_trivia_rule_to_grammar` + `classify_trivia_rules`, and `RustCstGenerator.__init__`
applies them again. Double-application is idempotent, but the emit command should parse the
grammar **without** trivia processing and hand the raw grammar to `RustCstGenerator`.
Implement `_parse_grammar_raw` as the body of the parse path up to but excluding the trivia
call (return `cst2gsm.visit_grammar(result.result)`).

### Makefile targets — FLTK-internal only

```make
# Emit Rust CST source from a grammar.
gen-rust-cst:
	uv run python -m fltk.fegen.genparser gen-rust-cst $(GRAMMAR) $(RS_OUT)

# Build the fltk._native extension (compiles all committed src/*.rs).
build-native:
	uv run --group dev maturin develop

# Build FLTK's committed standalone non-FLTK fixture extension (separate cdylib crate).
build-test-user-ext:
	$(MAKE) -C tests/rust_cst_fixture develop

# Build FLTK's own fegen-grammar Rust CST extension (separate cdylib crate) used by the
# parse_grammar(backend="rust") path and AC8.
build-fegen-rust-cst:
	$(MAKE) -C tests/rust_cst_fegen develop
```

The user build is documented, not Makefile-encoded. A user, in their own project: emit
`.rs`, write a `cdylib` crate with a `#[pymodule]` init calling `register_classes`, build
with their tool, pass `rust_cst_module="mypkg.mygrammar_cst"` to `generate_parser`.

### Test-policy → skip-when-absent + CI builds

Tier-2 tests are guarded by a helper that checks whether the relevant Rust CST module is
importable; if not, `pytest.skip`. CI runs `make build-native`, `make build-test-user-ext`,
and `make build-fegen-rust-cst` before `pytest`. Python-only contributors running
`uv run pytest` see skips, not failures. A CI lane that skips every Tier-2 test is a failure
signal.

---

## Edge Cases / Failure Modes

- **Standalone user extension fails to import because `fltk._native` is not installed.** The
  user's extension imports `fltk._native` at first node construction. If FLTK is not
  installed, the import — or the first node construction — fails with `ImportError`, caught
  by `_load_rust_cst_classes` (at load time) or surfacing at parse time (lazy sentinel).
  Documented as a hard runtime dependency.

- **Sentinel-import timing.** The `GILOnceCell` cache means `import fltk._native` runs at
  *first node construction*, not at extension import. A malformed/missing `fltk._native` may
  surface at parse time as a normal `ImportError` (loud, not silent). AC4's hard-error
  guarantee covers `generate_parser`-time failures (missing user module). Acceptable; noted.

- **Rust module exposes label-enum types alongside node classes.** The Rust module registers
  `*_Label` enum types as top-level classes; the Python backend nests them as
  `ClassName.Label`. `_load_rust_cst_classes` copies both onto `cst_module` and into
  `parser_globals`. Harmless: consumers reference node classes by name and `ClassName.Label`
  via `#[classattr] Label`, never the top-level `ClassName_Label` name. **Backend-parity
  note:** the two backends' `parser_globals` are NOT key-for-key identical — the Rust path
  adds inert top-level `*_Label` aliases. Benign; flagged so no future reader assumes exact
  key parity.

- **`Cst2Gsm` label dispatch across backends.** `Cst2Gsm` uses `self.cst.Items.Label.NO_WS`
  and `label == self.cst.Items.Label.WS_REQUIRED`. For the Rust backend, `self.cst` is
  `pr.cst_module`; `self.cst.Items.Label` resolves via the Rust `#[classattr] Label`, and the
  label objects carried in `children[i][0]` are the same Rust enum objects (constructed by
  the same Rust classes the parser used). Equality (`==`) and containment (`in`) require
  `__eq__`/`__hash__` on the Rust label enum (API Contract item 8) — verified by AC5/AC8.

- **`parse_grammar` Rust path and fegen-grammar recursion.** `_load_fegen_grammar()` parses
  `fegen.fltkg` via the *default Python* path, which takes no Rust branch — no infinite
  recursion. Parse it once and cache at module scope.

- **Backend mismatch: user module built from a different grammar than the one passed.**
  `generate_parser` does not verify `rust_cst_module` matches `grammar`. A mismatch fails at
  node construction (missing class / wrong labels) with a normal `AttributeError`/`KeyError`
  — not a silent wrong result. Caller responsibility (Open Question).

- **`fltk._native` / user-extension version skew.** A user extension built against one FLTK
  version, run against another whose `Span`/`UnknownSpan` changed, could misbehave. No
  pinning in Phase 4. Documented: rebuild on FLTK upgrade if `Span`/`UnknownSpan` changed.
  `TODO(rust-cst-abi-pinning)`.

- **`importlib.import_module` of a non-existent module.** Raises `ModuleNotFoundError`
  (subclass of `ImportError`), caught and re-raised as `RustBackendUnavailableError`. ABI /
  Python-version mismatch on the `.so` also surfaces as `ImportError`. Catch scoped to
  `ImportError`.

- **`sys.modules` pollution on the Rust path.** The per-call `types.ModuleType` is registered
  under `fltk_grammar_{id(grammar)}` exactly as the Python path does.
  `test_parser_module_cleanup` (`test_plumbing.py:81-88`) holds — registration line shared.

- **Empty-label-enum rules** (Phase 3 design): a zero-label rule has a node class but no
  `*_Label` enum and no `#[classattr] Label`. `register_classes` emits only
  `add_class::<NodeStruct>`. The node class still appears in `public`; nothing downstream
  requires its label enum. No Phase 4 handling needed.

- **Python backend / default callers unchanged.** When no backend is selected,
  `generate_parser`, `parse_grammar`, and `Cst2Gsm` behave exactly as today. `Cst2Gsm`'s
  default `cst=fltk_cst` keeps `genparser.py:52`, `genunparser.py:45`, and existing tests
  working with no edits. AC1 is the guard.

---

## Test Plan

The **primary** Rust artifact is a **standalone non-FLTK user-extension fixture**; FLTK's
own fegen Rust CST is a **secondary dogfooding case** — but AC8 (real `Cst2Gsm` on the Rust
fegen backend) is binding.

### Tier 1 (runtime-contract; no Rust artifact)

- **`test_python_backend_unchanged`** (AC1): existing `test_plumbing.py` /
  `test_plumbing_integration.py` / fegen tests pass unmodified. No new code path when no
  backend is selected.
- **`test_cst2gsm_default_namespace_unchanged`** (AC1): `Cst2Gsm(terminals)` with no `cst`
  arg uses `fltk_cst` and produces identical `gsm.Grammar` output to today on a sample
  grammar (guards the DI refactor's default behavior).
- **`test_rust_backend_missing_module_hard_errors`** (AC4): `generate_parser(g,
  rust_cst_module="does_not_exist_pkg.nope")`; assert `RustBackendUnavailableError`; assert
  `f"fltk_grammar_{id(g)}" not in sys.modules`; assert no parser class produced.
- **`test_parse_grammar_rust_missing_module_hard_errors`** (AC4): `parse_grammar(text,
  rust_fegen_cst_module="nope")` raises `RustBackendUnavailableError`, no fallback.
- **`test_rust_backend_empty_module_hard_errors`** (AC4 variant): monkeypatch
  `importlib.import_module` to return a module with no `type` attributes; assert
  `RustBackendUnavailableError` with the "exposes no CST classes" detail.
- **`test_gen_rust_cst_command_emits_source`** (supports AC6, Python half): run
  `gen-rust-cst` on a small grammar; assert output contains `pub fn register_classes`, the
  class names, and **no `use crate::UNKNOWN_SPAN;`**. No compilation.
- **`test_gen_rust_cst_no_double_trivia`**: assert the raw-grammar parse path feeds
  `RustCstGenerator` a grammar with no pre-existing `_trivia` rule.
- **`test_gen_rust_cst_sentinel_decoupled`**: assert the emitted preamble declares a
  module-local `GILOnceCell` sentinel cache and the `#[new]` body fetches
  `fltk._native.UnknownSpan` at runtime.

### Tier 2 (artifact-dependent; gated on a built Rust module, skip-when-absent)

**Committed Phase-4 deliverables (NOT mere fixtures).**

1. **A standalone non-FLTK user-extension fixture** (PRIMARY — the general capability). A
   small grammar `fltk/fegen/test_data/phase4_roundtrip.fltkg` (labeled children,
   optional/repeated items, ≥1 multi-variant label enum). Its generated `.rs`, a **separate
   `cdylib` crate** under `tests/rust_cst_fixture/` with its own `Cargo.toml` and a
   `#[pymodule]` init calling `register_classes`, and the build wiring are committed
   deliverables. Importable under a user-style name (e.g. `phase4_roundtrip_cst`) — **not**
   under `fltk._native`. Built via `make build-test-user-ext`.
2. **FLTK's fegen Rust CST extension** (SECONDARY — dogfooding; used by AC8). A separate
   `cdylib` crate under `tests/rust_cst_fegen/` whose `.rs` is generated from `fegen.fltkg`
   and whose `#[pymodule]` calls `register_classes`, importable under a user-style name (e.g.
   `fegen_rust_cst`). Built via `make build-fegen-rust-cst`. This is what `parse_grammar(
   ..., rust_fegen_cst_module="fegen_rust_cst")` loads.

A `requires_rust_cst(module_name)` helper skips when import fails — local Python-only path
only; a CI skip is a failure signal.

- **`test_rust_backend_module_registered`** (AC2): `generate_parser(g,
  rust_cst_module="phase4_roundtrip_cst")`; assert `cst_module_name in sys.modules`, the
  returned `cst_module` exposes each rule's node class, `hasattr` per rule. Against the
  standalone user extension.
- **`test_rust_roundtrip_standalone_extension`** (AC3): full parse → CST → unparse on
  `phase4_roundtrip.fltkg` via `phase4_roundtrip_cst`; assert Rust-backed node construction,
  unparser reads via the imported module, `isinstance` dispatch resolves.
- **`test_rust_cst_contract_non_fltk`** (AC5 PRIMARY — binding API-Contract verification):
  exercise all 12 API-Contract items directly against node instances from
  `phase4_roundtrip_cst` — `children[::2]`, `children[1::2]`, `children[-1]`, tuple unpack,
  label `==`/`in`, `isinstance`, `append_{label}`, `children.extend`, typed/iterator/generic
  accessors. Discharges the API Contract for the general capability.
- **`test_real_cst2gsm_on_rust_fegen_backend`** (AC8 — binding, the real consumer): parse a
  representative `.fltkg` grammar (e.g. a portion of `fegen.fltkg` itself or a fixture
  grammar) via `parse_grammar(text, rust_fegen_cst_module="fegen_rust_cst")`, asserting the
  resulting `gsm.Grammar` equals the one from `parse_grammar(text)` (Python backend) on the
  same input. Exercises the **real** `fltk2gsm.Cst2Gsm` against Rust-backed fegen nodes via
  the injection seam. **No hand-written substitute for `Cst2Gsm`.** Also run `Cst2Gsm`
  directly with `cst=` a Rust namespace against hand-built or parsed Rust fegen nodes to
  isolate the consumer.
- **`test_makefile_builds_rust_cst`** (AC6): `make build-test-user-ext` produces importable
  `phase4_roundtrip_cst`; `make build-fegen-rust-cst` produces importable `fegen_rust_cst`;
  `make build-native` produces `fltk._native`. Assert no cargo/maturin is invoked from any
  Python parse path.
- **Both-backend contract sweep** (AC7): a parametrized test running the 12 API-Contract
  items against the Python backend (Tier 1) and the Rust backend (Tier 2,
  `phase4_roundtrip_cst`).

### Static / unit

- **`test_no_runtime_compilation`** (Constraint): assert `plumbing.py`'s imports do not
  include `subprocess`/`cargo`/`maturin`/`rustc` invocation surfaces; `_load_rust_cst_classes`
  uses only `importlib`.

---

## Open Questions

The requirements have been rewritten around the backend-selection framing; the consumer
injection seam, the standalone artifact, the `gsm2tree_rs.py` generator change, the non-FLTK
AC5 as binding, and the real-`Cst2Gsm`-on-Rust AC8 are resolved/in-scope there and no longer
open. The remaining open questions are genuine user-judgment calls.

### selector-surface-form [USER]
`generate_parser` resolved to a single `rust_cst_module: str | None = None`. `parse_grammar`
resolved to `rust_fegen_cst_module: str | None = None` (parallel shape). `Cst2Gsm` resolved
to a `cst=` namespace parameter defaulting to `fltk_cst`. If the user prefers
`backend: Literal["python","rust"]` enums plus the module name, that is a surface-only change.
- Proposed: the single-parameter shapes above. To redirect: state the desired parameter set.

### user-crate-scaffolding [USER]
Should FLTK generate the user's `cdylib` crate scaffolding (`Cargo.toml` + `#[pymodule]`
wrapper calling `register_classes`), or only emit the `.rs` node source and document the
~15-line wrapper?
- Proposed: **emit `.rs` + document the wrapper** for Phase 4. A `gen-rust-crate` command is
  a clean follow-up.

### rust-backend-grammar-consistency-check [USER]
Should `generate_parser` verify `rust_cst_module` was generated from the same `grammar`, or
is a mismatch caller responsibility surfacing at parse time?
- Proposed: **no runtime check** (caller responsibility). Cheap follow-up if desired.

### TODO(rust-cst-shared-rlib)
If user extensions ever need to link *Rust-level* shared types (today they do not — `span` is
`PyObject`), Option D (a `fltk-cst-common` rlib + Cargo workspace) is the clean answer. Out of
Phase 4 scope. Add the `TODO(rust-cst-shared-rlib)` comment at the generator's sentinel-cache
emission site and a `TODO.md` entry.

### TODO(rust-cst-abi-pinning)
No version handshake exists between a user extension and `fltk._native` (`Span`/`UnknownSpan`
shape). If skew proves fragile, add an ABI-version check at the sentinel fetch. Out of Phase 4
scope. Add the `TODO(rust-cst-abi-pinning)` comment + `TODO.md` entry.

**Note:** every TODO requires BOTH the `TODO(slug)` code comment AND the `TODO.md` entry,
joined on the slug (CLAUDE.md "TODO System"). Neither half may be dropped.
