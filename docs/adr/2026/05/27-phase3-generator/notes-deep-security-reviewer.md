# Security review — Phase 3 Rust CST generator

Commit reviewed: af7dc6e (base 6f82c48)
Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Scope: `fltk/fegen/gsm2tree_rs.py`, `src/lib.rs`, generated `src/cst_generated.rs` / `src/cst_fegen.rs`, tests.

---

## security-1 — Unescaped grammar names interpolated into generated Rust source (code injection into a compiled artifact)

File: `fltk/fegen/gsm2tree_rs.py` — `_node_block` (137, 147), `_per_label_methods` (256, 266, 280, 286, 299, 306, 320, 329, 336, 350), `_label_enum_block` (98, 102, 115), `_hash_method` (380), `_repr_method` (391), `_register_classes_fn` (410-411); name transforms `_rust_variant_name` (15-17) / `_python_label_name` (20-22).

The issue: `class_name` (derived from `rule.name` via `CstGenerator.class_name_for_rule_node`) and `label` (from `item.label`) are interpolated into generated Rust via f-strings with no validation and no escaping. They land in two distinct syntactic positions:
- Rust **identifiers**: struct/enum names (`pub struct {class_name}`), enum variants (`{rust_variant}`), method names (`fn append_{label}`, `fn child_{label}`, ...).
- Rust **string literals**: error messages (`"Expected one {label} child but have {count}"`), downcast context (`"{class_name}.children_{label}: ..."`), `__repr__` (`"{class_name}(span=...)"`), `__hash__` (`"unhashable type: '{class_name}'"`).

Trust boundary / data flow: `RustCstGenerator(grammar)` is a public API taking a `gsm.Grammar`. `gsm.Rule.name` (`gsm.py:27`) and `gsm.Item.label` (`gsm.py:103`) are plain `str` with no validation at the dataclass or generator layer. The generator performs zero validation of either before emitting. Two entry paths reach these fields:
- Parsed `.fltkg` path (`fltk_parser` + `fltk2gsm`): identifiers are constrained by `identifier := name:/[_a-z][_a-z0-9]*/` (`fegen.fltkg:16`). Safe — alphanumeric + underscore only.
- Programmatic `gsm.Grammar` construction: no constraint. `_make_poc_grammar` in `tests/test_gsm2tree_rs.py` already builds grammars this way. Any caller (or future tooling that ingests grammar names from elsewhere — e.g. a grammar-composition feature, an externally-supplied `.fltkg` from a different parser, a name-mangling pass) can place arbitrary strings into `rule.name` / `item.label`.

Consequence: a `rule.name` or `item.label` containing Rust syntax produces attacker-shaped Rust source that maturin/cargo then compiles. The string-literal positions are the sharper vector: a label or class name containing `"` plus `);` closes the literal and statement, and the rest of the value becomes live Rust code in a `#[pymethods]` impl — e.g. a label `x"); std::process::Command::new("sh")...; //` yields arbitrary code in the generated `.rs`, which executes with developer/CI privileges at `maturin develop` / `cargo build` time (build-time RCE, supply-chain). Even without reaching RCE, an unbalanced quote/brace makes generation emit uncompilable Rust (build DoS). `class_name_for_rule_node` lowercases and capitalizes but does not strip non-identifier characters, so `"` `{` `;` `\n` all survive into output. The asset is the build host / CI pipeline and the integrity of the compiled extension shipped to downstream users.

Whether this is exploitable today hinges entirely on whether any non-`.fltkg`-parser path can supply grammar names. Today the only production producer is the regex-constrained parser, so it is latent rather than live. But the design (`design.md:40-52`) advertises `RustCstGenerator.__init__(self, grammar: gsm.Grammar)` as the public contract — accepting any `gsm.Grammar` — and a generator that emits source code must not assume its model came from the one trusted parser.

Suggested fix: validate names at the generator trust boundary. In `RustCstGenerator.__init__` (or at the top of `generate()`), assert every `rule.name` and every `item.label` across all rules/items matches `^[_a-z][_a-z0-9]*$` (the same invariant the grammar parser enforces), raising `ValueError` otherwise. This is cheap, makes the trusted-input assumption explicit and enforced rather than ambient, and converts a potential build-time RCE into a clear error. The same regex already governs identifiers in `fegen.fltkg:16`, so it rejects nothing the legitimate pipeline produces.

---

## security-2 — `sys.modules` manual insertion: no untrusted input, noted for completeness

File: `src/lib.rs:42-44`.

`sys.modules["fltk._native.fegen_cst"]` is set to the freshly created submodule during module init. The key string is a compile-time constant; no untrusted input reaches it. No injection or hijack vector. No finding — recorded only to show the manual `sys.modules` write was considered.

---

## Other vectors checked — clear

- Secrets in diff: none. No creds/keys/tokens added.
- Path traversal / SSRF / deserialization / open redirect / CSRF: not applicable — no filesystem path, URL, network, or HTTP-handler code introduced. Generator only builds strings; committed `.rs` files are compiled, not loaded as data.
- Crypto / RNG / timing: none introduced.
- `__eq__` (gsm2tree_rs.py:360) / `__hash__` (377): `__hash__` deliberately raises (unhashable); `__eq__` does structural compare. No security-relevant secret comparison.
- Generated `src/cst_generated.rs` / `src/cst_fegen.rs`: produced solely from the regex-constrained `fegen.fltkg` and the hand-built PoC grammar; spot-checked string literals contain only identifier-safe content. No injected content in the committed artifacts as-is.
