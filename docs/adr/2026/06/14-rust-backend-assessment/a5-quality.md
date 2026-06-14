# A5 — CODE QUALITY & MAINTAINABILITY (long-term-owner lens)

Scope assessed: `fltk/fegen/gsm2tree_rs.py` (2351 LoC), `fltk/fegen/gsm2parser_rs.py`
(1036 LoC), `fltk/fegen/gsm2lib_rs.py` (180 LoC), `fltk/fegen/genparser.py` (482 LoC CLI),
the committed generated `crates/fegen-rust/src/cst.rs` (15515 LoC) / `parser.rs` (1656),
and the regen discipline in the `Makefile` / CI. HEAD = c0182064. All citations against
that commit.

The question being answered: **can a new maintainer safely modify the generator code, and
is the committed generated code kept from drifting?**

---

## Verdict: ADEQUATE, trending toward debt

The generators are unusually *well-commented and self-aware* for prototype code — the
intricate parts (collision detection, iterative drop/eq, lock discipline) are documented to
the level of a design spec, and the semantic layer is genuinely single-sourced through
`gsm.py` + the borrowed `CstGenerator`. A careful maintainer reading top-to-bottom can
follow the intent. But the code is held correct by *human-maintained prose plus downstream
`rustc`/`clippy`/pinned tests*, not by any checkable structure: the Rust output bypasses the
IIR entirely and is assembled as raw strings. The result is a maintainability profile where
**the cost of any public-API change is an N-site hand edit across two backends with no
structural guard**, and **the single most important hygiene control for a code-generation
product — an automated "regenerate and diff" gate — is absent**. Several "temporary"
patterns (a deprecated-but-still-used alias, a pyo3 0.23 workaround now on 0.29, dead error
paths) have already hardened into the structure. None of this is unsound today, but it is
the kind of debt that compounds: it makes the backend riskier to evolve than its size
suggests, and it is the strongest argument that what exists is a high-quality prototype
rather than a maintainable production system.

---

## 1. The big structural fact: string emission, no IIR, no machine-checkable output

`gsm2tree_rs.py` and `gsm2parser_rs.py` build a `list[str]` of Rust source lines and
`"\n".join(...)` them. `gsm2tree_rs.py` has ~690 `lines.append/extend` calls;
`gsm2parser_rs.py` ~198. There is **no AST and no IIR for the Rust output**. The Python
backend, by contrast, builds a real `ast.Module` (`gsm2tree.py`) or an `iir.ClassType`
(`gsm2parser.py`) and unparses/compiles it (`genparser.py:96,187,206`).

Concrete consequences for a maintainer:

- **The generator cannot tell you its output is valid.** Whole `#[pymethods]` bodies are
  literal strings (e.g. the `insert` pymethod, gsm2tree_rs.py:1506–1563, is ~50 hand-written
  lines; the entire parser python-bindings block is a triple-quoted template,
  gsm2parser_rs.py:851–924). A typo in any of those strings — a missing brace, a wrong type
  name — is not caught at generation time. It surfaces only when `cargo build`/`make check`
  runs the emitted `.rs`. A maintainer editing an emission string gets no fast feedback loop;
  the edit→build→error cycle is the only validation.
- **There is no symbol table.** Because everything lands in one flat `.rs` namespace shared
  with pyo3 imports and fixed runtime types, the generator has to hand-roll a ~250-line
  identifier-collision subsystem (§4) that an IIR with a symbol table would have provided
  structurally.
- **Lint conformance is itself templated.** Large swaths of `_child_enum_block` /
  `_node_block` / `_native_per_label_methods` exist purely to emit-or-omit a match arm, a
  `_` wildcard, a `_`-prefixed param, or a whole `impl` depending on variant counts and
  child-union membership, so the output passes `clippy -D warnings` (e.g.
  gsm2tree_rs.py:799, 807–808, 824–833, 875, 898–900, 926–929, and the `need_wildcard` /
  `need_unexpected_arm` branches throughout `_native_per_label_methods`). This conditional
  logic is a real chunk of the file's cognitive load and exists only because the generator
  must produce lint-clean text rather than a model the framework lints once.

This is the root cause of most of what follows. It is not wrong — it works, it ships, it is
heavily tested downstream — but it sets the maintainability ceiling.

---

## 2. The maintenance tax: N-site edits, parity held by convention not construction

The *model* layer is shared (good): `RustCstGenerator.__init__` instantiates a real Python
`CstGenerator` (`self._py_gen`, gsm2tree_rs.py:165–170) and delegates every semantic
decision — `rule_models`, `class_name_for_rule_node`, `node_kind_member_name` (explicitly
"single source of truth", :527–533), `protocol_annotation_for_model_types`. A grammar-walk
change lands once in `gsm.py`.

But the *emission* layer is fully duplicated, and worse, **triplicated within the Rust file
itself**. The per-label accessor quintet is emitted three times in Rust:

- pymethods (`_per_label_methods`, gsm2tree_rs.py:2039–2136)
- native GIL-free impl (`_native_per_label_methods`, :1738–2012)
- `.pyi` stub (`generate_pyi`, :377–386)

— versus once-shared in Python (`_emit_label_quintet`, gsm2tree.py:820–867). Same story for
cross-backend eq/hash (gsm2tree.py:99–132 vs gsm2tree_rs.py:539–568), mutators
(`_emit_py_mutators` vs `_generic_*` + `_native_mutators`), separators, and parser fn-naming.

The practical impact on a new maintainer: **adding or changing one node method on the
generated public API is a 4-to-5-site edit** — native impl, handle pymethods, `.pyi` stub,
`register_classes` (if a class), plus the matching Python generator and protocol. Nothing
forces all five to stay aligned. The only backstop is the cross-backend parity test suite
plus a forest of "Mirrors the Python reference" / "matching the Rust backend" comments
(e.g. gsm2parser_rs.py:678–680, :697). Parity by convention, not by construction.

Evidence this already drifts: the internal memo-cache field name is `_cache__parse_X` in
Python (gsm2parser.py:387) but `cache__parse_X` in Rust (gsm2parser_rs.py:155). Harmless
because internal, but it is direct proof the hand-duplicated naming scheme is not
mechanically guaranteed identical — exactly the failure mode that becomes a *public*-surface
bug the day a parity test doesn't cover the changed surface.

---

## 3. NO automated regen-drift gate — the single biggest hygiene gap for a codegen product

`make gencode` (Makefile:247–298) regenerates ~75K lines of committed generated code from
the grammars. Its own comment (Makefile:245–246) admits drift detection is **manual**:
"After running, `git diff --stat` reveals any drift … (cheat-detection: committed
hand-patches show as diffs)."

But `gencode` is **not in `check`, `check-ci`, or `check-common`** (Makefile:39–76; the
`check-common` step list is `lint format-check typecheck test cargo-check cargo-clippy
cargo-test cargo-test-python-features cargo-test-no-python cargo-clippy-no-python
check-no-pyo3` — no `gencode`, no `git diff --exit-code`). CI runs `make check-ci`
(`.github/workflows/ci.yml`), so **CI never regenerates and diffs**.

Consequence: for a project whose generated output is *the public product*, there is no
mechanical guarantee that the committed `cst.rs`/`parser.rs` match what the generators
currently produce. Two failure modes pass CI silently:

1. A generator regression that only manifests on grammars not used to regenerate committed
   fixtures (the committed code is stale but still compiles and passes its own tests).
2. A hand-patch to committed generated code (someone fixes a bug directly in `cst.rs`
   instead of in the generator) — it passes every CI lane while being unreproducible from
   the generator.

This is the one control I would call genuinely *missing* (not merely imperfect). It is a
small Makefile/CI addition (`gencode && git diff --exit-code`) and the absence is the
clearest "we built a prototype's hygiene, not a product's" signal in the quality dimension.

---

## 4. No `@generated` / "Do not edit" header on the committed `cst.rs` (parser.rs has one)

Verified directly: every committed `cst.rs` starts with `use fltk_cst_core::CstError;` — no
provenance header. The generated `parser.rs` files *do* carry one
(`//! Generated by fltk gen-rust-parser from \`...\`. Do not edit.`, emitted at
gsm2parser_rs.py:249–251). The CST generator never emits an analogous banner.

Files checked (all headerless): `crates/fegen-rust/src/cst.rs`,
`tests/rust_poc_cst/src/cst.rs`, `tests/rust_cst_fixture/src/cst.rs`,
`tests/rust_parser_fixture/src/cst.rs`, `crates/fltk-cst-spike/src/cst.rs`.

Consequence: a 15515-line file with no marker that it is machine-generated. Combined with §3
(no drift gate), this actively invites the hand-patch failure mode — a maintainer opening
`cst.rs` to fix something has no in-file signal that the edit will be silently clobbered by
`make gencode` or, worse, that it should never be edited at all. The asymmetry with
`parser.rs` shows the project knows the right pattern; the CST generator just never adopted
it. (The Python generated files are also headerless, so this is at least backend-consistent —
but the bar for a 15K-line public-API artifact is higher.)

---

## 5. "Temporary" patterns that hardened into structure

### 5a. The pyo3 0.23 dual-cfg enum workaround, now unverified on 0.29 (and pinned by a test)

Every label enum and the `NodeKind` enum are emitted **twice** — a `#[cfg(feature="python")]`
pyclass variant and a `#[cfg(not(feature="python"))]` plain variant (gsm2tree_rs.py:580–608,
682–704). The justification (gsm2tree_rs.py:582–585): "cfg_attr on enum variant helper
attributes (pyo3(name=...)) **fails with pyo3 0.23** … Dual-cfg blocks are the correct
pyo3-idiomatic workaround."

Timeline (git): the workaround comment was introduced 2026-06-10 (commit 63e6b76). The
pyo3 0.23→0.29 upgrade landed 2026-06-12 (commit 7d17e98) — *after*. The comment still
says "0.23", the behaviour was never re-checked against 0.29, and a test
(`tests/test_gsm2tree_rs.py:498–502, 575–588`) **pins the dual-cfg emission as required**
with a docstring that also still cites "pyo3 0.23". So the test now enforces a workaround
whose justification may no longer hold, across 15 doubled enum blocks in the committed
`cst.rs` (`grep -c 'cfg(not(feature = "python"))'` = 15). If 0.29 supports the cleaner
`cfg_attr` form, this is dead doubling baked into the generator *and* fenced in by a test
that prevents anyone from noticing. Classic temporary-workaround-hardened-into-structure.

### 5b. Deprecated-but-still-used alias

`_label_enum_rust_name` is documented as "**Deprecated alias** for label_enum_name; kept for
internal call sites pending migration" (gsm2tree_rs.py:650–652) — yet it is still called in
8 places in the file while the canonical `label_enum_name` is used in 37. The migration was
declared but never finished; the dead-end alias is now load-bearing internal API. Minor, but
it is exactly the kind of half-done cleanup that confuses the next maintainer about which
name is canonical.

### 5c. Trivial-passthrough helpers that obscure rather than clarify

`_node_kind_variant_name(class_name)` returns `class_name` unchanged (gsm2tree_rs.py:523–525);
`_node_kind_canonical_name` returns `f"NodeKind.{class_name.upper()}"`. These add an
indirection layer for naming conventions that are one-liners, used at 4 sites. Defensible as
"single source of truth" hooks, but they raise the read cost of an already-large file without
encapsulating real logic.

---

## 6. Dead-but-compiled generated code paths (correctness-adjacent quality smell)

`_label_from_pyobject_match` for a rule **with no labels** (gsm2tree_rs.py:1359–1369) emits a
`match` whose `Some(lbl) => { ... return Err(...) }` arm can never be reached at runtime via
the supported API for label-free nodes, yet it is emitted into every label-free node's
`append`/`extend`/`insert`/`replace_at`. Similarly, `extract_from_pyobject`'s degenerate
"no known child types" branch (gsm2tree_rs.py:926–933) emits `let _ = (_py, _span_type);`
purely to suppress unused-variable lints on a path that always errors. These are correct and
intentional, but they are *generated dead-ish error scaffolding* whose only purpose is lint
appeasement — symptomatic of templating Rust as strings rather than modelling it. They add
to the volume a maintainer must read and reason about per node.

---

## 7. Observability of the generators themselves

Mixed. The collision subsystem produces genuinely good diagnostics: cross-rule collisions
name both offending rules and the identifier family ("Generated Rust identifier {ident!r}
collides: {family} for {rule} vs …; rename one of these rules", gsm2tree_rs.py:246), and the
auto-added trivia rule is annotated in messages so users who never wrote `_trivia` aren't
mystified (:228–232). `genparser.py` catches `ValueError`/`RuntimeError` from the generators
and exits cleanly without leaving partial files (:341–349). Good.

But the failure granularity is coarse where it matters most: because there is no IIR, the
*overwhelmingly likely* generator bug — emitting malformed Rust — produces **no generator
diagnostic at all**. It manifests as a `rustc` error pointing into a 15K-line generated file
with no source-grammar context and no `@generated` header to even tell the reader the file is
machine-produced. A maintainer debugging "why won't the generated parser compile" has to
reverse-map a `cst.rs` line back to which emission method produced it, by hand. That is the
weakest observability story in the whole pipeline, and it is a direct cost of §1 + §4.

---

## 8. Where the engineering is genuinely good (do not refactor away)

To keep this honest — several things are above prototype bar and should be preserved in any
restart:

- **Intra-file dedup is real**: `_emit_rust_cross_backend_eq_hash` (shared NodeKind+Label),
  `_emit_resolve_index_stmts` (remove_at+replace_at), `_emit_count_first_scan_block`
  (child_<l>+maybe_<l>, confirmed used at :2102 and :2119), `_emit_drain_arm`, `_emit_eq_arm`.
  The duplication problem is cross-backend, not within the Rust file.
- **The iterative Drop/PartialEq worklist machinery** (gsm2tree_rs.py:2186–2315 +
  per-node drivers) is a deliberate, well-reasoned defense against attacker-controlled
  stack exhaustion on deep trees — correctly identified threat, correctly documented.
- **Lock-discipline comments** in the mutators ("§2.3 lock discipline": validate before
  taking the write lock; drop the guard before Python work) are precise and consistent.
- **The collision-detection invariant is machine-checked at module load** via `if/raise`
  (not `assert`, so it survives `python -O`) — gsm2tree_rs.py:118–142. That is exactly the
  right rigor for a hand-maintained invariant.

The comments-as-spec density (283 pure-comment lines + extensive docstrings in 2352 total)
is a double-edged sword: excellent for a one-time auditor, but it means correctness lives in
prose a maintainer must keep in sync by hand, with no compiler to catch prose that drifts
from emission.

---

## Bottom line for the retrospective

Quality is **adequate but debt-trending**. The generators are readable, heavily documented,
and semantically single-sourced — a competent maintainer *can* modify them. But three things
make modification riskier than the size implies, and all three stem from the string-emission /
no-IIR choice: (1) every public-API change is an N-site hand edit held in lockstep only by
tests and comments; (2) there is no automated regen-drift gate, so committed generated code
(the actual product) can silently diverge from the generators in CI; (3) a 15K-line generated
public-API file carries no "do not edit" header. Layered on top are several
temporary-patterns-turned-structural (a pyo3 0.23 workaround now unverified on 0.29 and
fenced by a test, a deprecated-but-used alias, generated dead error scaffolding for lint
appeasement). None is unsound today. Collectively they say: this is a high-quality
**prototype's** quality bar, not a production system's. The cheapest high-value fixes are the
regen-drift CI gate and the `@generated` header — both small, both currently missing.
