Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Reviewed commits: 60f5c3f (inc 1), ee4a59b (inc 2), e850f48 (inc 3), bf281fc (inc 4); base 6fd32e7.

## scope-1 — Increment 2 commit hash never recorded in log

**Location:** `docs/adr/.../implementation-log.md`, line 14: "## Increment 2 ... (commit TBD)"

**Expected:** commit hash inserted (actual commit is ee4a59b) when the log-update commit e4391ce was made.

**Actual:** "commit TBD" remains in HEAD. Log for increment 2 body is otherwise accurate; the hash was simply never filled in.

**Consequence:** audit trail is broken; reviewers cannot `git show <hash>` for increment 2 to verify claims.

**Fix:** replace "commit TBD" with "commit ee4a59b" in the log header.

---

## scope-2 — Log sections appear in reverse order (increment 4 before increment 3)

**Location:** `docs/adr/.../implementation-log.md`, lines 32–51: increment 4 section precedes increment 3 section.

**Expected:** sections in commit-chronological order (inc 1 → 2 → 3 → 4).

**Actual:** "Increment 4" section (bf281fc, 16:15) appears before "Increment 3" section (e850f48, 16:02). Git history is correct; only the log text is mis-ordered.

**Consequence:** confusing to read; a reader scanning the log top-to-bottom sees the parse-fix before the children change it depends on.

**Fix:** reorder log sections to match commit chronology.

---

## scope-3 — Increment 3 header/body test-count inconsistency

**Location:** `docs/adr/.../implementation-log.md`, lines 44 and 49.

**Expected:** consistent number. Body at line 49 says "121 targeted tests pass." Header summary at line 44 says "124 targeted tests pass."

**Actual:** mismatch of 3. Cannot determine from the diff which is correct.

**Consequence:** minor — the count is informational, but inconsistency signals the log was written in multiple passes and not reconciled.

**Fix:** verify the actual count against the e850f48 state and align both entries.

---

## scope-4 — tests/rust_cst_fixture/src/cst.rs regenerated from wrong grammar (§2.8, §4 item 5)

**Location:** `tests/rust_cst_fixture/src/cst.rs` at HEAD (f2bf59b).

**Expected (design §2.8):** fixture grammar (`fltk/fegen/test_data/phase4_roundtrip.fltkg`) → `tests/rust_cst_fixture/src/cst.rs`. Grammar has 6 rules: Config, Entry, Operator, Identifier, Literal, Trivia (5 + Trivia). `register_classes` must expose `Config`, `Entry`, `Operator`, `Identifier`, `Literal`.

**Actual:** file has 3 rules: Identifier, Items, Trivia — identical to the PoC grammar (`src/cst_generated.rs`). `register_classes` exposes only those three. `Config`, `Entry`, `Operator`, `Literal` are absent.

**Consequence:** building the fixture (`make build-test-user-ext`) produces a `phase4_roundtrip_cst` module without `Config`/`Entry`/`Operator`. Every test in `tests/test_phase4_rust_fixture.py` (all 71 that were not already skipped for missing build) would fail with `AttributeError: module has no attribute 'Config'`. The test suite does not detect this because the fixture is not rebuilt during a plain `pytest` run — it is skipped via `importorskip` if the previously-built `.so` happens to pre-date this commit. A fresh `make build-test-user-ext && pytest` will fail.

**Not noted in log.**

**Fix:** regenerate `tests/rust_cst_fixture/src/cst.rs` from `fltk/fegen/test_data/phase4_roundtrip.fltkg` (`make gen-rust-cst GRAMMAR=fltk/fegen/test_data/phase4_roundtrip.fltkg RS_OUT=tests/rust_cst_fixture/src/cst.rs`), then `make fix`.

---

## scope-5 — Node structs not moved to fltk-cst-core (design §2.1 / §2.3 / §4 item 1)

**Location:** `crates/fltk-cst-core/src/` — contains only `span.rs` and `lib.rs`. Node structs (`Identifier`, `Items`, etc.) and child enums (`IdentifierChild`, `ItemsChild`, etc.) remain in the cdylib's generated files (`src/cst_generated.rs`, etc.).

**Expected (design §2.1):** "fltk-cst-core rlib crate holding…the generated node structs, and the per-rule child-node enums." §2.3: "the node structs themselves are pyo3-runtime-free (fltk-cst-core, §2.1)." §4 item 1: pure-Rust `#[cfg(test)]` in fltk-cst-core constructs a node subtree, walks it, and compares it without `Python::with_gil`.

**Actual:** node struct fields (`span`, `children`) are not `pub` — only accessible within the cst_generated module. Child enums are in the cdylib. No `#[cfg(test)]` Rust test exists in fltk-cst-core. A downstream rlib depending on `fltk-cst-core` cannot name or construct node types at compile time.

**Design tension noted for context:** §2.8 specifies generated output paths as `src/cst_generated.rs` and `tests/*/src/cst.rs`, not as paths inside `crates/fltk-cst-core/`. Fulfilling both §2.1 and §2.8 simultaneously would require either (a) the generated file living inside fltk-cst-core's source tree, or (b) a build-script `include!()` mechanism. The design does not resolve this contradiction. The implementation chose the §2.8 path (cdylib-resident generated files) without logging the §2.1 deviation.

**Consequence:** the §4 item 1 acceptance test ("pure-Rust node-tree construction without GIL") cannot be written in its design-specified location (fltk-cst-core `#[cfg(test)]`) because the node types are inaccessible across crate boundaries. The downstream "compile-time Rust type access" scenario (a downstream cdylib naming `Box<ConcreteNode>` from fltk-cst-core) is also unimplemented. This is a stated acceptance criterion for the native-state requirement.

**Not noted in log.**

**Suggested resolution:** either (a) move the generated CST files into fltk-cst-core (changing §2.8 paths and generator output), or (b) make node struct fields `pub` and add plain-Rust constructors in the generated modules, note the §2.1 deviation explicitly, and write the §4 item 1 test as a `#[cfg(test)]` in the cdylib crate. Or (c) revise the design to acknowledge the contradiction and adopt (b) as the accepted approach. Whichever path is chosen must be logged.

---

## Items confirmed correct (not findings)

- **§2.1 split crate (non-struct parts):** Cargo workspace, `fltk-cst-core` rlib, `Span`/`SourceText` moved with public Rust constructors and accessors, fixture `Cargo.toml` dependencies with `default-features = false` — all match log and design.
- **§2.2 native span field:** `span: Span` in node structs, `Span::unknown()` default, `extract_span()` helper, getter/setter, `_preamble` changes — all match log and diff. Logged deviations (cross-cdylib isinstance hack, getter loses source) are accurately described.
- **§2.3 native children:** per-node child enums, `Vec<(Option<Label>, Child)>` storage, `append`/`extend`/accessor rewrites, `children` getter rebuilds on demand — all in diff and match log.
- **§2.4 native equality:** `PartialEq` derived on child enums; `self == &*other_node` in `__eq__` (no Python `.eq()` on stored state) — present in diff. Not explicitly logged as a separate section but accurately described as part of §2.3 increment.
- **§2.5 partial (extend_children + gsm2parser):** both `inline_to_parent` sites changed, `extend_children` added to Python and Rust generators, all parser and CST files regenerated — all match log and diff. Individual `append` calls already used the node method (not getter mutation) and were correctly left unchanged.
- **§2.5 remainder deferred:** source-bearing spans not implemented; log correctly attributes this to `backend-with-source-signature` prerequisite.
- **§2.6, §2.7, §2.8 (unstarted):** absent from diff; correctly absent (these are future increments).
