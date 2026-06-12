# Adversarial validation: TODO(empty-cn-underscore-rule)

Concise. Precise. No padding. Audience: implementer/reviewer.

---

## Claim being validated

> Underscore-only rule names (`_`, `__`, etc.) pass `_IDENTIFIER_RE` but
> `snake_to_upper_camel` collapses them to CN `""`, producing `pub struct  {`
> (Rust syntax error) with no generation-time diagnostic. Fix: reject rule names
> whose derived CN is empty — either tighten `_IDENTIFIER_RE` to require at least
> one `[a-z0-9]` character, or add an explicit post-CN check. Location:
> `fltk/fegen/gsm2tree_rs.py` (`_IDENTIFIER_RE` definition and per-rule
> validation in `RustCstGenerator.__init__`).

---

## Verification results

### `_IDENTIFIER_RE` admits underscore-only names — CONFIRMED

`fltk/fegen/gsm2tree_rs.py:22`:
```python
_IDENTIFIER_RE = re.compile(r"^[_a-z][_a-z0-9]*$")
```
`_`, `__`, `___` all match: the pattern requires only `[_a-z]` at position 0,
then zero or more `[_a-z0-9]`. No lower-bound on non-underscore characters.

This is also consistent with the grammar-level identifier rule
(`fltk/fegen/fegen.fltkg:16`):
```
identifier := name:/[_a-z][_a-z0-9]*/ ;
```
The grammar itself admits underscore-only identifiers; `_IDENTIFIER_RE` was
written to match it exactly.

### `snake_to_upper_camel` collapses underscore-only names to `""` — CONFIRMED

`fltk/fegen/naming.py:22`:
```python
return "".join(part.capitalize() for part in name.lower().split("_"))
```
`"_".split("_")` → `["", ""]`; `"".capitalize()` → `""`. All segments are
empty after splitting on `_`, so the join produces `""`. The docstring at
`naming.py:16` documents this:
> Leading underscore collapses: `"_foo_bar"` -> `"FooBar"`

For purely underscore names there are no non-underscore segments to capitalize.

### Empty CN is not caught by `_RESERVED_CLASS_NAMES` check — CONFIRMED

`gsm2tree_rs.py:101`:
```python
if class_name in _RESERVED_CLASS_NAMES:
```
`_RESERVED_CLASS_NAMES` (`gsm2tree_rs.py:43-50`) contains
`"NodeKind"`, `"Span"`, `"Shared"`, `"CstError"`, `"DropWorklistItem"`,
`"EqWorklistItem"`. The empty string `""` is not a member; the check passes
silently.

### Empty CN is not caught by the cross-rule collision check — CONFIRMED

`gsm2tree_rs.py:141-164`: The cross-rule collision check enters `""` into
`claims` for the node struct, `"Py"` for the handle (`py_handle_name("")`),
and `"Child"` for the child enum (`child_enum_name("")`). With a single
underscore-only rule there is exactly one claimant per key → no collision
detected → no `ValueError` raised.

Two distinct underscore-only rules (e.g., `_` and `__`) would both collapse to
CN `""`, causing a collision on `""`, `"Py"`, and `"Child"`. That would raise a
`ValueError`. A single underscore-only rule silently passes.

### `generate()` would produce syntactically invalid Rust — CONFIRMED

`gsm2tree_rs.py:860`:
```python
lines.append(f"pub struct {class_name} {{")
```
With `class_name = ""` this emits `pub struct  {` (two consecutive spaces),
which is a Rust syntax error. Similarly:
- `pub enum Child {` (valid Rust but semantically wrong name)
- `pub struct Py {` (valid but wrong)
- All `impl {class_name}` blocks emit `impl  {`

### No generation-time diagnostic for a single underscore-only rule — CONFIRMED

The path through `RustCstGenerator.__init__` for a grammar containing exactly
one rule named `_`:
1. `_IDENTIFIER_RE.match("_")` → truthy → passes (line 97)
2. `class_name_for_rule_node("_")` → `""` → not in `_RESERVED_CLASS_NAMES` →
   passes (lines 100-103)
3. Label check loop: no labels → skipped
4. Cross-rule collision check: single rule, no multi-claimant keys → no error

`__init__` completes without error. `generate()` then produces invalid Rust.

### The TODO comment is already present in the file — CONFIRMED

`gsm2tree_rs.py:18-21`:
```python
# TODO(empty-cn-underscore-rule): underscore-only names (_, __, ...) pass this regex but
# snake_to_upper_camel collapses them to CN="" — producing `pub struct  {` (Rust syntax error)
# with no generation-time diagnostic. Fix: reject rule names whose CN is empty (or tighten
# the regex to require at least one [a-z0-9] character).
```
The TODO is already in-tree at the `_IDENTIFIER_RE` definition site.
`RustCstGenerator.__init__` (line 82) is cited as the validation location;
the cross-rule collision check block starts at line 122.

---

## Does the cross-rule collision check from commit 108ee61 already catch this?

No. The commit 108ee61 message says "generation-time cross-rule collision
check." That check (`gsm2tree_rs.py:122-164`) detects when two rules produce
the same derived Rust identifier. A single underscore-only rule maps to a
unique (empty) identifier family; there is no collision. The collision check
would only fire if two or more underscore-only rules exist simultaneously
(since they all collapse to CN `""`). A single `_` rule is not caught.

---

## Does the Python backend (`gsm2tree.py`) have the same hole?

Partially, but it fails earlier with a different error type.

`gsm2tree.py:237` calls `pygen.dataclass(class_name)`, where `pygen.py:54`
calls `ast.parse(f"...\nclass {name}(...):\n    pass\n")`. With `name = ""`
this raises `SyntaxError: invalid syntax` from CPython's parser.

The `SyntaxError` is raised during `CstGenerator.gen_py_module()`, not during
`CstGenerator.__init__()`. The Python backend's `__init__` calls
`model_for_rule` for each rule (line 43-44), which calls
`iir_type_for_rule` (`gsm2tree.py:69-78`), which calls
`iir.Type.make(cname="")` (`typemodel.py:58-71`). `Type.make` has no
non-empty validation on `cname`; it stores the empty string without complaint.
The error surfaces later in `gen_py_module()`.

So the Python backend does not silently produce invalid output — it raises
`SyntaxError` — but the error is not a friendly `ValueError` with a diagnostic
message, and it occurs in the generation method rather than at construction time.

---

## Is the TODO's proposed fix shape feasible?

Both proposed approaches are straightforward:

**Option A — tighten `_IDENTIFIER_RE`**: Change `r"^[_a-z][_a-z0-9]*$"` to
require at least one `[a-z0-9]` character, e.g. `r"^[_a-z][_a-z0-9]*[a-z0-9][_a-z0-9]*$"`.
This would cause `_IDENTIFIER_RE.match("_")` to return `None`, triggering
the `ValueError` at line 97-99. However, this would also reject names like
`_trivia` — wait, `_trivia` has `[a-z]` characters, so it passes any
reasonable tightening. But names like `_` (no non-underscore chars) would
be rejected. The grammar-level identifier regex (`fegen.fltkg:16`) would
also need updating for consistency if underscore-only rule names are to be
fully banned at the grammar level.

**Option B — post-CN check**: After `class_name = self._py_gen.class_name_for_rule_node(rule.name)`
at line 100, add `if not class_name: raise ValueError(...)`. This is a
targeted fix with minimal side-effects.

Both approaches are feasible. Neither has hidden blockers.

---

## Is there a deeper problem the TODO papers over?

Possibly. The grammar-level identifier regex (`fegen.fltkg:16`:
`/[_a-z][_a-z0-9]*/`) admits underscore-only names. If the fix is applied
only in `RustCstGenerator.__init__`, then:
- The grammar can still represent underscore-only rule names.
- The Python backend raises `SyntaxError` in `gen_py_module()` rather than
  an earlier diagnostic.
- The unparser generator (`gsm2unparser.py`) also delegates
  `class_name_for_rule_node` to `naming.snake_to_upper_camel` via
  `CstGenerator` — same hole applies to unparser generation.

The root cause is that the identifier validity constraint (at least one
non-underscore character required for valid code generation) is not enforced
at the grammar/GSM level, only at per-backend generation time. The TODO
acknowledges this is a backend-level fix rather than a grammar-level
constraint. Whether grammar-level validation is appropriate depends on
whether underscore-only rule names are intentional in some usage (e.g.,
the `_trivia` rule exists in the grammar but has a non-underscore suffix).

---

## Blockers the TODO did not mention

1. The fix also applies to `item.label` validation: a label named `_` would
   pass `_IDENTIFIER_RE` and produce `snake_to_upper_camel("_") = ""` →
   `_rust_variant_name("_") = ""` → invalid Rust enum variant `""`. The same
   tighten-or-post-CN approach is needed for labels (lines 107-121 in
   `__init__`).
   
2. `node_kind_member_name` (`gsm2tree.py:96`) calls `.upper()` on the CN:
   `"".upper() == ""` — producing a `NodeKind` variant with an empty name,
   which in Python generates `enum.auto()` assigned to member `""` 
   (a non-identifier attribute name). This is a secondary failure path if the
   primary check is not applied.

3. The grammar-level regex (`fegen.fltkg:16`) does not need to be tightened
   as a prerequisite — the fix can live purely in the Rust generator — but
   consistency with the Python backend and unparser generator suggests a
   grammar-level change or GSM-level validation is the more complete solution.
