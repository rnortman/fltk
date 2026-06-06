# Design: extract-rule-name-to-class-name

Style note (applies to this doc): concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

## Root cause / context

The snake_case→CamelCase transform `"".join(part.capitalize() for part in <name>.lower().split("_"))` is reimplemented in four places. Verified against source:

1. `fltk/fegen/gsm2tree.py:46-47` — `CstGenerator.class_name_for_rule_node`.
2. `fltk/unparse/gsm2unparser.py:638-639` — `UnparserGenerator.class_name_for_rule_node` (byte-identical to #1).
3. `fltk/unparse/gsm2unparser.py:1888` — module-level inline list-comp building CST import names (byte-identical expression).
4. `fltk/fegen/gsm2tree_rs.py:25-27` — `_rust_variant_name(label)`: `"".join(part.capitalize() for part in label.split("_"))` — **omits `.lower()`**.

The generated CST node classes, parsers, and Rust variant names are public API for out-of-tree consumers (CLAUDE.md). This transform decides those public names, so its definition must be single-sourced and its behavior stable.

Copies 1–3 are identical. Copy 4 diverges: on uppercase input it preserves mid-segment case (`"MixedLabel"` → copy1-3 `"Mixedlabel"`, copy4 `"MixedLabel"`). Grammar identifiers are lowercase snake_case (enforced by `_IDENTIFIER_RE = ^[_a-z][_a-z0-9]*$` at `gsm2tree_rs.py:17`, matching `fegen.fltkg`), so the divergence is latent today. It is still live drift: any future behavior change (digit handling, underscore collapsing) must be made in four spots, and copies could silently diverge further.

A `TODO(extract-rule-name-to-class-name)` already marks the work at `gsm2tree_rs.py:18-22` (its cited path `fltk/fegen/gsm2unparser.py` is wrong; the file is `fltk/unparse/gsm2unparser.py` — line numbers correct).

## Proposed approach

Pure refactor. No behavior change on real (lowercase snake_case) inputs. Generated artifacts must be byte-identical before/after.

### New module `fltk/fegen/naming.py`

A leaf module with **no FLTK imports** (and no third-party imports). One public function:

```
def snake_to_upper_camel(name: str) -> str
```

Body is the canonical transform — the `.lower()`-applied form (copies 1–3):
`"".join(part.capitalize() for part in name.lower().split("_"))`.

Docstring documents the canonical edge-case contract (see below). Name chosen to describe the transform, not a call-site role, since it serves both class names and Rust variant names.

### Why a new module, not `gsm2tree.py`

Dependency direction (load-bearing, from request):
- `fltk/unparse/gsm2unparser.py` must **not** import `fltk.fegen.gsm2tree` — that adds a new `fltk.unparse → fltk.fegen` cross-package edge through a heavy module and risks import cycles.
- `fltk/fegen/naming.py` is a leaf in the same package as `gsm2tree.py`/`gsm2tree_rs.py`. All three (and `gsm2unparser.py`) import it freely. `gsm2tree_rs.py` already imports from `gsm2tree`, so #4 routing through `naming` adds at most one trivial leaf import.

### Call-site changes

- `gsm2tree.py:46-47`: `class_name_for_rule_node` body delegates to `naming.snake_to_upper_camel(rule_name)`. Method kept (preserves the public/internal method surface; request: do not merge methods away).
- `gsm2unparser.py:638-639`: `class_name_for_rule_node` body delegates likewise. Method kept.
- `gsm2unparser.py:1888`: inline list-comp becomes `[naming.snake_to_upper_camel(rule_name) for rule_name in rule_names]`.
- `gsm2tree_rs.py:25-27`: `_rust_variant_name` body delegates to `naming.snake_to_upper_camel(label)`. **This is the only behavioral unification** — copy 4 gains `.lower()`, inert on current inputs (all labels are lowercase snake_case). Function kept (its docstring/name describe the Rust-variant role).
- Add `from fltk.fegen import naming` to `gsm2tree.py`, `gsm2tree_rs.py`, and `gsm2unparser.py` (import style consistent with each file's existing imports).

### TODO removal

Delete the `TODO(extract-rule-name-to-class-name)` comment block at `gsm2tree_rs.py:18-22` and the `TODO.md` entry at `TODO.md:19`.

## Canonical edge-case contract (documented in docstring)

For inputs `split("_")` produces empty segments; `capitalize()` of `""` is `""`, and `capitalize()` lowercases all but the first char of each segment:

- Consecutive underscores collapse: `"a__b"` → `"AB"`.
- Leading underscore collapses: `"_foo_bar"` → `"FooBar"`.
- Trailing underscore collapses: `"foo_"` → `"Foo"`.
- Digits mid-segment unaffected: `"rule1_test"` → `"Rule1Test"`; `"a1b2c3"` → `"A1b2c3"`.
- Digit-leading segment unchanged by `capitalize()`: `"1starts"` → `"1starts"` (not a valid grammar identifier; documented, not relied upon).
- `.lower()` applied: `"MixedLabel"` → `"Mixedlabel"`.

This is the existing copies 1–3 behavior; documenting it pins the contract, it is not a change.

## Edge cases / failure modes

- **Copy 4 divergence on uppercase:** unified to the canonical (`.lower()`) form. Current inputs are lowercase-only, so generated output is unchanged. Risk only if some caller relied on copy 4's case preservation — none does (only label inputs, all lowercase).
- **Import cycle:** avoided by `naming.py` being a leaf with zero FLTK imports.
- **Generated-output drift:** caught by the regenerate-and-diff verification gate; any nonzero diff fails the change.
- **Empty string input:** `snake_to_upper_camel("")` → `""`. Not produced by valid grammars; covered by a test to pin behavior.

## Test plan

After this change the following tests exist:

- `tests/` unit tests for `fltk/fegen/naming.py` (TDD: write first, expect fail until module exists), covering the documented contract:
  - basic: `"no_ws"` → `"NoWs"`, `"foo_bar_baz"` → `"FooBarBaz"`, single segment `"foo"` → `"Foo"`.
  - consecutive `__`, leading `_`, trailing `_` collapse cases.
  - digit cases: mid-segment and digit-leading segment.
  - `.lower()` applied: mixed-case input lowercased.
  - empty string → empty string.
- Existing generator/parser/unparser test suite continues to pass unchanged (`uv run pytest`) — proves no behavioral regression at call sites.
- Manual/CI verification gate (not a stored test): regenerate in-tree CST, unparser, and Rust artifacts; `git diff` shows zero change. Then `uv run ruff check . && uv run pyright`.

## Open questions

None. Request fully specifies module location, canonical behavior, method-retention, and verification. The only judgment call (which copy is canonical) is resolved by the request: canonicalize on the `.lower()` form.
