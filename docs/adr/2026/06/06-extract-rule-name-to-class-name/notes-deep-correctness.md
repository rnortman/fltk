# Deep correctness review — extract-rule-name-to-class-name

Style note (applies to this doc): concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Reviewed: 3055a3e..8ddd61f (3 commits). Scope: logic/control-flow/data-flow per mandate.

No findings.

Verification performed:
- `fltk/fegen/naming.py:22` body is byte-identical to the pre-change expression in copies 1–3 (`gsm2tree.py:47`, `gsm2unparser.py:635`, `gsm2unparser.py:1827`); all three call sites now delegate with the same argument. Zero behavior change there.
- Copy 4 (`gsm2tree_rs.py:20` `_rust_variant_name`) gains `.lower()`. Confirmed inert: its only inputs are labels from `model.labels` keys, emitted at `gsm2tree_rs.py:325,338,760`; grammar-parsed labels match `_IDENTIFIER_RE = ^[_a-z][_a-z0-9]*$` and `RustCstGenerator.__init__` re-validates top-level item labels before emission. (Nested sub-expression labels skip that `__init__` re-validation, but that gap is pre-existing, not introduced by this diff, and grammar parsing enforces lowercase anyway.)
- `git grep capitalize` shows no remaining inline copies of the transform outside `naming.py`/tests.
- Docstring edge-case contract matches actual `str.capitalize`/`str.lower`/`split("_")` semantics for every documented case ("a__b"→"AB", "_foo_bar"→"FooBar", "foo_"→"Foo", "a1b2c3"→"A1b2c3", "1starts"→"1starts", "MixedLabel"→"Mixedlabel", ""→"").
- `uv run pytest tests/test_naming.py`: 11 passed.
- Public-API surface (generated class/variant names) unchanged for all valid (lowercase snake_case) inputs — consistent with the out-of-tree-consumer constraint in CLAUDE.md.
