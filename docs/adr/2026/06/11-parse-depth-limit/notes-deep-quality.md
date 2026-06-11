Style: concise, precise, complete, unambiguous. No padding, no preamble.

## quality-1

**File:line**: `crates/fltk-parser-core/src/memo.rs:86`

**Issue**: `PackratState::max_depth` is `pub` (direct field write), while `depth` and `depth_exceeded` are private (accessor-only). This is an asymmetric, leaky abstraction. The two private fields exist precisely because unmediated mutation would break invariants — the doc comment even says "managed by `apply` guard". `max_depth` has the same characteristic: mutating it mid-parse (after the first `apply` has incremented `depth`) produces undefined-but-silent semantics. The design chose `pub max_depth` explicitly, but `set_max_depth` already exists and provides the same write access with a place to attach the "call before parsing" contract.

**Consequence**: Downstream Rust callers seeing three fields — two private, one public — have no obvious cue that `max_depth` must not be touched mid-parse. As more `PackratState` accessors are added over time, the "some fields pub, some private, no method for the public one" pattern spreads the inconsistency. If `max_depth` is ever joined by `min_depth` or a flags field, they will face the same pressure to be `pub` for symmetry, eroding the accessor contract further.

**Fix**: Make `max_depth` private; `set_max_depth` and `max_depth()` already provide full read/write access with doc-contract. Remove the `pub` keyword from the field declaration; `set_max_depth` on the generated `Parser` and `PackratState::max_depth = …` in `DepthParser::new` in `memo_toy.rs` would both need to switch to the method form. The generated `Parser::set_max_depth` already calls `self.packrat.max_depth = max_depth` — replace that with `self.packrat.set_max_depth(max_depth)` once the setter is on `PackratState`.

---

## quality-2

**File:line**: `crates/fltk-parser-core/tests/memo_toy.rs:236`

**Issue**: The toy-parser test constructs `PackratState::default()` then immediately overwrites `packrat.max_depth` as a public field — the only location in the test that depends on `max_depth` being `pub`. This is a direct consequence of quality-1, but it's also redundant state: `DepthParser::new` could pass `max_depth` to a `PackratState::with_max_depth(n)` constructor, or `PackratState::default()` could accept it. As written, `DepthParser::new` is a two-step init (construct then mutate) where one-step would be unambiguous.

**Consequence**: When/if quality-1 is fixed and `max_depth` goes private, every test site will need a mechanical rewrite. Only one site currently, but toy tests are the model for future third-party integrations of `fltk-parser-core`.

**Fix**: As part of fixing quality-1, add `PackratState::with_max_depth(max_depth: u32) -> Self` (or accept in a named constructor). `DepthParser::new` becomes `PackratState::with_max_depth(max_depth)`. No functional change; removes the two-step init and the pub-field dependency.

---

## quality-3

**File:line**: `fltk/fegen/gsm2parser_rs.py:391`

**Issue**: The generated `Parser::set_max_depth` writes `self.packrat.max_depth` as a direct field access (`pub` field), bypassing any future validation or hook point on `PackratState`. This is a coupling between the generator and the internal layout of `PackratState` that isn't needed: `PackratState` already has `set_max_depth` missing — but when quality-1 is fixed and the field goes private, the generator template breaks at compile time. The generator is the source of truth for what the generated file contains; it should call a method, not poke a field.

**Consequence**: Any refactor of `PackratState`'s storage for `max_depth` requires a coordinated change to the generator template. Because generated files are committed, the mismatch is only caught when the fixture parser is regenerated — not immediately. Propagates: every future generated parser written by this generator will embed the field-access pattern.

**Fix**: After quality-1 is addressed and `PackratState::set_max_depth` exists, update the generator line:
```python
lines.append("    pub fn set_max_depth(&mut self, max_depth: u32) { self.packrat.set_max_depth(max_depth); }")
```
Similarly `max_depth()` getter should delegate to `self.packrat.max_depth()` rather than `self.packrat.max_depth`.
