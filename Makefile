.PHONY: check lint format-check typecheck test cargo-check cargo-test cargo-clippy \
        build-native build-test-user-ext build-fegen-rust-cst gen-rust-cst fix

# Run all checks: lint, format, type-check, tests, and Rust checks. This is the canonical
# entry point used by CI.
check: lint format-check typecheck test cargo-check cargo-clippy cargo-test

lint:
	uv run --group lint --group test ruff check .

format-check:
	uv run --group lint ruff format --check .

fix:
	uv run --group lint ruff check --fix .
	uv run --group lint ruff format .

typecheck:
	uv run --group lint --group test pyright

test:
	uv run --group lint --group test pytest

cargo-check:
	cargo check

cargo-test:
	cargo test

cargo-clippy:
	cargo clippy -- -D warnings

# ── FLTK-internal Rust artifact targets ──────────────────────────────────────
# These build FLTK's own test/dogfooding Rust artifacts.
# They are NOT the user build recipe; see docs/ for the user build guide.

# Build the fltk._native extension (compiles all committed src/*.rs).
build-native:
	uv run --group dev maturin develop

# Build FLTK's committed standalone non-FLTK fixture extension (separate cdylib crate).
# Produces the importable module 'phase4_roundtrip_cst' used by Tier-2 tests.
build-test-user-ext:
	cd tests/rust_cst_fixture && uv run --group dev maturin develop

# Build FLTK's fegen Rust CST extension (separate cdylib crate).
# Produces the importable module 'fegen_rust_cst' used by parse_grammar(rust_fegen_cst_module=...)
# and the AC8 Tier-2 test (real Cst2Gsm on Rust fegen backend).
build-fegen-rust-cst:
	cd tests/rust_cst_fegen && uv run --group dev maturin develop

# Emit Rust CST source from a grammar (no compilation).
# Usage: make gen-rust-cst GRAMMAR=path/to/grammar.fltkg RS_OUT=path/to/output.rs
gen-rust-cst:
	uv run python -m fltk.fegen.genparser gen-rust-cst $(GRAMMAR) $(RS_OUT)
