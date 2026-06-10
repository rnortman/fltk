# Design: rust-cst-pyi

Style: concise, precise, no padding, no preamble. Audience: smart LLM/human.

Scope: `.pyi` emitter for the generated Rust CST extension (Part 1), plus the B4
runtime/packaging verification against the prebuilt `fltk._native.fegen_cst` extension
(Part 2 — in scope per user decisions, §5). Spec is `request.md` in this dir; not
restated. Validation is `exploration.md` in this dir plus the staleness re-check
`docs/adr/2026/06/09-todo-burndown-resume/expl-staleness-rust-cst-pyi.md`.

---

## 1. Root cause / context

`gen-rust-cst` emits only `.rs` (`genparser.py:264-287`; generator
`gsm2tree_rs.RustCstGenerator.generate`, `gsm2tree_rs.py:114-130`). The compiled PyO3
extension therefore has **no static type surface**. Downstream consumers' typed code
sees Rust nodes only through `cast("cst.Grammar", result.result)` on `Any`
(`plumbing.py:173-175`, same pattern at `genparser.py:60-63`). The cast is taken on
faith: a real divergence between the PyO3 surface and the committed `CstModule` Protocol
(`fltk_cst_protocol.py:746-791`) is invisible to pyright.

`CstModule` is generated per-grammar by `gsm2tree.CstGenerator._cst_module_protocol`
(`gsm2tree.py:658-675`; appended to the protocol module at l.519) and committed
(e.g. `fltk_cst_protocol.py:746-791`). It is the authoritative description of the
consumer-facing surface. The `.pyi`'s job is to give pyright a typed view of the Rust
module that can be statically checked against `CstModule`.

All information needed is already in the GSM that `RustCstGenerator` holds: rule names,
class names (`CstGenerator.class_name_for_rule_node`), per-rule sorted labels
(`_rule_info`, `gsm2tree_rs.py:69-95`), and the per-label / child-union accessor types
(`CstGenerator.protocol_annotation_for_model_types`, `gsm2tree.py:412`, used at
`gsm2tree.py:573,612`).

### The surface the `.pyi` must mirror is the *Rust* surface, not the Python protocol

The `.pyi` must describe what `gsm2tree_rs.py` actually emits, which diverges from the
committed Python protocol in load-bearing ways. Enumerated from `gsm2tree_rs.py` at HEAD
(post-`4c8f0ad`, native-span rework):

| Member | Rust emission (source) | Python `CstModule` protocol |
|---|---|---|
| `span` | getter returns canonical `fltk._native.Span` (`_span_getter_setter`, l.584-612); setter accepts local or `fltk._native` span via `extract_span` | `terminalsrc.Span \| fltk._native.Span` (`fltk_cst_protocol.py:89`; emitted at `gsm2tree.py:571`) |
| `children` | `Py<PyList>` get (`_children_getter`, l.636-655; struct field is native `Vec`, rebuilt per call) | `list[tuple[Label\|None, <union>]]` |
| `children_<label>` | returns `Py<PyList>` (`_per_label_methods`, l.802) | `Iterator[T]` |
| `extend_children` | `fn extend_children(&mut self, other: PyRef<ClassName>)` (`_generic_extend_children`, l.725-740) | `def extend_children(self, other: <Class>) -> None` (`fltk_cst_protocol.py:96` et al.; emitted at `gsm2tree.py:599-601`) |
| `kind` | getter -> `NodeKind` (`_kind_getter`, l.615-622) | `Literal[NodeKind.X]` |
| `Label` | `#[classattr]` only when rule has labels (`_label_classattr`, l.625, emitted conditionally at l.547) | nested class only when labelled |
| `NodeKind` / `<Class>_Label` | PyO3 enums with `__eq__`/`__hash__`/`_fltk_canonical_name` | enum / `_ProtocolLabelMember` |
| module-level `Span` | **not registered** (`_register_classes_fn`, l.908-921, adds only `NodeKind`, label enums, node classes; spans come from `fltk._native` at runtime) | `@property def Span(self) -> type[Span]` (`gsm2tree.py:670-672`) — but the *Python concrete module doesn't satisfy this either*; see below |

**`CstModule.Span` is a protocol overclaim, not a Rust-backend gap.** The generated
Python concrete module also has no module-level `Span` binding (`fltk_cst.py` top level:
only `import fltk.fegen.pyrt.span` / `terminalsrc`, no `Span = ...`). The runtime `Span`
type lives in common libraries on both backends — `fltk.fegen.pyrt.terminalsrc.Span`
(pure Python), re-exported by the backend selector `fltk/fegen/pyrt/span.py` (which
prefers `fltk._native.Span`), and `fltk._native.Span` registered once at
`src/lib.rs:20-23` — never in the per-grammar generated module. So `mod.Span` on a
`CstModule`-typed binding raises `AttributeError` on **every** backend today; no working
downstream code can depend on it. Confirmed by the user (OQ-A answer, §5): the
common-single-`Span` model is the intended design. Resolution in §2.1a.

### Conformance is impossible with stub-local nominal types (feasibility constraint)

A stub whose classes carry their own nested `Label` classes, their own `NodeKind` enum,
and self-referential node types in `children`/method signatures **cannot** satisfy
`CstModule` under a bare no-cast assignment. Four independent blockers:

- **Nested `Label` nominal identity.** The protocol's per-node `Label` is a plain
  nominal class (`fltk_cst_protocol.py:85-87`); conformance requires the implementer's
  `Label` attribute be assignable to `type[<proto>.Label]` — a stub-local `Label` class
  always fails.
- **`kind` Literal enum identity.** The protocol's `kind: Literal[NodeKind.X]`
  references the *protocol module's* `NodeKind`; a `Literal` of a stub-local enum member
  is a different type, and the attribute is mutable hence invariant.
- **`children` invariance.** `children: list[tuple[Label|None, <union>]]` is an
  invariant mutable attribute whose element types are the protocol's own classes;
  stub-local element types fail bidirectional assignability.
- **Parameter contravariance.** `append(child: ..., label: ...)`,
  `extend_children(other: <Class>)` — the protocol's parameter types are not assignable
  to stub-local nominal parameter types.

This is proven in-repo: T2b (`test_boundary_probe_documents_label_mismatch`,
`test_cst_protocol.py:365-382`) asserts the bare assignment
`_m: cstp.CstModule = fltk_cst` **must produce pyright errors** for the concrete Python
backend, whose surface uses exactly such module-local nominal types. Any stub that
mirrors that shape fails the same way.

Consequence: the stub's *member set and signatures* must come from the Rust generator's
own rule info (so a missing accessor in `.rs` is a missing member in the stub), but the
*type identities* in annotations must reference the grammar's committed protocol module.
That is the adopted strategy (OQ-0(a), decided by the user — §5).

---

## 2. Proposed approach

All §5 open questions are resolved (user, 2026-06-09): OQ-0 = (a) protocol-typed
annotations; OQ-A = common-lib `Span` model confirmed (→ §2.1a); OQ-1 = both parts now;
OQ-2 = prebuilt `fltk._native.fegen_cst` (→ §2.3). §2.1 is written against OQ-0(a).

### 2.1 Part 1 — `.pyi` emitter

Add a `.pyi` generator driven from the same GSM as `RustCstGenerator`. It is **additive**;
the `.rs` output is unchanged (non-goal: touching `.rs`).

**Placement.** Add the emitter as a method/companion of `RustCstGenerator`, e.g.
`RustCstGenerator.generate_pyi(protocol_module: str) -> str`, reusing the instance's
`self.grammar`, `self._py_gen` (a `CstGenerator`), and `self._rule_info()`. This
guarantees the `.pyi` node set, class names, and labels are derived from the *same*
trivia-processed grammar the `.rs` is, so the two never drift. `_rule_info` already
enumerates exactly the classes and labels `.rs` emits; reusing it is the single source
of truth.

**Protocol module parameter.** `generate_pyi` takes the import path of the grammar's
committed protocol module (e.g. `fltk.fegen.fltk_cst_protocol`); the stub imports it
under an alias (`import <path> as _proto`) and all type identities in annotations are
qualified against it. New `gen-rust-cst` CLI option (e.g. `--protocol-module`); when
omitted, skip `.pyi` emission (backward compatible with existing invocations). Never
emit a stub-local-types stub — per §1 it cannot conform.

**Member shapes from the protocol machinery, identities from the protocol module.** The
accessor *shape* (per-label `append_/extend_/children_/child_/maybe_`, generic
`append/extend/child/extend_children`, `kind` discriminant) is identical in name to what
`_protocol_class_for_model` emits (`gsm2tree.py:540-641`). Produce the same method names
and the same child-union / per-label element types via
`self._py_gen.protocol_annotation_for_model_types(...)`, then qualify every protocol
class reference with the `_proto` alias so the names resolve to the committed protocol's
classes, not stub-local ones. Do **not** fork the annotation logic.

**Emitted `.pyi` structure** (one stub file; placement per CLI wiring below):

- Header: derive the import list from the annotations actually emitted, as
  `gen_protocol_module` does. The expected set: `from __future__ import annotations`;
  `import typing`; `import fltk.fegen.pyrt.terminalsrc`; `import fltk.fegen.pyrt.span`
  (the annotation machinery emits `fltk.fegen.pyrt.span.Span` for terminal children —
  see `fltk_cst_protocol.py:197,219,...` and the matching import at `gsm2tree.py:495`);
  `import fltk._native`; `import <protocol_module> as _proto`.
- `NodeKind = _proto.NodeKind` — module-level alias. The runtime object is the PyO3
  enum; typing it as the protocol's `NodeKind` is the deliberate checker-favorable
  divergence of OQ-0(a). Consumers' `node.kind == mod.NodeKind.X` checks type-check
  against one consistent enum.
- Per rule, in `_rule_info()` order, `class <Class>:` with:
  - When labelled: `Label: typing.ClassVar[type[_proto.<Class>.Label]]` (runtime is the
    PyO3 `<Class>_Label` enum; same divergence category). Omit entirely for label-free
    rules — emitting one would diverge from `.rs` and mask a real gap.
  - `kind: typing.Literal[_proto.NodeKind.<MEMBER>]` — member set from `_rule_info`
    (`_node_kind_python_name`). Resolving against `_proto.NodeKind` is what makes the
    protocol's `Literal` match; it also keeps consumer `.kind` narrowing (commit
    `1f5ad7a`) working.
  - `span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span` — the protocol's exact
    union (§3).
  - `children: list[tuple[_proto.<Class>.Label | None, <proto-qualified union>]]`
    matching the protocol's labelled/label-free split (`tuple[None, T]` when label-free).
  - Generic `append`, `extend`, `child`, `extend_children(other: <Class>) -> None`
    (mirrors `gsm2tree.py:599-601` / `fltk_cst_protocol.py:96` — emitted by
    `_generic_extend_children`, `gsm2tree_rs.py:725-740`, on every node; omitting it
    fails conformance), and the five per-label accessors, with element types from
    `protocol_annotation_for_model_types`, proto-qualified. `children_<label>` typed
    `typing.Iterator[T]` (§3). Parameter and return types reference `_proto` classes
    throughout (the contravariance/invariance blockers of §1 require it).
- Module-level class attributes: one `<Class>: type[<Class>]` per rule, so the module
  object's node-class properties structurally satisfy `CstModule`. (`type[<StubClass>]`
  is assignable to `type[<proto Class>]` because the stub class, annotated entirely with
  proto types, structurally satisfies the proto class.)
- **No module-level `Span`**: neither backend's generated module exports one (§1);
  declaring it would make the stub certify an attribute that raises `AttributeError` at
  runtime. With §2.1a's protocol fix, the whole-module no-cast assignment passes with
  zero errors despite the omission.

**CLI wiring** (`genparser.py:264-287`): after writing `output_file` (the `.rs`; that
write is wrapped in try/except), also write the `.pyi` at
`output_file.with_suffix(".pyi")` by default (co-located with the `.rs`, per the
request's "next to the `.rs`"), overridable via a new `--pyi-output <path>` option for
cases where the `.rs` stem differs from the compiled module's import name — required by
Part 2, where `src/cst_fegen.rs` backs the `fegen_cst` submodule (§2.3). Generate the
`.pyi` text *before* opening the file (mirror the existing partial-file-avoidance
pattern in `gen_python_cst`, `genparser.py:186, 197`). Both parts land in this workflow,
so remove the `TODO(rust-cst-pyi)` comment (`genparser.py:279`) and the `TODO.md` entry
(the `## rust-cst-pyi` section — locate by slug, not line number) outright; no narrowed
follow-up remains.

**Formatting.** Generated stub need not pass ruff straight out of the generator (per
CLAUDE.md "Generated Code and Formatting"); regen → `make fix` → commit is the flow.
Emit a `# ruff: noqa: N802` header if module-level PascalCase names trip lint, mirroring
the protocol generator (`genparser.py:205`).

### 2.1a Remove `CstModule.Span` (deliberate public-API correction, per OQ-A)

Per §1, `CstModule.Span` promises a member no backend's concrete module has ever
provided; the user confirmed `Span` belongs to the common libraries, not the generated
CST module. Fix the protocol, not the backends:

- Delete the `Span` property emission from `_cst_module_protocol`
  (`gsm2tree.py:668-676`, the `span_prop` block). The module-level
  `class Span(typing.Protocol)` (`_protocol_span_class`, `gsm2tree.py:643-656`) **stays**
  — it types span values for `case cst.Span.kind:` narrowing and is unrelated to the
  module-attribute promise.
- Regenerate the four committed protocol modules (`fltk_cst_protocol.py`,
  `bootstrap_cst_protocol.py`, `toy_cst_protocol.py`, `unparsefmt_cst_protocol.py`) via
  `make gencode` + `make fix`.
- Update tests that assert the property's presence: `test_cst_protocol.py:177-178`
  (expected `CstModule` property set includes `"Span"`); `:108-110` is the
  protocol-module *class* set, which keeps `Span`.

This is a removal from committed public protocol API, called out deliberately per
CLAUDE.md: it is safe for out-of-tree consumers because any code reading `.Span` off a
`CstModule`-typed binding raises `AttributeError` at runtime on both backends today —
no working consumer code can exist. Removing it loosens what implementing modules must
provide (Protocol members are requirements on implementers); consumers obtain `Span`
from `fltk.fegen.pyrt.span` / `terminalsrc` / `fltk._native`, as they already must.
With this fix the whole-module no-cast conformance target becomes **zero errors**.

### 2.2 Conformance verification — what is static, what needs a build

Pyright never imports the compiled extension; once a `.pyi` exists on the import path,
*every* pyright check of "the extension" is a check of the stub. Two consequences:

1. **The no-cast static conformance check belongs to Part 1.** A test can write the
   generated `.pyi` to a tmp dir as `<mod>.pyi`, write a fixture
   `import <mod>; _m: cstp.CstModule = <mod>` (no cast), and run pyright — no Rust
   toolchain. Expected outcome under OQ-0(a) + §2.1a: **zero errors**. Per-class no-cast
   fixtures (a parameter typed as the stub class assigned to a protocol-typed local,
   e.g. `def f(g: mod.Grammar) -> None: _g: cstp.Grammar = g`) also assert zero errors.
   This uses the existing harness (`run_pyright`, `pyright_available`,
   `test_cst_protocol.py:37-74`).
2. **Part 2's residual value is runtime-vs-stub agreement,** which pyright cannot see:
   import the *compiled* extension and introspect — every class, method, and classattr
   the stub declares exists at runtime (and the stub omits nothing the runtime has, for
   the generated surface). Plus stub packaging/resolution for the real import name.
   Both are in scope (OQ-1 "both now"); §2.3 designs them against the prebuilt
   `fltk._native.fegen_cst` surface (OQ-2).

### 2.3 Part 2 — verification against the prebuilt `fltk._native.fegen_cst`

The user chose the prebuilt route over compile-on-the-fly. The earlier objection — that
a `fltk._native` stub is a repo-wide typing change that must be designed deliberately,
not as a test side effect — is answered by designing it here. The prebuilt route also
costs no new build machinery: `uv run --group dev maturin develop` is already required
before running any tests (CLAUDE.md "Build and test workflow"), so the extension under
test is the one every test run already builds.

**Surface under test.** The fegen Rust CST classes in the `fltk._native.fegen_cst`
submodule (`src/lib.rs:33-47`; registered in `sys.modules` manually, so
`from fltk._native.fegen_cst import X` works — already exercised by
`tests/test_fegen_rust_cst.py:12`). Not the duplicate `fegen_rust_cst` test crate
(`tests/rust_cst_fegen`, see `TODO(fegen-cst-rs-single-source)`), which stays out of
scope.

**Stub package layout.** `fltk/_native` is a single-file extension
(`fltk/_native.abi3.so`) with a submodule, so the stub is a directory package:

- `fltk/_native/__init__.pyi` — hand-written, committed.
- `fltk/_native/fegen_cst.pyi` — generated by the §2.1 emitter, committed.

Runtime safety: a `fltk/_native/` directory containing only `.pyi` files (no
`__init__.py`) is at most a namespace-package *portion*; CPython's finder selects the
regular extension module `_native.abi3.so` over it, so the stub directory does not
shadow the compiled module at import time. Guarded by the existing runtime tests
(`tests/test_fegen_rust_cst.py` constructs real classes) plus the B4 test below; an
accidental `__init__.py` in that directory *would* shadow the extension and break every
runtime import — note this in the `__init__.pyi` header comment.

**`__init__.pyi` contents** (hand-written; the only hand-maintained stub):

- `Span` — mirror the `#[pymethods]` surface of `crates/fltk-cst-core/src/span.rs:188+`:
  `__init__(start: int, end: int)`; classmethod `with_source(start, end,
  source: SourceText) -> Span`; `text() -> str | None`; `text_or_raise() -> str`;
  `has_source() -> bool`; `len() -> int`; `is_empty() -> bool`;
  `merge(other: Span) -> Span`; `intersect(other: Span) -> Span`; getters
  `start: int`, `end: int`; getter `kind` typed
  `Literal[terminalsrc.SpanKind.SPAN]` (the runtime getter returns the *same* shared
  `terminalsrc.SpanKind.SPAN` object, `span.rs:372-394`, so this annotation is exact
  and keeps `fltk._native.Span` satisfying the protocol's `Span` class).
- `SourceText` — `__init__(text: str)` plus its pymethods surface.
- `UnknownSpan: Span` — module-level instance (`src/lib.rs:22-23`).
- **PoC grammar classes intentionally omitted.** `cst_generated::register_classes(m)`
  (`src/lib.rs:29`) adds the hand-built PoC grammar's classes at top level; they have no
  committed protocol module (the OQ-0(a) emitter requires one) and no static in-repo
  references, so omission costs nothing statically. Document the omission in the stub
  header, cross-referencing `TODO(gencode-poc-fltkg)`; do not hand-maintain generated
  class signatures.

**Generation wiring.** `make gencode` (`Makefile:104-105`) gains the stub emission for
the fegen grammar:
`gen-rust-cst fltk/fegen/fegen.fltkg src/cst_fegen.rs --protocol-module
fltk.fegen.fltk_cst_protocol --pyi-output fltk/_native/fegen_cst.pyi` — the `.rs` stem
(`cst_fegen`) differs from the import name (`fegen_cst`), which is exactly why §2.1
adds `--pyi-output`. Regen → `make fix` → commit, per the standard generated-code flow;
`make check` keeps the committed stub in sync.

**Repo-wide blast radius (deliberate).** Today pyright treats `fltk._native` attributes
as Unknown; the stub makes them concrete. Statically affected at HEAD:

- `fltk/fegen/pyrt/span.py:10` `from fltk._native import SourceText, Span, UnknownSpan`
  — carries `# type: ignore[assignment]`, which continues to suppress the redefinition;
  all three names exist in the stub.
- `fltk._native.Span` in the committed protocol span unions (`fltk_cst_protocol.py:89`
  et al., `unparsefmt_cst_protocol.py`) and in `test_cst_protocol.py` span-consumer
  fixtures — now resolve to the stub's `Span`; the `kind` annotation above keeps the
  protocol-`Span` relationships these fixtures assert.
- `tests/test_fegen_rust_cst.py:11-12` imports — now checked against the stubs; all
  imported names (Span, UnknownSpan, the 14 node classes) are declared.

The acceptance gate for this radius is the repo-wide `uv run pyright` (already part of
the standard check).

**Packaging.** maturin's mixed layout ships the `fltk/` package tree, so the `.pyi`
files and the existing `fltk/py.typed` ride along; verify wheel contents during
implementation. Bazel does not build the Rust extension at all
(`TODO(bazel-rules-rust)`), so no Bazel change.

**B4 runtime-agreement test.** Import `fltk._native.fegen_cst`, parse
`fltk/_native/fegen_cst.pyi` with `ast`, and assert two directions over the generated
surface: every stub-declared class/method/classattr exists on the runtime module, and
every public runtime member of the submodule is declared in the stub. Scope is the
`fegen_cst` submodule only (top-level `_native` is excluded — PoC omission above is
deliberate). Skip cleanly when `fltk._native` is unimportable, mirroring
`pyright_available`-style skips.

**Static conformance of the committed stub.** A checked-in fixture
(`_m: cstp.CstModule = fegen_cst_module`, no cast) asserting zero errors — this is the
request's B4 "without a cast" criterion against the *real* prebuilt extension's typed
surface. It can live as a normal typed file under the repo pyright gate rather than a
subprocess fixture.

### 2.4 Files touched

- `fltk/fegen/gsm2tree_rs.py` — add `.pyi` emitter (new method, no change to `.rs` path).
- `fltk/fegen/genparser.py` — wire `.pyi` emission + `--protocol-module` /
  `--pyi-output` into `gen-rust-cst`; remove the TODO comment.
- `fltk/fegen/gsm2tree.py` — remove the `Span` property from `_cst_module_protocol`
  (§2.1a); everything else is only *called into*.
- `fltk/fegen/fltk_cst_protocol.py`, `bootstrap_cst_protocol.py`,
  `fltk/unparse/toy_cst_protocol.py`, `unparsefmt_cst_protocol.py` — regenerated (§2.1a).
- `fltk/_native/__init__.pyi` (hand-written), `fltk/_native/fegen_cst.pyi` (generated,
  committed) — §2.3.
- `Makefile` — `gencode` emits the fegen stub (§2.3).
- `TODO.md` — remove the `rust-cst-pyi` entry (by slug).
- `fltk/fegen/test_*`, `tests/` — new tests (§4); update
  `test_cst_protocol.py:177-178` expected property set (§2.1a).

---

## 3. Edge cases / failure modes

- **Nominal-identity blockers (Label / kind / children / parameters).** Resolved by
  OQ-0(a): all type identities reference `_proto`. If any annotation slips through with
  a stub-local class, the §4 conformance fixture fails — that is the regression guard.
- **`children_<label>` return-type mismatch.** Rust emits `Py<PyList>`
  (`gsm2tree_rs.py:802`); protocol declares `Iterator[T]` (`gsm2tree.py:627`). `list[T]`
  does not satisfy `Iterator[T]`. The `.pyi` must type `children_<label>` as
  `typing.Iterator[T]` (matching the protocol), accepting that the stub's declared
  return type is narrower than the runtime `list`. Deliberate stub/runtime divergence in
  the *checker-favorable* direction (callers only ever iterate). Flag in stub comment.
  Failure mode if mistyped as `list[T]`: pyright rejects the no-cast conformance fixture.
- **`span` annotation must be the protocol's exact union.** The Rust struct holds a
  native `fltk_cst_core::Span`; the Python getter always returns a canonical
  `fltk._native.Span` constructed via `get_span_type` (`_span_getter_setter`,
  `gsm2tree_rs.py:584-612`), and the setter accepts either a local or `fltk._native`
  span (`extract_span`). The committed protocol annotates
  `span: terminalsrc.Span | fltk._native.Span` (`fltk_cst_protocol.py:89`;
  `gsm2tree.py:571`). The stub must use **exactly that union**: protocol *attributes*
  are invariant under structural matching, so a narrower runtime-accurate annotation
  fails conformance. The union also correctly describes the settable side.
- **Module-level `Span` (protocol overclaim).** Resolved by §2.1a: the stub honestly
  omits `Span` (matching both backends' real shape) and `CstModule` stops promising it.
  Do **not** instead register `Span` per generated module — wrong direction per the
  user's OQ-A answer: `Span` is a single common-lib type, and per-module registration
  would create N aliases of it and touch `.rs` output (the request's non-goal) for no
  consumer benefit.
- **Stub directory shadowing.** `fltk/_native/` must never gain an `__init__.py`; only
  `.pyi` files. With `.pyi` only, the regular extension module `_native.abi3.so` wins
  import resolution; with an `__init__.py`, the directory becomes a regular package and
  shadows the extension, breaking all runtime imports. Header comment in the stub +
  runtime tests catch it immediately.
- **`fltk._native` goes from Unknown to typed repo-wide.** Enumerated in §2.3 (blast
  radius); the failure mode is a previously-Unknown reference now erroring under
  `uv run pyright`. Mitigation: the `__init__.pyi` member list is derived from the real
  PyO3 surface (`crates/fltk-cst-core/src/span.rs`, `src/lib.rs`), and the repo gate
  runs in the same change.
- **Hand-written `__init__.pyi` drift.** `Span`/`SourceText` evolve in
  `fltk-cst-core`; the stub is hand-maintained. Bounded: the B4 runtime-agreement
  direction "stub declares → runtime has" can include the `Span`/`SourceText`/
  `UnknownSpan` names it imports, and the surface is small and stable. PoC top-level
  classes are excluded by design (§2.3).
- **Label-free nodes.** No `Label` classattr in `.rs` (emitted conditionally,
  `gsm2tree_rs.py:547`). The `.pyi` omits the nested `Label` for those nodes and uses
  `tuple[None, T]` children, matching the protocol's split.
- **Name collisions / invalid identifiers.** `RustCstGenerator.__init__` already validates
  rule names and labels against `_IDENTIFIER_RE` (`gsm2tree_rs.py:56-67`) and raises
  before emission; the `.pyi` emitter inherits that guard (same instance).
- **Empty-model rules.** `_rule_info` raises `RuntimeError` for models with no types
  (`gsm2tree_rs.py:85-91`); the `.pyi` emitter reusing `_rule_info` fails loudly, same as
  `.rs`. Consistent behavior, no silent skip.
- **Wrong protocol module passed to `--protocol-module`.** A protocol generated from a
  different grammar has a different `NodeKind` member set / class set; the conformance
  fixture and the stub's own pyright self-check fail loudly (unresolved
  `_proto.<Class>`). No silent mis-typing.
- **`.pyi`/`.rs` drift.** Mitigated structurally by deriving both from one
  `RustCstGenerator` instance and `_rule_info()`. A test (§4) asserts the class/label set
  of the `.pyi` equals that of the `.rs`.
- **Trivia rules.** `RustCstGenerator.__init__` runs `add_trivia_rule_to_grammar` +
  `classify_trivia_rules` (`gsm2tree_rs.py:44`); the committed `CstModule` also includes
  trivia nodes (`Trivia`, `LineComment`, `BlockComment` in `fltk_cst_protocol.py`). The
  `.pyi` covers them because it shares that grammar.

---

## 4. Test plan

After this change the following tests exist:

- **`.pyi` content unit tests** (no Rust toolchain; pure string/AST assertions):
  - One class per rule with correct class name and `Label: ClassVar[type[_proto...]]`
    iff labelled.
  - Each node has `kind: Literal[_proto.NodeKind.<MEMBER>]`, `span` (exact protocol
    union), `children`, generic `append/extend/child/extend_children`, and the five
    per-label accessors per label.
  - `children_<label>` typed `Iterator[T]` (regression guard for §3 mismatch).
  - Module-level `<Class>: type[<Class>]` for every rule; **no** module-level `Span`
    (§2.1a).
  - `.pyi` class/label set == `.rs` class/label set (drift guard), both from one
    generator.
- **Protocol-generator test (§2.1a):** regenerated protocol modules have no
  `CstModule.Span` property; the module-level `class Span(Protocol)` remains. Update
  the expected-set assertions (`test_cst_protocol.py:177-178`).
- **`.pyi` pyright self-check** (pyright available; no Rust build): run pyright over the
  emitted `.pyi` alone, assert zero errors. This verifies internal well-typedness only —
  it performs no protocol comparison; that is the next item's job.
- **Stub-vs-protocol conformance fixtures** (pyright available; no Rust build; §2.2
  item 1):
  - Whole-module no-cast fixture: assert **zero errors** (post-§2.1a).
  - Per-class no-cast fixtures (`_g: cstp.Grammar = ...` against stub-typed values):
    assert zero errors. This is the load-bearing verification of the request's core
    constraint and exists in Part 1.
- **CLI test:** `gen-rust-cst grammar.fltkg out.rs --protocol-module ...` writes both
  `out.rs` (unchanged from today — assert byte-identical to current output for the fegen
  grammar) and the `.pyi`; `--pyi-output` overrides the stub path; no `--protocol-module`
  → no `.pyi` (backward compatible).
- **B4 runtime-agreement test (Part 2):** import `fltk._native.fegen_cst`, introspect
  against `fltk/_native/fegen_cst.pyi` in both directions for the generated surface
  (§2.3). Skips cleanly when the extension is unimportable (mirror the
  `pyright_available` skip pattern, `test_cst_protocol.py:58-59`).
- **B4 static conformance of the committed stub (Part 2):** checked-in no-cast
  `CstModule` assignment against `fltk._native.fegen_cst`, zero errors, under the
  repo-wide `uv run pyright` gate (§2.3).
- **Committed-stub sync:** `make check` / gencode-diff discipline keeps
  `fltk/_native/fegen_cst.pyi` regenerated alongside `src/cst_fegen.rs`.

Existing `test_cst_protocol.py` T2a (cast-based, Python backend) and T2b (no-cast must
fail for the concrete Python module) are unchanged; the new fixtures are the Rust-stub
counterparts. `uv run pytest && uv run pyright` is the gate.

---

## 5. Decisions (user, 2026-06-09 — no open questions remain)

### OQ-0 — conformance strategy: **(a) protocol-typed annotations**

As recommended. §2.1 is written against it: member presence from `_rule_info`, type
identities from the committed protocol module via `--protocol-module`. The stub's
deliberate checker-favorable divergences (PyO3 `NodeKind`/`Label` typed as protocol
types; `children_<label>` as `Iterator`) are accepted.

### OQ-A — module-level `Span`: **premise corrected; fix the protocol, not the backends**

The user: "Don't we have a common single Span defined somewhere? We should I think?
that's how Python works — the Span class is not part of the generated CST module; it
lives in a common lib." Verified true (§1): `terminalsrc.Span` / the
`fltk.fegen.pyrt.span` selector / `fltk._native.Span` (`src/lib.rs:20-23`) are the
common-lib `Span`s, and *neither* backend's generated module exports a module-level
`Span` — the original OQ-A framing ("Rust-backend surface gap" to be fixed by
per-module registration) was wrong. Resolution: §2.1a removes the never-satisfiable
`CstModule.Span` property; the stub omits `Span`; per-generated-module `Span`
registration is rejected (§3). Whole-module no-cast conformance target: zero errors.

### OQ-1 — Part 2 scope: **both now**

User overrode the recommendation to defer. Part 2 deliverables are in §2.3: the
`fltk/_native` stub package, gencode wiring, the B4 runtime-agreement test, and the
committed-stub static conformance fixture. `TODO(rust-cst-pyi)` and its `TODO.md` entry
are removed outright; no narrowed follow-up.

### OQ-2 — Part 2 strategy: **prebuilt `fltk._native.fegen_cst`**

User overrode the compile-on-the-fly recommendation. The objection that motivated that
recommendation — the `fltk._native` stub package is a repo-wide typing change deserving
deliberate design — is satisfied by designing it in §2.3 (stub layout, `__init__.pyi`
member list, blast-radius enumeration, shadowing guard, packaging). Net advantages of
prebuilt as chosen: no per-test Cargo build (the extension is already built by the
mandatory `maturin develop` step), and the verification runs against the exact artifact
shipped to consumers of the fegen surface.

### `.pyi` output path

Default `output_file.with_suffix(".pyi")` per the request ("next to the `.rs`"), plus
`--pyi-output` for stem/import-name mismatches (§2.1, §2.3). Pyright resolves stubs by
the compiled module's **import name**, not the `.rs` file name; document this in the
`gen-rust-cst` help text. The fegen case (`src/cst_fegen.rs` → `fegen_cst`) is the
in-repo proof that the override is needed.
