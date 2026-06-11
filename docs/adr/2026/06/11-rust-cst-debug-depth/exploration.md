# Exploration: `rust-cst-debug-depth` TODO adversarial validation

Concise. Token-dense. No fluff.

---

## 1. Claim: `derive(Debug)` emitted on node data structs

**Confirmed.** `gsm2tree_rs.py:640` emits `#[derive(Clone, Debug)]` on every generated node data struct, immediately after the inline TODO comment:

```python
# TODO(rust-cst-debug-depth): derived Debug recurses without depth bound; DoS risk for
# downstream parsers over untrusted input (tree depth is attacker-controlled).
lines.append("#[derive(Clone, Debug)]")
```

The emit is also confirmed in the generated artifacts:
- `src/cst_generated.rs:184` — `pub struct Identifier { … }` carries `#[derive(Clone, Debug)]`
- `src/cst_generated.rs:789` — `pub struct Items { … }` carries `#[derive(Clone, Debug)]`
- Same pattern in `crates/fltk-cst-spike/src/cst.rs`, `tests/rust_cst_fixture/src/cst.rs`, `src/cst_fegen.rs`

The generator also emits `#[derive(Clone, Debug)]` on every child enum (e.g., `IdentifierChild`, `ItemsChild`) at the same location pattern (`_child_enum_block`), `cst_generated.rs:140` and `cst_generated.rs:702`.

Location claimed (~line 638) is accurate; actual line in generator is 640.

---

## 2. Claim: `Shared<T>::Debug` recurses through children without depth bound

**Confirmed.** `crates/fltk-cst-core/src/shared.rs:98–102`:

```rust
impl<T: fmt::Debug> fmt::Debug for Shared<T> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Debug::fmt(&*self.read(), f)
    }
}
```

`self.read()` acquires the RwLock read guard and delegates directly to `T`'s `Debug` impl (i.e., the generated node struct). That struct's `Debug` — emitted by `derive(Debug)` — formats `span` (shallow, `Copy`) and `children: Vec<(label, child_enum)>`. The child enum variant for node-typed children is `ChildEnum::Foo(Shared<Foo>)`, so formatting the enum delegates back to `Shared<Foo>::Debug`, which acquires the next lock and recurses. The chain: `Shared<A>::Debug → A::Debug → Vec<…>::Debug → Shared<B>::Debug → B::Debug → …` with no depth counter anywhere in this path.

The `shared.rs` doc comment acknowledges infinite loops for cycles at `shared.rs:36–40`:
> "`PartialEq`, `Debug`, and other recursive operations will loop infinitely on a cycle"

No mention of depth bounding for the acyclic case.

---

## 3. Claim: handle `__repr__` is non-recursive and is "the model"

**Confirmed.** `gsm2tree_rs.py:1500–1511` emits `__repr__` on the Python handle (`Py<ClassName>` pyclass):

```python
def _repr_method(self, class_name: str, _child_enum_name: str) -> list[str]:
    return [
        "    fn __repr__(&self, _py: Python<'_>) -> String {",
        "        let guard = self.inner.read();",
        '        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());',
        "        let children_len = guard.children.len();",
        "        format!(",
        f'            "{class_name}(span={{span_repr}}, children=[<{{children_len}} child(ren)>])"',
        "        )",
        "    }",
```

This reads only `children.len()` — no recursion into child nodes. This is the Python-visible `repr(node)` and it is already non-recursive. The TODO claims it is "the model" for what a manual depth-capped `Debug` should look like.

The Python backend's node classes (`gsm2tree.py`) have no `__repr__` at all for node structs — the single `__repr__` in `gsm2tree.py:469` is for `_ProtocolLabelMember` (label enum values), not for node objects. Python's default `repr()` on node dataclass objects would recurse too.

---

## 4. Is `derive(Debug)` used in practice?

**Yes — tests in `fltk-cst-spike` explicitly call it.** `crates/fltk-cst-spike/src/spike_tests.rs:364–378`:

```rust
#[test]
fn debug_child_enums_and_node_structs() {
    let src = make_source();
    let span_child = IdentifierChild::Span(span(0, 5, &src));
    let _ = format!("{span_child:?}");

    let items_child = ItemsChild::Identifier(Shared::new(Identifier::new(span(0, 5, &src))));
    let _ = format!("{items_child:?}");    // ← triggers Shared<Identifier>::Debug

    let node = Identifier::new(span(0, 5, &src));
    let _ = format!("{node:?}");

    let shared_node = Shared::new(Identifier::new(span(0, 5, &src)));
    let _ = format!("{shared_node:?}");   // ← triggers the recursive path
}
```

`spike_tests.rs:347` names the test section "Phase 2: Debug smoke test", confirming `derive(Debug)` was added intentionally in Phase 2. These tests use shallow trees (depth 1), so they don't demonstrate the DoS — they only verify compilation and formatting on minimal inputs.

No other `{:?}` format invocations on node data structs appear in the codebase outside of `spike_tests.rs` and the two parser fixture files (which use `{:?}` only on `REGEX_PATTERNS`, not on CST nodes).

---

## 5. Are `apply-depth-limit` / `parser-depth-limit` blockers?

**Partially relevant, but do not eliminate the exposure.**

`apply-depth-limit` (`TODO.md:45–52`, code at `crates/fltk-parser-core/src/memo.rs:89–90`): limits `apply → rule → apply` recursion in the packrat runtime. Has no implementation yet.

`parser-depth-limit` (`TODO.md:76–78`, code at `crates/fltk-parser-core/src/memo.rs` and generated parser comment): limits generated-parser recursion depth. Has no implementation yet.

If both landed and were set to limit N, a successfully parsed tree could have node-nesting depth up to ~N (one node per grammar rule application level). Calling `format!("{:?}", root_node)` on such a tree would then recurse N stack frames for `Debug` in addition to the N already consumed during parsing. The parsing recursion and the `Debug` recursion are separate stack consumers — the parse stack is already gone by the time `Debug` is called.

More importantly: the two depth-limit TODOs gate parse admission, not post-parse operations. After a tree is admitted, callers can hand it to any Rust code that calls `{:?}` — Rust test frameworks (`assert_eq!` failure messages), logging crates, error reporters — with no depth guard at the `Debug` call site.

The parse-time depth limits would bound the *maximum* tree depth of a validly parsed tree. So if `apply-depth-limit` and `parser-depth-limit` both landed and were set to limit N, the Debug recursion on a validly parsed tree would be bounded by N. This is a real mitigation dependency, but it requires: (a) both TODOs implemented, (b) a concrete limit chosen and documented as a security property, (c) that limit set low enough that N stack frames for `Debug` don't overflow (default Linux Rust thread stack is 8 MiB; each frame on x86-64 is typically 64–256 bytes for this pattern, so N=10,000 is feasible but N=100,000 is not). The current TODO text correctly identifies this as "new exposure introduced by Phase 2's `derive(Debug)`" independent of the parse-depth question.

---

## 6. Would replacing `derive(Debug)` break anything?

**No breaking change to current consumers.** `derive(Debug)` on node data structs is not part of the Python-visible API (data structs are Rust-only; Python sees the `Py<ClassName>` handles). The Python `__repr__` (via `_repr_method`) is separate and non-recursive — it would be unaffected.

The only in-tree callers of the Rust-side `Debug` are in `crates/fltk-cst-spike/src/spike_tests.rs` (the three `format!("{:?}", …)` calls). Replacing `derive(Debug)` with a manual implementation that emits the same string as `_repr_method` (i.e., `ClassName { span: Span(start=N, end=M), children: [<K child(ren)>] }`) would require updating only those spike tests. No Python test uses `{:?}` on node data structs.

---

## 7. Feasibility of the fix

The `_repr_method` for the handle is at `gsm2tree_rs.py:1500–1511`. A manual `Debug` impl would emit identically structured output — span start/end plus children count, no recursion. In the generator, this means: instead of `#[derive(Clone, Debug)]` at line 640, emit `#[derive(Clone)]` plus a manual `impl fmt::Debug for {class_name}` block using the same `guard.span.start()`, `guard.span.end()`, `guard.children.len()` pattern. The child enum (`#[derive(Clone, Debug)]` at `_child_enum_block`) can keep its `derive(Debug)` — it is not recursive because `Shared<T>` variants would need a `Debug` impl that does not recurse; alternatively the child enum `Debug` can also be made non-recursive by excluding node-typed variants from `Debug` output or printing only the variant name.

The spike test at `spike_tests.rs:370–371` calls `format!("{items_child:?}")` on an `ItemsChild::Identifier(Shared<Identifier>)`. If `Shared<Identifier>::Debug` were replaced with a non-recursive impl, this test would need updating.

---

## 8. Open factual questions

- What depth limit would `apply-depth-limit` and `parser-depth-limit` establish when implemented? Not yet specified in either TODO entry. Without a concrete limit, the "parse depth bounds Debug depth" argument cannot be evaluated numerically.
- Is there any downstream consumer currently calling `{:?}` on generated node structs? Not visible in this repo. The CLAUDE.md warning about out-of-tree consumers applies: absence of in-tree callers is not evidence of safety.
