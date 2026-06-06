# Spike: label-free node empty-enum vs Protocol (pyright)

Empirical spike. No git-tracked files were modified. All work done in
`/tmp/labelfree-spike` against generated artifacts only (the generator
`fltk/fegen/gsm2tree.py` was NOT touched).

Tooling: `uv run pyright` (pyright 1.1.402, installed in the project venv).

## Setup / Grammar

Minimal grammar producing a zero-label node (`/tmp/labelfree-spike/lf.fltkg`):

```
top := foo+ ;
foo := $"x" , $"y" ;
```

- `top := foo+` — `foo` is a rule reference, which auto-labels, so `top` is a
  labeled node (label `FOO`). This is scaffolding (an entry rule that references
  the zero-label rule).
- `foo := $"x" , $"y"` — only `$`-disposition literals, no labels → **zero-label
  node**. This is the node of interest.

Generated via the pure-Python CLI (no maturin/Rust build needed):

```
uv run python -m fltk.fegen.genparser generate /tmp/labelfree-spike/lf.fltkg \
    lf lf_cst -o /tmp/labelfree-spike --no-trivia-only
```

Outputs: `lf_cst.py` (concrete), `lf_cst_protocol.py` (Protocol),
`lf_parser.py`. (A `Trivia` node is auto-added by the trivia pass; ignore it.)

### Generated zero-label CONCRETE class (`lf_cst.py`)

```python
@dataclasses.dataclass
class Foo:

    class Label(enum.Enum):
        _fltk_canonical_name: str

        def __eq__(self, other: object) -> bool:
            if other is self:
                return True
            if type(other) is type(self):
                return self.name == other.name
            cn = getattr(other, '_fltk_canonical_name', None)
            if cn is not None:
                return self._fltk_canonical_name == cn
            return NotImplemented

        def __hash__(self) -> int:
            return hash(self._fltk_canonical_name)
    kind: typing.Literal[NodeKind.FOO] = NodeKind.FOO
    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[typing.Optional[Label], typing.Union['Trivia', 'fltk.fegen.pyrt.terminalsrc.Span']]] = dataclasses.field(default_factory=list)

    def append(self, child: typing.Union['Trivia', 'fltk.fegen.pyrt.terminalsrc.Span'], label: typing.Optional[Label]=None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[typing.Union['Trivia', 'fltk.fegen.pyrt.terminalsrc.Span']], label: typing.Optional[Label]=None) -> None:
        self.children.extend(((label, child) for child in children))

    def child(self) -> tuple[typing.Optional[Label], typing.Union['Trivia', 'fltk.fegen.pyrt.terminalsrc.Span']]:
        if (n := len(self.children)) != 1:
            msg = f'Expected one child but have {n}'
            raise ValueError(msg)
        return self.children[0]
```

The empty `Label` enum carries only `_fltk_canonical_name`/`__eq__`/`__hash__`
(no members). `children` is `list[tuple[Optional[Label], ...]]`.

### Generated zero-label PROTOCOL counterpart (`lf_cst_protocol.py`)

```python
class Foo(typing.Protocol):
    kind: typing.Literal[NodeKind.FOO] = NodeKind.FOO
    span: fltk.fegen.pyrt.terminalsrc.Span
    children: list[tuple[None, typing.Union['Trivia', fltk.fegen.pyrt.terminalsrc.Span]]]

    def append(self, child: typing.Union['Trivia', fltk.fegen.pyrt.terminalsrc.Span], label: None=None) -> None:
        ...

    def extend(self, children: typing.Iterable[typing.Union['Trivia', fltk.fegen.pyrt.terminalsrc.Span]], label: None=None) -> None:
        ...

    def child(self) -> tuple[None, typing.Union['Trivia', fltk.fegen.pyrt.terminalsrc.Span]]:
        ...
```

The Protocol emits **NO** `Label` class and uses `list[tuple[None, ...]]` /
`child() -> tuple[None, ...]` / `label: None`. So the concrete and Protocol
zero-label surfaces genuinely diverge:
`tuple[Optional[Label], ...]` (concrete) vs `tuple[None, ...]` (Protocol).

## Step 2 — Empty-enum compile/typecheck

`uv run pyright /tmp/labelfree-spike/lf_cst.py` (project context):

```
0 errors, 0 warnings, 0 informations
```

Import:

```
$ PYTHONPATH=... python -c "import lf_cst; print(lf_cst.Foo())"
IMPORT_OK
Foo(kind=<NodeKind.FOO: 2>, span=Span(start=-1, end=-1), children=[])
```

**The empty `Label` enum (no members, with the eq/hash body) passes pyright with
zero errors and imports without error.** An empty `enum.Enum` subclass is legal
both at type-check time and at runtime.

## Step 3 — Concrete-vs-Protocol conformance

Two patterns were tested, because the production code path matters:

### (3a) Direct structural assignment (`consumer.py`)

```python
import lf_cst as concretemod
import lf_cst_protocol as protomod
def f(x: protomod.Foo) -> None: ...
f(concretemod.Foo())
```

pyright (BEFORE fix):

```
error: Argument of type "Foo" cannot be assigned to parameter "x" of type "Foo" in function "f"
  "Foo" is incompatible with protocol "Foo"
    "kind" is invariant because it is mutable
    "kind" is an incompatible type
      "lf_cst.NodeKind" is not assignable to "lf_cst_protocol.NodeKind"
    "children" is invariant because it is mutable
    "children" is an incompatible type
      "list[tuple[Label | None, Trivia | Unknown]]" is not assignable to "list[tuple[None, Trivia | Unknown]]"
    "child" is an incompatible type
  ...
```

So under direct structural assignment the concrete class does **NOT** satisfy its
own generated Protocol. There are TWO independent causes:
1. `children` (invariant list) / `child()` return: `tuple[Label | None, ...]`
   vs `tuple[None, ...]` — **this is the label-free-specific mismatch.**
2. `kind`: `lf_cst.NodeKind` vs `lf_cst_protocol.NodeKind` — a cross-module
   nominal mismatch.

### Important context: cause #2 is pre-existing and NOT label-free-specific

The same direct-structural test on the LABELED node `Top`
(`g(concretemod.Top())`) also fails, with the `kind` mismatch AND a
`Top.Label` nominal mismatch (`lf_cst.Top.Label` vs
`lf_cst_protocol.Top.Label`). i.e. direct structural concrete→Protocol
assignment never type-checks for ANY node, label-free or not, because the two
generated modules define their own `NodeKind` and their own nested `Label`
types.

This matches the in-tree design: `fltk/fegen/test_cst_protocol.py` consumes the
concrete module only via `typing.cast(cstp.CstModule, fltk_cst)` (see
`_MEMBER_ACCESS_FIXTURE`, and `test_boundary_probe_documents_label_mismatch`,
which asserts that bare `fltk_cst -> CstModule` assignment is *expected* to
error). The cast at the DI boundary is intentional and documented.

### (3b) Production pattern: CstModule cast + member access (`member_access.py`)

Mirrors `_MEMBER_ACCESS_FIXTURE`:

```python
_m: cstp.CstModule = cast(cstp.CstModule, lf_cst)
def _check_foo(foo: cstp.Foo) -> None:
    _ = foo.span
    _ = foo.children
    _ = foo.child()
```

pyright (BEFORE fix):

```
0 errors, 0 warnings, 0 informations
```

**Under the production pattern, the zero-label divergence is invisible** — member
access through the cast resolves cleanly even with the empty-enum /
`Optional[Label]` mismatch present.

## Step 4 — Simulate the proposed fix (generated concrete file only)

Edited `lf_cst.py`'s `Foo` class only (NOT the generator): dropped the empty
`Label` enum entirely, and changed `children` to `list[tuple[None, ...]]`,
`label: None` in append/extend, and `child() -> tuple[None, ...]` — i.e. made the
concrete surface match the Protocol.

Results after the fix:

- pyright on fixed concrete alone (project ctx): `0 errors, 0 warnings`.
- Import: `IMPORT_OK Foo(kind=<NodeKind.FOO: 2>, span=..., children=[])`.
- `member_access.py` (production cast pattern): `0 errors` (unchanged — still clean).
- `consumer.py` (direct structural): the `children`/`child` errors are **GONE**.
  The only remaining error is the pre-existing, label-independent `kind`
  cross-module mismatch:

```
error: Argument of type "Foo" cannot be assigned to parameter "x" ...
  "Foo" is incompatible with protocol "Foo"
    "kind" is invariant because it is mutable
    "kind" is an incompatible type
      "lf_cst.NodeKind" is not assignable to "lf_cst_protocol.NodeKind"
```

So the fix removes the entire label-free-specific portion of the mismatch
(`children` invariant-list + `child()` return). The residual `kind` error is the
same cross-module NodeKind nominal mismatch that affects every node and is
handled in production by the `CstModule` cast (it is not introduced or worsened
by this fix, and is out of scope for the label-free issue).

## Step 5 — Definitive statements

(a) **Does the current empty-enum emission pass pyright + import?**
    YES. `lf_cst.py` as generated passes `uv run pyright` with 0 errors and
    imports cleanly. The empty `Label(enum.Enum)` with the eq/hash body is valid
    at type-check and at runtime.

(b) **Does the current concrete satisfy its Protocol?**
    Depends on how it is consumed.
    - Direct structural assignment (`f(x: proto.Foo); f(concrete.Foo())`): NO.
      Two mismatches: the label-free-specific `children`/`child`
      (`tuple[Optional[Label], ...]` vs `tuple[None, ...]`), AND the
      label-independent cross-module `kind` (`NodeKind`) mismatch. The `kind`
      mismatch (plus nested-`Label` for labeled nodes) is pre-existing, affects
      all nodes, and is by design handled via `typing.cast(CstModule, ...)`.
    - Production pattern (`cast(cstp.CstModule, concrete)` + member access): YES,
      0 errors, even before any fix. The divergence is masked by the cast.

(c) **Does the proposed fix (drop enum + match annotation) pass pyright and
    resolve conformance?**
    YES, for the label-free-specific part. After dropping the empty enum and
    switching to `tuple[None, ...]` / `label: None`:
    - the fixed concrete module passes pyright (0 errors) and imports;
    - the production-pattern fixture still passes (0 errors);
    - the direct-structural conformance check loses the `children`/`child`
      errors entirely. The fix makes the concrete and Protocol zero-label
      surfaces agree. The only residual direct-structural error is the
      pre-existing cross-module `kind` NodeKind mismatch, which is unrelated to
      the label-free issue and is the intended job of the `CstModule` cast.
