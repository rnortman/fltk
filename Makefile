.PHONY: check lint format-check typecheck test cargo-check cargo-test cargo-clippy \
        cargo-test-no-python cargo-clippy-no-python check-no-pyo3 \
        build-native build-test-user-ext build-fegen-rust-cst build-rust-parser-fixture gen-rust-cst fix gencode

# Run all checks: lint, format, type-check, tests, and Rust checks. This is the canonical
# entry point used by CI. On success prints one line; on failure prints the failing step name
# and its full output, then exits non-zero. Individual sub-targets are unchanged and still
# stream output when invoked directly.
check:
	@steps="lint format-check typecheck test cargo-check cargo-clippy cargo-test cargo-test-no-python cargo-clippy-no-python check-no-pyo3"; \
	failed=0; \
	for step in $$steps; do \
	    tmpfile=$$(mktemp); \
	    if ! $(MAKE) $$step >"$$tmpfile" 2>&1; then \
	        echo "FAILED: $$step"; \
	        cat "$$tmpfile"; \
	        rm -f "$$tmpfile"; \
	        exit 1; \
	    fi; \
	    rm -f "$$tmpfile"; \
	done; \
	echo "check: all steps passed (lint format-check typecheck test cargo-check cargo-clippy cargo-test cargo-test-no-python cargo-clippy-no-python check-no-pyo3)"

lint:
	uv run --group lint --group test ruff check -q .

format-check:
	uv run --group lint ruff format --check -q .

fix:
	uv run --group lint ruff check --fix .
	uv run --group lint ruff format .

typecheck:
	uv run --group lint --group test pyright

test:
	uv run --group lint --group test pytest -q

# cargo-check: fast compile for the workspace. Test-crate per-feature checks are omitted
# here because cargo-clippy (a strict superset of cargo-check) already covers them at the
# same feature sets; running both in make check would double-compile each fixture crate.
cargo-check:
	cargo check -q

cargo-test:
	cargo test -q

# cargo-clippy covers test crates at their python-on feature set (the only non-default
# feature that adds code; default features for rust_cst_fegen are already python-on).
cargo-clippy:
	cargo clippy -q -- -D warnings
	cargo clippy -q --manifest-path tests/rust_cst_fegen/Cargo.toml -- -D warnings
	cargo clippy -q --manifest-path tests/rust_parser_fixture/Cargo.toml --features python -- -D warnings

# python-off lane: feature isolation requires -p selection (workspace unification would
# re-enable pyo3 via fltk-native's dependency).
cargo-test-no-python:
	cargo test -q -p fltk-cst-core --no-default-features
	cargo test -q -p fltk-cst-spike
	cargo test -q -p fltk-parser-core
	cargo test -q --manifest-path tests/rust_parser_fixture/Cargo.toml
	cargo test -q --manifest-path tests/rust_cst_fegen/Cargo.toml --no-default-features

cargo-clippy-no-python:
	cargo clippy -q -p fltk-cst-core --no-default-features -- -D warnings
	cargo clippy -q -p fltk-cst-spike -- -D warnings
	cargo clippy -q -p fltk-cst-spike --features python -- -D warnings
	cargo clippy -q -p fltk-parser-core -- -D warnings
	cargo clippy -q --manifest-path tests/rust_parser_fixture/Cargo.toml -- -D warnings
	cargo clippy -q --manifest-path tests/rust_cst_fegen/Cargo.toml --no-default-features -- -D warnings

# Mechanical check: verify pyo3 is absent from the python-off dependency graphs.
# Uses a positive control (fltk-cst-core present) before the negative assertion
# to prevent false passes when cargo tree fails silently.
check-no-pyo3:
	@set -e; \
	out="$$(cargo tree -p fltk-cst-spike --edges normal,build)"; \
	echo "$$out" | grep -q fltk-cst-core || { echo "FAIL: check-no-pyo3 broken: cargo tree output lacks fltk-cst-core"; exit 1; }; \
	! echo "$$out" | grep -q pyo3 || { echo "FAIL: pyo3 present in fltk-cst-spike python-off dependency graph"; exit 1; }; \
	core="$$(cargo tree -p fltk-cst-core --no-default-features --edges normal,build)"; \
	echo "$$core" | grep -q fltk-cst-core || { echo "FAIL: check-no-pyo3 broken: cargo tree output lacks fltk-cst-core"; exit 1; }; \
	! echo "$$core" | grep -q pyo3 || { echo "FAIL: pyo3 present in fltk-cst-core --no-default-features graph"; exit 1; }; \
	parser="$$(cargo tree -p fltk-parser-core --edges normal,build)"; \
	echo "$$parser" | grep -q fltk-cst-core || { echo "FAIL: check-no-pyo3 broken: cargo tree output lacks fltk-cst-core"; exit 1; }; \
	! echo "$$parser" | grep -q pyo3 || { echo "FAIL: pyo3 present in fltk-parser-core dependency graph"; exit 1; }; \
	echo "check-no-pyo3: pyo3 absent from python-off graphs"

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

# Build the fixture Rust parser extension (separate cdylib crate).
# Produces the importable module 'rust_parser_fixture' used by parity tests.
build-rust-parser-fixture:
	cd tests/rust_parser_fixture && uv run --group dev maturin develop --features extension-module

# Emit Rust CST source from a grammar (no compilation).
# Usage: make gen-rust-cst GRAMMAR=path/to/grammar.fltkg RS_OUT=path/to/output.rs
gen-rust-cst:
	uv run python -m fltk.fegen.genparser gen-rust-cst $(GRAMMAR) $(RS_OUT)

# Emit Rust parser source from a grammar (no compilation).
# Usage: make gen-rust-parser GRAMMAR=path/to/grammar.fltkg RS_OUT=path/to/output.rs
gen-rust-parser:
	uv run python -m fltk.fegen.genparser gen-rust-parser $(GRAMMAR) $(RS_OUT)

# Regenerate the parser for the fegen grammar into the rust_cst_fegen test crate.
build-fegen-rust-parser:
	uv run python -m fltk.fegen.genparser gen-rust-parser \
		fltk/fegen/fegen.fltkg tests/rust_cst_fegen/src/parser.rs

# Run native (no-Python) Rust parser tests for the fegen grammar.
test-native-parser:
	cd tests/rust_cst_fegen && cargo test --no-default-features

# Run native Rust parser tests for the fixture grammar.
test-rust-parser-fixture:
	cd tests/rust_parser_fixture && cargo test

# Regenerate ALL generated code from their source grammars, then normalize formatting.
# Covers:
#   - Python CST/parser/protocol for fltk, fegen/bootstrap, toy, and unparsefmt grammars
#   - Rust CST source for cst_generated.rs (PoC grammar), cst_fegen.rs, and fixture crates
# After running, `git diff --stat` reveals any drift between committed generated files and
# what the generators actually produce (cheat-detection: committed hand-patches show as diffs).
gencode:
	# Python: fegen grammar → fltk_cst.py, fltk_cst_protocol.py, fltk_parser.py, fltk_trivia_parser.py
	# (fltk.fltkg is intentionally broken; fltk_cst.py is generated from fegen.fltkg)
	uv run python -m fltk.fegen.genparser generate \
		fltk/fegen/fegen.fltkg fltk fltk.fegen.fltk_cst \
		--output-dir fltk/fegen
	# Python: bootstrap grammar → bootstrap_cst.py, bootstrap_cst_protocol.py, bootstrap_parser.py, bootstrap_trivia_parser.py
	uv run python -m fltk.fegen.genparser generate \
		fltk/fegen/bootstrap.fltkg bootstrap fltk.fegen.bootstrap_cst \
		--output-dir fltk/fegen
	# Python: toy grammar (toy_cst.py, toy_cst_protocol.py, toy_parser.py, toy_trivia_parser.py)
	uv run python -m fltk.fegen.genparser generate \
		fltk/unparse/toy.fltkg toy fltk.unparse.toy_cst \
		--output-dir fltk/unparse
	# Python: unparsefmt grammar (unparsefmt_cst.py, unparsefmt_cst_protocol.py, unparsefmt_parser.py, unparsefmt_trivia_parser.py)
	uv run python -m fltk.fegen.genparser generate \
		fltk/unparse/unparsefmt.fltkg unparsefmt fltk.unparse.unparsefmt_cst \
		--output-dir fltk/unparse
	# Rust: src/cst_generated.rs (PoC grammar — fltk/fegen/test_data/poc_grammar.fltkg)
	uv run python -m fltk.fegen.genparser gen-rust-cst \
		fltk/fegen/test_data/poc_grammar.fltkg src/cst_generated.rs
	# Rust: src/cst_fegen.rs (fegen.fltkg) + fltk/_native/fegen_cst.pyi stub
	uv run python -m fltk.fegen.genparser gen-rust-cst \
		fltk/fegen/fegen.fltkg src/cst_fegen.rs \
		--protocol-module fltk.fegen.fltk_cst_protocol \
		--pyi-output fltk/_native/fegen_cst.pyi
	# Rust: tests/rust_cst_fixture/src/cst.rs (phase4_roundtrip.fltkg)
	$(MAKE) gen-rust-cst GRAMMAR=fltk/fegen/test_data/phase4_roundtrip.fltkg RS_OUT=tests/rust_cst_fixture/src/cst.rs
	# Rust: tests/rust_cst_fegen/src/cst.rs (fegen.fltkg) — must match src/cst_fegen.rs;
	# regenerated here so staleness is visible to cargo check in the rust_cst_fegen workspace.
	$(MAKE) gen-rust-cst GRAMMAR=fltk/fegen/fegen.fltkg RS_OUT=tests/rust_cst_fegen/src/cst.rs
	# Rust: tests/rust_cst_fegen/src/parser.rs (fegen.fltkg) — generated Rust parser.
	$(MAKE) build-fegen-rust-parser
	# Rust: tests/rust_parser_fixture/src/cst.rs and parser.rs (rust_parser_fixture.fltkg)
	$(MAKE) gen-rust-cst GRAMMAR=fltk/fegen/test_data/rust_parser_fixture.fltkg RS_OUT=tests/rust_parser_fixture/src/cst.rs
	$(MAKE) gen-rust-parser GRAMMAR=fltk/fegen/test_data/rust_parser_fixture.fltkg RS_OUT=tests/rust_parser_fixture/src/parser.rs
	# Rust: crates/fltk-cst-spike/src/cst.rs — same grammar as cst_generated.rs; cp makes identity explicit
	cp src/cst_generated.rs crates/fltk-cst-spike/src/cst.rs
	# Normalize formatting. Order matters:
	# 1. ruff check --fix: upgrades typing.Union[X,Y] → X|Y and similar, so ruff format can then
	#    wrap the resulting X|Y chains correctly.  Exit code ignored — residuals handled by step 2.
	# 2. ruff format: applies canonical line-length formatting.
	# 3. ruff check --fix again: cleans up any issues exposed after formatting.
	# make check (the gate) is the definitive clean check; intermediate exits are informational.
	uv run --group lint ruff check --fix . || true
	uv run --group lint ruff format .
	uv run --group lint ruff check --fix . || true
