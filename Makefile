.PHONY: check lint format-check typecheck test cargo-check cargo-test cargo-clippy \
        build-native build-test-user-ext build-fegen-rust-cst gen-rust-cst fix gencode

# Run all checks: lint, format, type-check, tests, and Rust checks. This is the canonical
# entry point used by CI. On success prints one line; on failure prints the failing step name
# and its full output, then exits non-zero. Individual sub-targets are unchanged and still
# stream output when invoked directly.
check:
	@steps="lint format-check typecheck test cargo-check cargo-clippy cargo-test"; \
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
	echo "check: all steps passed (lint format-check typecheck test cargo-check cargo-clippy cargo-test)"

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

cargo-check:
	cargo check -q

cargo-test:
	cargo test -q

cargo-clippy:
	cargo clippy -q -- -D warnings

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

# Regenerate ALL generated code from their source grammars, then normalize formatting.
# Covers:
#   - Python CST/parser/protocol for fltk, fegen/bootstrap, toy, and unparsefmt grammars
#   - Rust CST source for cst_generated.rs (PoC grammar), cst_fegen.rs, and fixture crates
# After running, `git diff --stat` reveals any drift between committed generated files and
# what the generators actually produce (cheat-detection: committed hand-patches show as diffs).
# TODO(gencode-poc-fltkg): src/cst_generated.rs is generated from a hand-built PoC grammar
# (_make_poc_grammar in tests/test_gsm2tree_rs.py) — no .fltkg file exists for it.
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
	# Rust: src/cst_generated.rs (PoC grammar — no .fltkg; import helper from tests)
	uv run python -c "\
import sys; sys.path.insert(0, 'tests'); \
from test_gsm2tree_rs import _make_poc_grammar; \
from fltk.fegen.gsm2tree_rs import RustCstGenerator; \
open('src/cst_generated.rs', 'w').write(RustCstGenerator(_make_poc_grammar()).generate())"
	# Rust: src/cst_fegen.rs (fegen.fltkg)
	$(MAKE) gen-rust-cst GRAMMAR=fltk/fegen/fegen.fltkg RS_OUT=src/cst_fegen.rs
	# Rust: tests/rust_cst_fixture/src/cst.rs (phase4_roundtrip.fltkg)
	$(MAKE) gen-rust-cst GRAMMAR=fltk/fegen/test_data/phase4_roundtrip.fltkg RS_OUT=tests/rust_cst_fixture/src/cst.rs
	# Normalize formatting. Order matters:
	# 1. ruff check --fix: upgrades typing.Union[X,Y] → X|Y and similar, so ruff format can then
	#    wrap the resulting X|Y chains correctly.  Exit code ignored — residuals handled by step 2.
	# 2. ruff format: applies canonical line-length formatting.
	# 3. ruff check --fix again: cleans up any issues exposed after formatting.
	# make check (the gate) is the definitive clean check; intermediate exits are informational.
	uv run --group lint ruff check --fix . || true
	uv run --group lint ruff format .
	uv run --group lint ruff check --fix . || true
