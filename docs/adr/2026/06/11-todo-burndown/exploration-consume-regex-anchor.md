# Adversarial validation: TODO(consume-regex-anchor)

Concise. Precise. No fluff. Audience: LLM/human reviewing whether to act on this TODO.

---

## 1. Does `consume_regex` actually use `find_at`?

Yes. `crates/fltk-parser-core/src/terminalsrc.rs:154`:

```rust
let m = regex.find_at(text, byte_pos)?;
```

`regex::Regex::find_at` is `regex 1.12.3`'s public API. Its implementation
(`~/.cargo/registry/src/…/regex-1.12.3/src/regex/string.rs:1110`):

```rust
let input = Input::new(haystack).span(start..haystack.len());
self.meta.search(&input).map(|m| Match::new(haystack, m.start(), m.end()))
```

No `Anchored::Yes` — the search is unanchored. On a non-match at `byte_pos` it
scans forward through the remaining span.

---

## 2. Is the unanchored-scan behavior real?

Yes. `find_at` creates `Input` with `span(byte_pos..text.len())` and no
`anchored(Anchored::Yes)`, so the underlying `regex_automata` meta engine
performs a leftmost search that may return a match starting anywhere in
`[byte_pos, text.len())`. The code at `terminalsrc.rs:155-158` compensates:

```rust
if m.start() != byte_pos {
    return None;
}
```

This correctly rejects a non-start match. However, the scan work was already
done before the rejection.

---

## 3. Is the O(rules × n²) claim accurate?

Conditionally accurate; the bound is real but the coefficient depends on regex
behavior.

- Packrat memoization means each (rule, position) pair is evaluated at most
  once: O(R × N) `consume_regex` calls total across a parse of N codepoints
  with R regex terminals.
- Per failing `find_at` call, the scan work is O(N) in the worst case (e.g.
  pattern `(?s:.)*x` on `"aaa…a"` with no `x`).
- Worst-case total: O(R × N²).

The claim is factually sound. Whether it is practically exploitable depends on
the patterns in actual grammars and the input structure — it requires both many
regex non-matches per position AND patterns that cause the engine to scan far.

---

## 4. "Look-behind context" — what does it actually refer to?

The TODO text and the `terminalsrc.rs:133` doc comment both use "look-behind"
loosely to mean word-boundary assertions (`\b`, `\B`), not true look-behind
(`(?<=…)`). The `regex` crate **does not support look-behind** (it rejects
`(?<=…)` patterns at compile time; `gsm2parser_rs.py:7-8` explicitly states
this in the module docstring). The `terminalsrc.rs:133` comment names the
actual concern: `\b`/`\B` require seeing the character before `byte_pos`, which
is why the full string is passed instead of a slice.

The term "look-behind context" in the TODO is therefore a misnomer; the real
feature being preserved is `\b`/`\B` correct resolution at `byte_pos > 0`.

---

## 5. Is the `\A`-prepending alternative viable?

No. `\A` anchors to byte offset 0 of the haystack, not to the start of the
search span. `regex` crate docs (`lib.rs:872`): "`\A` — only the beginning of
a haystack (even with multi-line mode enabled)." When `find_at` is called with
`byte_pos > 0`, prepending `\A` to the pattern would always fail. This
alternative does not work.

---

## 6. Is `regex_automata` already a transitive dep?

Yes. `cargo metadata` shows `regex-automata 0.4.14` in the dependency graph,
pulled transitively by `regex = "1"` (the `regex` crate's `Cargo.toml` lists
`regex-automata = "0.4.12"` as a direct dep). However, `fltk-parser-core`'s own
`Cargo.toml` lists only `regex = "1"` as a direct dependency — `regex-automata`
is not a direct dep of `fltk-parser-core`. Switching to
`regex_automata::meta::Regex` would require adding `regex-automata` as a direct
dep to `fltk-parser-core/Cargo.toml`.

---

## 7. Is `regex_automata::meta::Regex` + `Input::anchored(Anchored::Yes)` the right fix?

The API exists and is documented to do what the TODO claims.
`regex-automata-0.4.14/src/util/search.rs:251-252`:

> When a search is anchored ([`Anchored::Yes`] or [`Anchored::Pattern`]), a
> match must begin at the start of a search.

And `search.rs:317`: "An anchored search can still match anywhere in the
haystack, it just must begin at the start of the search which is '2' in this
case." The span-with-anchored pattern preserves surrounding-context visibility
(the full haystack is still passed; only the start of the search is constrained)
which is what `\b`/`\B` requires.

The `Input::span(byte_pos..text.len()).anchored(Anchored::Yes)` form would fail
immediately on non-match at `byte_pos`, matching Python `re.match(pos=…)`
semantics exactly.

---

## 8. Impact on generated-code API (the `regex::Regex` type)

`gsm2parser_rs.py:271` emits `use fltk_parser_core::regex::Regex;` into
generated parsers. `gsm2parser_rs.py:307-317` generates a static
`REGEX_CELLS: [OnceLock<Regex>; N]` and a `regex_at(idx) -> &'static Regex`
function. `terminalsrc.rs:148` takes `regex: &Regex`.

If `TerminalSource::consume_regex` is switched to accept
`&regex_automata::meta::Regex`, all generated code that constructs `Regex`
objects and passes them in must also change. This affects the public API of
`fltk-parser-core` (the `consume_regex` signature) and the emitted generated
code from `gsm2parser_rs.py`. The change is contained to `fltk-parser-core` and
the generator, but is not trivial (type of the regex table cells, import paths,
construction call sites).

---

## 9. Deeper structural issue?

The core mismatch is: `regex::Regex::find_at` is designed for forward iteration
("give me the next match from this offset"), while packrat parsing needs
"match exactly at this offset or fail immediately." This is a genuine
interface-impedance mismatch that is not fixable within `regex::Regex`'s public
API. The `regex_automata` path is the correct remedy. There is no within-`regex`
workaround.

---

## Summary verdict

| Claim | Verdict |
|---|---|
| `find_at` is used | **True** (`terminalsrc.rs:154`) |
| `find_at` is unanchored (scans on non-match) | **True** (`regex-1.12.3/src/regex/string.rs:1110`) |
| Match start validation rejects forward matches | **True** (`terminalsrc.rs:155-158`) — but scan cost is already paid |
| O(rules × n²) worst case | **True** (packrat memoization limits calls to O(R×N); each failing call costs O(N)) |
| "Look-behind context" terminology | **Misleading** — no look-behind in `regex`; real concern is `\b`/`\B` at `byte_pos > 0` |
| `regex_automata` already a transitive dep | **True** (via `regex = "1"`) but NOT a direct dep of `fltk-parser-core` |
| `regex_automata` fix is feasible | **True** — API supports `Input::anchored(Anchored::Yes).span(byte_pos..text.len())` with full-string context |
| `\A` prepending alternative | **Does not work** — `\A` anchors to haystack byte 0, not span start |
| Fix requires changing generated-code API | **True** — `Regex` type in `REGEX_CELLS` and `regex_at` must change |
