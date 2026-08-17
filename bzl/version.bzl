"""The version every Rust target in this repo reports, in one place.

There are no Cargo manifests, so a `rust_library` / `rust_binary` `version` attribute is where the
number lives — and rules_rust compiles it in as `CARGO_PKG_VERSION`, which is what
`clap`'s `#[command(version)]` prints from a formatter binary built on `fltk-fmt-cli`.

One constant rather than a literal per target because a forgotten bump is the defect that made
`v0.5.0` broken: a number spelled once cannot be bumped in some targets and not others.
"""

# TODO(version-bump-0-6-0): still 0.4.0 while v0.5.0 is tagged.
FLTK_CRATE_VERSION = "0.4.0"
