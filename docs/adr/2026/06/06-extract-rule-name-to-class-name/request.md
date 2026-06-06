# Request: extract-rule-name-to-class-name

Style: concise, precise, no padding, no preamble. Audience: smart LLM/human.

**Type of work:** pure refactor (de-duplicate + canonicalize); small.

**Background.** The snake_case→CamelCase name transform is reimplemented in four places:
1. `fltk/fegen/gsm2tree.py:46-47` — `CstGenerator.class_name_for_rule_node`: `"".join(part.capitalize() for part in rule_name.lower().split("_"))`
2. `fltk/unparse/gsm2unparser.py:638-639` — `UnparserGenerator.class_name_for_rule_node`: identical
3. `fltk/unparse/gsm2unparser.py:1888` — inline list-comp: identical expression
4. `fltk/fegen/gsm2tree_rs.py:25-27` — `_rust_variant_name`: `"".join(part.capitalize() for part in label.split("_"))` — **omits `.lower()`**

Copies 1–3 are byte-identical; copy 4 diverges (no `.lower()`), so on uppercase input it produces a different result. Today all inputs are lowercase snake_case (grammar identifiers), so the divergence is latent — but it is live drift, and a single behavior change (digit handling, consecutive underscores) must currently be made in four spots.

**Fix shape (chosen).** Extract one shared helper into a NEW module `fltk/fegen/naming.py` and route all four sites through it. Canonicalize on the **`.lower()`-applied** behavior (copies 1–3) as the single definition — i.e. copy 4 adopts `.lower()`. Document the canonical edge-case behavior in the helper docstring (consecutive/leading/trailing underscores collapse; `capitalize()` per segment).

**Load-bearing constraints (dependency direction).**
- Put the helper in `fltk/fegen/naming.py` (a leaf with no FLTK imports), NOT in `gsm2tree.py`. Rationale: `fltk/unparse/gsm2unparser.py` must not import `fltk.fegen.gsm2tree` (cross-package coupling / would risk import cycles). `gsm2tree.py` and `gsm2tree_rs.py` already share a package and may import `naming` freely; `gsm2tree_rs.py` already imports from `gsm2tree`.
- Behavior on the actual (lowercase snake_case) inputs must be unchanged — this is a no-observable-change refactor for all current call sites. The only behavioral *unification* is copy 4 gaining `.lower()`, which is inert on current inputs.
- Generated output (class names, Rust variant names) must be byte-identical before/after for the in-tree grammars. Regenerate and confirm no diff.

**Non-goals.** No change to the transform's behavior on real inputs. No touching unrelated parts of the three files. Do not merge `class_name_for_rule_node` methods away if they carry other responsibilities — just delegate their body to the helper.

**Verification.** All four sites call the helper; `naming.py` has unit tests covering the documented edge cases (consecutive `__`, leading/trailing `_`, digits, and that `.lower()` is applied); regenerate in-tree CST/unparser/Rust artifacts and confirm zero diff; `uv run pytest && uv run ruff check . && uv run pyright`. `TODO.md` entry and the `TODO(extract-rule-name-to-class-name)` comment (`gsm2tree_rs.py:18-22`) removed. Good TDD candidate — write `naming.py` tests first.

**Exploration:** `exploration.md` in this dir (note: it corrects the TODO's path — the unparser file is `fltk/unparse/gsm2unparser.py`, not `fltk/fegen/`).
