# U3 — MAP: The Code Generators (Rust backend)

Scope: `fltk/fegen/gsm2tree_rs.py` (2351 LoC), `gsm2parser_rs.py` (1036 LoC),
`gsm2lib_rs.py` (180 LoC), `genparser.py` (482 LoC CLI), compared against the
Python-backend counterparts `gsm2tree.py` (1026 LoC) and `gsm2parser.py` (845 LoC),
plus the shared `gsm.py` (Grammar Semantic Model) and `naming.py` (22 LoC leaf).

HEAD = c0182064. All line citations are against that commit.

---

## 1. Emission strategy: structured IIR vs raw string templating

There are **two completely different emission philosophies** between the backends, and
this is the single most important architectural fact about the Rust generators.

### Python backend — builds an AST / IIR, then unparses
- `gsm2tree.py` builds a real Python `ast.Module` via the `pygen` helpers
  (`pygen.dataclass`, `pygen.function`, `pygen.klass`, `pygen.stmt`, `ast.parse(...)`),
  then `genparser.py` calls `ast.unparse(...)` (genparser.py:187, :206, :114). 106 `pygen.`
  calls in gsm2tree.py.
- `gsm2parser.py` builds an `iir.ClassType` out of `iir.Method`, `iir.Construct`,
  `iir.If`, `iir.While`, `iir.SelfExpr()...` nodes (141 `iir.` calls) and compiles it
  through `fltk.iir.py.compiler.compile_class` (genparser.py:95–96). The output is a
  typed model that knows about scopes, variables, moves/borrows, and types.

### Rust backend — emits `.rs` text directly as strings
- **There is no IIR and no AST for the Rust output.** Both Rust generators assemble a
  `list[str]` of source lines and `"\n".join(...)` them. Density: gsm2tree_rs.py has
  **690** `lines.append/extend` calls; gsm2parser_rs.py has **198** `*.append` calls.
  Whole `#[pymethods]` bodies are literal string blocks (e.g. the `insert` pymethod is
  ~50 hand-written lines, gsm2tree_rs.py:1506–1563; the entire parser python-bindings
  block is one triple-quoted boilerplate template, gsm2parser_rs.py:851–924, 958–968).
- gsm2tree_rs.py imports `iir` only for `create_default_context()` and `pyreg.Builtins`
  (gsm2tree_rs.py:14–15, used at :163–168) — i.e. only to *construct the borrowed Python
  CstGenerator*, never to model Rust output. gsm2parser_rs.py has **zero** `iir.` usage.
- `gsm2lib_rs.py` is the simplest: a `LibSpec`/`Submodule` dataclass description plus a
  `RustLibGenerator.generate()` that string-builds `lib.rs`. It consumes no grammar at all
  (gsm2lib_rs.py:5–7) — it is pure module-wiring templating parameterized by module name
  and a span/parser flag set.

Consequence: the Rust path has **no type checking, no scope tracking, and no
machine-verification that the emitted source is even syntactically valid Rust**. Validity
is established only downstream by `rustc`/`clippy` at `cargo build`/`make check` time.
The generators compensate with hand-written guards (see §4) and a *huge* volume of
load-bearing comments explaining why each emitted token is correct.

---

## 2. How the generators walk `gsm.Grammar` — and what IS shared

### The semantic (model) layer IS shared; the emission layer is NOT.

`RustCstGenerator.__init__` (gsm2tree_rs.py:162–170) **instantiates a real Python
`CstGenerator`** (`self._py_gen`) over the same trivia-processed grammar:

```python
grammar_with_trivia = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))
self._py_gen = CstGenerator(grammar=grammar_with_trivia, py_module=pyreg.Builtins, context=context)
```

The Rust CST generator then **delegates every semantic decision** to that Python object:
- `self._py_gen.rule_models[rule.name]` — the `ItemsModel` (labels → types, types set).
  This is THE grammar-walk: `CstGenerator.model_for_rule` / `model_for_items` /
  `model_for_alternatives` (gsm2tree.py:1008–1026, 625–649) does the recursion over
  alternatives, items, sub-expressions, dispositions (SUPPRESS/INLINE), and trivia
  incorporation. The Rust generator never re-derives the model; it reads `model.labels`
  and `model.types` (e.g. gsm2tree_rs.py:236–238, :275–276, :288–294, :1721–1724).
- `class_name_for_rule_node` → `naming.snake_to_upper_camel` (gsm2tree.py:46–47,
  naming.py:7–22). Both backends share this one naming function for rule→class names.
- `node_kind_member_name` — gsm2tree_rs.py:527–533 explicitly delegates so "CstGenerator
  is the single source of truth for this naming convention across .rs, .pyi, and protocol."
- `protocol_annotation_for_model_types` — reused by the `.pyi` generator
  (gsm2tree_rs.py:398–414 wraps gsm2tree.py:660–690 and post-processes the string with a
  regex to `_proto.`-qualify rule refs).

So the **grammar-walking and label/type-modelling logic is genuinely shared** (single
source of truth = `gsm.CstGenerator` + `gsm.py`). A grammar-semantics change that affects
*which children/labels a rule produces* is implemented once in `gsm.py`/`gsm2tree.py` and
both backends pick it up.

### The Rust parser generator's own grammar walk
`RustParserGenerator` (gsm2parser_rs.py:67) holds a `RustCstGenerator` (`self._cst`,
:80) and works off `self._cst.grammar` (the trivia-processed grammar). It then does its
**own independent recursive descent** over `rule.alternatives → alt.items → item.term`
to emit parser functions:
- `_gen_rule` → `_emit_rule_body` → `_gen_alternative` → `_gen_item`
  (`_gen_item_multiple` / `_gen_item_single_or_optional`) → `_gen_consume_term`
  (gsm2parser_rs.py:454–804). This mirrors, function-for-function, the Python parser's
  `gen_alternatives_parser` / `gen_alternative_parser` / `gen_item_parser*` /
  `_gen_consume_term_expr` (gsm2parser.py:699–845, 475–618, 303–375) — but re-implemented
  as string emission with no shared base class.
- Term dispatch (`Identifier` / `Literal` / `Regex` / sub-expression list/tuple /
  `Invocation`) is hand-coded twice: gsm2parser_rs.py:736–774 vs gsm2parser.py:303–375.
  Rust raises `NotImplementedError` for `Invocation` terms (gsm2parser_rs.py:768–770) —
  a real feature gap vs the Python backend's term handling.

---

## 3. Structural duplication — the maintenance tax

Despite the shared *model* layer, the **emission logic is copied, not shared**, between
Python and Rust. Concretely duplicated grammar-aware logic that lives in BOTH a Python
generator and a Rust generator:

| Concept | Python site | Rust site |
|---|---|---|
| Per-label accessor *quintet* (append/extend/children/child/maybe) | `_emit_label_quintet` gsm2tree.py:820–867 (shared only between concrete + protocol Python) | re-hand-written 5× as Rust strings: pymethods in `_per_label_methods` gsm2tree_rs.py:2039–2136; native in `_native_per_label_methods` :1738–2012; pyi in `generate_pyi` :377–386 |
| Cross-backend enum `__eq__`/`__hash__` | `_emit_cross_backend_eq_hash` gsm2tree.py:99–132 | `_emit_rust_cross_backend_eq_hash` gsm2tree_rs.py:539–568 (separate impl, same contract) |
| Named mutators insert/remove_at/replace_at/clear (incl. clamp + parity error text) | `_emit_py_mutators` gsm2tree.py:386–610 | `_generic_insert/_generic_remove_at/_generic_replace_at/_generic_clear` gsm2tree_rs.py:1506–1703 + native `_native_mutators` :1468–1504 |
| Index normalization / clamping semantics | gsm2tree.py:541–602 | gsm2tree_rs.py:1528–1559, `_emit_resolve_index_stmts` :1565–1587 |
| Parser fn-name scheme `parse_` + `"__".join(path)`, `apply__`, memo cache | gsm2parser.py:380–394, 377–378 | gsm2parser_rs.py:143–171 |
| Separator/trivia handling (WS_ALLOWED/WS_REQUIRED, capture_trivia) | `_gen_separator_handling` gsm2parser.py:620–697 | `_gen_separator_code` gsm2parser_rs.py:568–627 |
| Zero-width-match progress guard for `+`/`*` loops | gsm2parser.py:570–577 | gsm2parser_rs.py:698–701 (comment at :697 says "Mirrors the identical Python guard") |
| Append/push-child code per disposition+label | gsm2parser.py:801–813 | `_gen_append_code` / `_gen_append_code_for_consumed` gsm2parser_rs.py:810–832, 998–1036 |

The duplication is **acknowledged in-code**: numerous comments say "Mirrors the Python
reference", "matching the Rust backend (§3)", "matching Python's pinned message text",
"match Python reference path tuple scheme … preserve side-by-side auditability"
(gsm2parser_rs.py:678–680). The two backends are kept behaviorally identical by
*convention + pinned cross-backend tests*, not by a shared abstraction.

### Where a grammar-semantics change forces edits in BOTH generators
- **Adding/changing a child-disposition rule** (e.g. a new `Disposition`, or changing how
  SUPPRESS/INLINE map to children): touches `gsm2parser.py` append logic AND
  `gsm2parser_rs.py:810–832, 1007–1036` AND the model in `gsm2tree.py:625–643`. Note Rust
  currently *rejects* INLINE disposition outright (`NotImplementedError`,
  gsm2parser_rs.py:824–826, 1010–1012) — a divergence, not parity.
- **Changing the per-label accessor surface** (rename/add a method in the quintet, change a
  signature): Python edits `_emit_label_quintet` once; Rust requires editing **three**
  separate hand-written emitters (pymethods, native, and the `.pyi` stub) plus the protocol
  in gsm2tree.py to keep the public API aligned.
- **Changing a separator/trivia behavior**: both `_gen_separator_handling` and
  `_gen_separator_code` must change, and the trivia-class lookup
  (`gsm.TRIVIA_RULE_NAME`) is referenced in both.
- **Changing the parser fn-naming scheme or memoization shape**: both `_make_parser_info`
  implementations must change in lockstep (cross-backend audit relies on identical names).
- **Adding a new node-level method** (e.g. another mutator): Python emits in
  `_emit_py_mutators` + protocol; Rust must emit in the *native* impl block, the *handle*
  pymethods block, AND the `.pyi` stub — and add it to `register_classes` if it is a class.

Naming itself is NOT fully parity-faithful even where it claims to be: cache field is
`_cache__parse_X` (Python, gsm2parser.py:387) vs `cache__parse_X` (Rust,
gsm2parser_rs.py:155) — only the public `apply__parse_X` method names match exactly. These
are internal, but they show the duplication is maintained by hand and can silently drift.

---

## 4. Naming / identifier-collision handling (Rust-only, large and intricate)

The Rust CST generator carries a **substantial, self-aware collision-detection subsystem**
that has no Python-backend analogue (Python emits to its own module namespace; Rust emits
into one flat `.rs` namespace shared with pyo3 imports and fixed runtime types). This is
~250 lines of module-level tables + `__init__` checks (gsm2tree_rs.py:17–249):

- `_IDENTIFIER_RE` (:22): every rule name and item label is validated against
  `^[_a-z][_a-z0-9]*$` *before any emission*, because they are interpolated directly into
  Rust identifiers and string literals — explicitly framed as **build-time code-injection
  defense** on the dev/CI host (:172–193).
- `_RESERVED_LABELS` (:28–30): label `children` would generate `extend_children` colliding
  with the fixed handle method — rejected at gen time (:194–201).
- `_RESERVED_CLASS_NAMES` (:43–75): rule-derived class names that would collide with
  `fltk_cst_core` types (`Span`, `Shared`, `CstError`), the generated `NodeKind`/worklist
  enums, or unqualified pyo3 prelude/exception imports (`Bound`, `Py`, `Python`,
  `IntoPyObject`, `IndexError`, `TypeError`, `ValueError`).
- `_RESERVED_CLASS_NAMES_SEEDED` (:86–106): pyo3 method-trait names (`PyAnyMethods`, …)
  that are in `Py{CN}` *handle* form and so must be seeded into the cross-rule claims dict.
- A **module-load-time invariant check** (`if/raise`, not `assert`, so it survives
  `python -O`) verifying no reserved name can shadow a derived `Py{CN}`/`{CN}Child`/
  `{CN}Label` identifier (:108–142).
- **Cross-rule collision check** in `__init__` (:203–249): builds a `claims` dict mapping
  every derived identifier (node struct `{CN}`, handle `Py{CN}`, child enum `{CN}Child`,
  label enum `{CN}Label`) back to its rule, and reports any identifier claimed by >1 rule
  (catches non-injective `snake_to_upper_camel`, e.g. `foo_bar` and `foo__bar` → `FooBar`,
  and `foo_child` rule vs `foo` rule's `FooChild` enum). The `{CN}Label` identifier is only
  claimed for rules that actually have labels (:237–238) to avoid breaking grammars that
  compile today.

This subsystem exists **because** of the string-emission choice into a shared namespace —
an IIR with a symbol table would have surfaced most of these collisions structurally. It is
careful and well-documented, but it is a large maintenance surface unique to Rust, and the
comments themselves note future reserved names "must also be seeded into claims"
(:42, :112–117) — i.e. it is a manually-maintained invariant.

The parser generator deliberately **opts out** of this analysis: it emits only fixed class
names (`PyParser`, `PyApplyResult`, never rule-derived `PyX`), so it retains
`use pyo3::prelude::*` glob inside `mod python_bindings` (gsm2parser_rs.py:838–857). The
asymmetry is called out as load-bearing (:842–850).

---

## 5. Label-enum and child-enum generation

- **Label enum** (`_label_enum_block`, gsm2tree_rs.py:659–728): one Rust enum per rule
  *that has labels* (Rust enums can't be zero-variant, so label-free rules emit nothing,
  :668–669). Phase-2 naming split: Rust name is CamelCase `{CN}Label`
  (`label_enum_name`, :639–647) but the **Python-visible name is preserved** as
  `{CN}_Label` via `#[pyclass(name = "{CN}_Label")]` (:655–657, :690) — an explicit
  backward-compat decision (CLAUDE.md: renaming public symbols is breaking). Emitted twice:
  a `#[cfg(feature="python")]` pyclass variant and a `#[cfg(not(...))]` plain variant
  (:682–704), because pyo3 0.23 `cfg_attr` on variant helper attrs failed (:583–586) —
  a worked-around toolchain limitation now baked into the generator.
- **Child value enum** (`_child_enum_block`, :768–938): one `{CN}Child` enum per rule with
  a `Span(Span)` variant for terminal/literal/regex children plus one `{Cls}(Shared<{Cls}>)`
  variant per referenced rule. Carries hand-emitted `PartialEq`, `into_drop_item`,
  `eq_shallow_enqueue`, `to_pyobject`, `extract_from_pyobject`. Variant/method emission is
  conditioned on `has_span`, `child_classes`, `child_union` membership, and variant count
  (to suppress `-D warnings` dead-code / unreachable-pattern / unused-variable lints) — this
  conditional logic (e.g. :799, :807–808, :824–833, :860, :875, :898–900, :926–929) is a
  major source of the file's complexity.
- `child_enum_name` / `py_handle_name` / `label_enum_name` are `@staticmethod` "single
  source of truth" helpers (:734–749, :639–647) reused by the parser generator
  (gsm2parser_rs.py:190–191) so a rename propagates.

---

## 6. Accessor generation

For each rule, the handle pyclass (`_node_block`, gsm2tree_rs.py:944–1231) emits:
- fixed methods: `new`, `span` getter/setter, `kind` getter, `children` getter, generic
  `append/extend/extend_children/child/insert/remove_at/replace_at/clear`, `__eq__`,
  `__hash__`, `__repr__`, and (for labeled rules) the `Label` classattr.
- per-label quintet pymethods (`_per_label_methods`, :2039–2136):
  `append_<l>/extend_<l>/children_<l>/child_<l>/maybe_<l>`.

Separately, the **plain data-struct impl** emits a *native (GIL-free) Rust API*
(`_native_per_label_methods` :1738–2012, `_native_mutators` :1468–1504) — the suffixless
surface generated parsers build against. So per label there are effectively two parallel
accessor families (pymethod + native) plus a `.pyi` stub family — three emission sites that
must stay aligned (see §3). The native accessors carry real semantics: `child_<l>` returns
`Result<_, CstError>` with `ChildCount`/`UnexpectedChildType` variants, single-vs-union
label typing via `_label_type_info` (:1705–1736), and zero-alloc `(next, next)` count
patterns. There is genuine engineering here, but it is ~570 lines of hand-built strings for
one concept.

A known **runtime/stub divergence** is baked in and commented: the native/pymethod
`children_<l>` returns a `list`, but the `.pyi` declares `Iterator[T]`
(gsm2tree_rs.py:382–384) to satisfy the protocol — a deliberate documented lie in the stub.

---

## 7. Complexity and readability assessment

- **2351 lines is large for one generator**, but the bulk is *not* algorithmic complexity —
  it is **string volume**: 690 `lines.append` calls emitting Rust tokens, plus an unusually
  high comment-to-code ratio. Many methods are pure templating (`_new_method`,
  `_span_getter_setter`, `_generic_*`) returning fixed `list[str]`.
- The **genuinely intricate** parts are: (a) the collision subsystem (§4, ~250 lines of
  invariant-maintaining tables + the `if/raise` machine-check); (b) the lint-suppression
  conditional logic in `_child_enum_block`/`_node_block` (emit-or-omit a match arm / Drop
  impl / `_` wildcard / `_`-prefixed param depending on variant counts and child-union
  membership); (c) the iterative Drop / iterative PartialEq / worklist machinery
  (`_drop_block` :2205–2243, `_eq_block` :2271–2315, and their per-node drivers) emitted to
  avoid attacker-controlled stack-exhaustion on deep trees.
- **Readability is carried by comments, not structure.** The code is heavily commented to
  the point that the comments are the spec (e.g. the entire `_preamble` is interleaved prose
  explaining every import's collision rationale, :461–517). This is a double-edged sword:
  excellent for an auditor reading once, but it means correctness lives in human-maintained
  prose + downstream `rustc`/`clippy`/pinned tests rather than in a checkable model.
- There is **good intra-file dedup**: `_emit_rust_cross_backend_eq_hash` (NodeKind+Label),
  `_emit_resolve_index_stmts` (remove_at+replace_at), `_emit_count_first_scan_block`
  (child_<l>+maybe_<l>), `_emit_drain_arm`, `_emit_eq_arm`, and the static name helpers.
  The duplication problem is **cross-backend** (Python↔Rust), not within the Rust file.

---

## 8. genparser.py (CLI)

`genparser.py` (482 LoC) is the typer CLI exposing four commands:
- `generate` (:120–252) — the *Python* backend path (CST + protocol + two parsers).
- `gen-rust-cst` (:265–363) — constructs `RustCstGenerator`, optionally emits a `.pyi`
  stub (requires `--protocol-module`). Generates `.pyi` text *before* opening any file so a
  failure leaves no partial artifact (:341–349).
- `gen-rust-parser` (:368–397) — validates `--cst-mod-path` against `_CST_MOD_PATH_RE`
  (:365), constructs `RustParserGenerator`.
- `gen-rust-lib` (:400–478) — constructs `LibSpec` and `RustLibGenerator`.

The Rust CLI commands consume the **raw** grammar (`_parse_grammar_raw`, :255–262) because
`RustCstGenerator` applies trivia processing internally — whereas the Python `generate`
path applies trivia in the CLI (`parse_grammar_file`, :66–70). This asymmetry is a small
trap: the same grammar flows through two different pre-processing entry points depending on
backend. There is a `TODO(rust-ident-dedup)` (gsm2lib_rs.py:16–18) noting the
`_CST_MOD_PATH_RE` / `_validate_rust_ident` single-segment validators are hand-duplicated
between genparser.py and gsm2lib_rs.py.

---

## 9. Bottom line for the retrospective

- **Shared where it matters semantically, duplicated where it matters operationally.** The
  grammar walk and the label/type model are genuinely single-sourced via `gsm.py` +
  `CstGenerator`. But every line of *target syntax* is emitted twice — once as Python AST,
  once as Rust strings — with no shared emission abstraction. The Rust output bypasses the
  IIR entirely.
- The string-templating choice is the root cause of two whole subsystems that exist only on
  the Rust side: the **identifier-collision detector** (§4) and the pervasive
  **lint-suppression conditional emission** (§7). An IIR/symbol-table approach would have
  folded most of both into the framework.
- **Maintenance tax is real and concentrated** at: per-label accessors (3 Rust emission
  sites + protocol), mutators (native + pymethod + pyi + Python), dispositions, separators,
  and parser fn naming. Any change to the generated public API surface is an N-site edit, and
  parity is enforced by convention + pinned tests, not by construction.
- **Feature gaps / divergences** that the string approach has left standing: Rust rejects
  `INLINE` disposition (`NotImplementedError`, gsm2parser_rs.py:824, 1010) and `Invocation`
  terms (:768); children-getter list-identity differs from Python (gsm2tree_rs.py:1304–1315);
  `children_<l>` stub/runtime type diverge (:382–384). These are documented, but they mean
  the "near-drop-in replacement" claim has explicit holes a downstream consumer could hit.
