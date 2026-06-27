# Quality review: rust-fltkfmt increments 4–6

Commit reviewed: `0718645d66cec435752a28094f0cd7631712b058`
Base: `762bbced1f5b44de2ad507db3a18a653c2ca585a`

---

## quality-1 — Binary name `fltkfmt` hardcoded in shared library's temp-file suffix

**File:line**: `crates/fltk-fmt-cli/src/lib.rs:130`

```rust
tmp.push(format!(
    ".{}.fltkfmt.tmp.{}",
    file_name.to_string_lossy(),
    std::process::id()
));
```

**Issue**: `write_atomic` is a private function of `fltk-fmt-cli`, a shared scaffolding crate designed to be a dependency for *any* FLTK grammar formatter binary (design §2.2: "shared, publishable infrastructure that downstream formatter crates depend on"). The temp file suffix `.fltkfmt.tmp.` embeds the name of the first concrete consumer. A second formatter binary built on `fltk-fmt-cli` (say `myfmt`) would create temp files named `.file.fltkfmt.tmp.<pid>` during `--in-place` writes.

**Consequence**: Orphaned temp files from `myfmt` are misattributed to `fltkfmt` in `ls -la` output. Any cleanup script, gitignore pattern, or documentation that filters on `.fltkfmt.tmp.` to identify stale temps will silently miss orphans left by non-`fltkfmt` consumers. If this pattern propagates to a third consumer it compounds: every new formatter binary inherits the wrong brand label on its crash artifacts.

**Fix**: Replace `.fltkfmt.tmp.` with a generic library-level marker such as `.fltk-fmt.tmp.` (matching the crate name `fltk-fmt-cli`). This is a one-character-class change entirely within the private function and has no API impact.

---

## quality-2 — Macro-support re-exports lack `#[doc(hidden)]`

**File:line**: `crates/fltk-fmt-cli/src/lib.rs:20`

```rust
pub use fltk_unparser_core::{resolve_spacing_specs, Renderer, RendererConfig};
```

**Issue**: The comment directly above this line states that `Renderer` and `resolve_spacing_specs` "are used only by the macro expansion" — they are re-exported solely so the `fltk_formatter_main!` macro can reference them via `$crate::` without forcing each consumer to also name `fltk-unparser-core`. This is a standard Rust pattern, but the standard companion is `#[doc(hidden)]` on such re-exports. Without it, `fltk_fmt_cli::Renderer` and `fltk_fmt_cli::resolve_spacing_specs` appear as first-class items in the crate's generated rustdoc, indistinguishable from items that are intentionally part of the public API.

`RendererConfig` is a different case: it appears in the signature of the public `run_main` function and is legitimately part of the crate's public API surface. It should remain an undisguised `pub use`.

**Consequence**: Downstream consumers reading `fltk_fmt_cli`'s docs see `Renderer` and `resolve_spacing_specs` as if they are supported entry points, and may write code that depends on `fltk_fmt_cli::Renderer` rather than `fltk_unparser_core::Renderer`. If the macro is ever reimplemented (e.g., via a trait) and the re-export is removed, those consumers break — a semver-incompatible change for what is effectively an implementation detail. The pattern also propagates: a third-party author of a grammar formatter crate, looking at this crate as a model, may adopt the same undisclosed re-export pattern for their own macro-support items.

**Fix**: Split the `pub use` so `#[doc(hidden)]` covers only the macro-support items:

```rust
pub use fltk_unparser_core::RendererConfig;
#[doc(hidden)]
pub use fltk_unparser_core::{resolve_spacing_specs, Renderer};
```

The items remain accessible at `$crate::resolve_spacing_specs` / `$crate::Renderer` in macro expansions (Rust `#[doc(hidden)]` does not affect item visibility), but they are excluded from rustdoc output and implicitly marked as non-API surface.
