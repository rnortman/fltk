# document-scope-boundary — user decision (verbatim)

Captured by the orchestrator as a verbatim user directive for the eventual fast-track implementer.
This item is a fast-track (no design cycle): implement from this directive + the `document-scope-boundary`
entry in `recommended-actions.md`, then full pre-pass + deep review, then squash.

## User's words (verbatim, 2026-06-14)

> OK, standardize all versions on 0.2.0. And consumers can pin on whatever works for them, we do not
> express a preference.

## Verified current version state (live, at time of decision)

| Artifact | File | Current | Target |
|---|---|---|---|
| `fltk` (Python wheel) | `pyproject.toml` | 0.1.1 | **0.2.0** |
| `fltk-native` (root Rust extension crate) | `Cargo.toml` | 0.1.0 | **0.2.0** |
| `fltk-cst-core` (runtime crate) | `crates/fltk-cst-core/Cargo.toml` | 0.2.0 | 0.2.0 (no change) |
| `fltk-parser-core` (runtime crate) | `crates/fltk-parser-core/Cargo.toml` | 0.2.0 | 0.2.0 (no change) |

(Internal/build crates `fegen-rust-cst` and `fltk-cst-spike` are out of scope — not part of the three
runtime/shipping artifacts the decision concerns. Implementer to confirm scope at implementation time.)

## Consumer-guide pin

- `docs/rust-cst-extension-guide.md:59` currently leads with `fltk-cst-core = { version = "0.2", ... }`,
  which does NOT resolve (no crates.io release). Working git/path pins sit commented-out just below.
- Per the directive: express **no** preferred pin method. Present the working pin options (git / path / Bazel)
  neutrally and remove/demote the non-resolving crates.io-style `version = "0.2"` example so the guide
  contains no broken example.

## Out of scope (now obsolete per prior analysis)

The original item also proposed documenting Rust scope boundaries (no unparser; regex subset permanent;
INLINE unsupported). Those are largely obsolete: regex is owned by `regex-portability-lint`; the no-unparser
boundary disappears when the Rust unparser is built; INLINE is unsupported on BOTH backends (not a Rust scope
cut). The live, actionable remainder is only the version reconciliation + consumer-guide pin fix above.
