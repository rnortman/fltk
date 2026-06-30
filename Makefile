.PHONY: check check-ci check-common lint format-check typecheck test cargo-check cargo-test cargo-clippy \
        cargo-test-no-python cargo-clippy-no-python check-no-pyo3 cargo-deny \
        cargo-test-python-features \
        build-native build-test-user-ext build-fegen-rust-cst build-rust-parser-fixture \
        build-test-fixtures gen-rust-cst fix gencode

# ══════════════════════════════════════════════════════════════════════════════
# CHECK TARGET FAMILY — READ BEFORE TOUCHING
# ══════════════════════════════════════════════════════════════════════════════
#
# THREE targets, ONE sanctioned difference:
#
#   check-common  — every check step EXCEPT cargo-deny.
#                   This is the shared base. BOTH lanes run exactly this.
#
#   check         — check-common + cargo-deny.  LOCAL / PRECOMMIT lane.
#                   The git pre-commit hook runs this.  cargo-deny MUST run
#                   locally because it is NOT run in CI (cargo-deny is not
#                   installed on the GitHub Actions runner).
#
#   check-ci      — check-common ONLY.  CI lane.
#                   cargo-deny is intentionally absent: the tool is not
#                   installed on the GitHub Actions runner and we have chosen
#                   NOT to install it there.  Supply-chain / advisory checks
#                   are enforced via the local precommit hook instead.
#
# ANTI-DRIFT RULE (MANDATORY):
#   Any new check step MUST be added to check-common so BOTH lanes pick it up
#   automatically.  Adding a step directly to `check` or `check-ci` (other
#   than the existing cargo-deny line on `check`) is FORBIDDEN.  Violating
#   this rule silently breaks either local or CI coverage, and the mismatch
#   will not be caught by the other lane.
#
# ══════════════════════════════════════════════════════════════════════════════

# Shared base: all checks except cargo-deny.
# ADD new steps here by appending the target name to the `steps` string below.
# DO NOT add new steps directly to `check` or `check-ci` — they inherit via this target.
check-common:
	@steps="lint format-check typecheck test cargo-check cargo-clippy cargo-test cargo-test-python-features cargo-test-no-python cargo-clippy-no-python check-no-pyo3"; \
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
	echo "check-common: all steps passed (lint format-check typecheck test cargo-check cargo-clippy cargo-test cargo-test-python-features cargo-test-no-python cargo-clippy-no-python check-no-pyo3)"

# LOCAL / PRECOMMIT lane: check-ci + cargo-deny (the supply-chain gate).
# Depends on check-ci (not check-common directly) so the one-sanctioned-divergence
# relationship is enforced structurally: any step added to check-ci (or check-common)
# is automatically picked up here, and a future developer cannot accidentally add a
# step only to `check` without it being visible as a structural anomaly.
# cargo-deny is NOT installed on the GitHub Actions runner; it is enforced
# here via the local pre-commit hook.  DO NOT add steps here directly — add
# them to check-common instead so check-ci also picks them up.
check: check-ci
	@tmpfile=$$(mktemp); \
	if ! $(MAKE) cargo-deny >"$$tmpfile" 2>&1; then \
	    echo "FAILED: cargo-deny"; \
	    cat "$$tmpfile"; \
	    rm -f "$$tmpfile"; \
	    exit 1; \
	fi; \
	rm -f "$$tmpfile"; \
	echo "check: all steps passed (check-ci + cargo-deny)"

# CI lane: check-common only.  cargo-deny is deliberately omitted — it is not
# installed on the GitHub Actions runner and supply-chain checks are enforced
# via the local pre-commit hook instead.  DO NOT add steps here directly —
# add them to check-common so `check` (local) also picks them up.
check-ci: check-common

lint:
	uv run --group lint --group test ruff check -q .

format-check:
	uv run --group lint ruff format --check -q .

fix:
	uv run --group lint ruff check --fix .
	uv run --group lint ruff format .

typecheck:
	uv run --group lint --group test pyright

# Aggregate target: build every native extension the Python test suite requires.
# Wire this as a prerequisite of `test` so `make test` and `make check` (which
# calls $(MAKE) test) always build fixtures before running pytest — no stale-SO risk.
build-test-fixtures: build-native build-test-user-ext build-fegen-rust-cst build-rust-parser-fixture build-poc-cst

test: build-test-fixtures
	uv run --group lint --group test pytest -q

# cargo-check: fast compile for the workspace. Test-crate per-feature checks are omitted
# here because cargo-clippy (a strict superset of cargo-check) already covers them at the
# same feature sets; running both in make check would double-compile each fixture crate.
cargo-check:
	cargo check -q

cargo-test:
	cargo test -q

# Run fltk-cst-core tests with the python feature enabled, linking libpython via a uv-managed
# interpreter (python-build-standalone ships the unversioned libpython3.10.so required to link).
# PYO3_PYTHON points pyo3's build script at the managed interpreter; it emits the correct
# rustc-link-search automatically — no build.rs or RUSTFLAGS needed.
#
# `env -u VIRTUAL_ENV` is required: with a venv active, `uv python find --managed-python` returns
# the venv's interpreter (a system python whose LIBDIR lacks the unversioned libpython3.10.so),
# and the link fails. Stripping VIRTUAL_ENV forces resolution to a managed standalone regardless
# of whether the caller's shell has the venv activated.
cargo-test-python-features:
	@PYO3_PYTHON=$$(env -u VIRTUAL_ENV uv python find --managed-python --no-project 3.10); \
	if [ -z "$$PYO3_PYTHON" ]; then \
	    echo "cargo-test-python-features: no uv-managed CPython 3.10 found. Run: uv python install cpython-3.10"; \
	    exit 1; \
	fi; \
	PYO3_PYTHON=$$PYO3_PYTHON cargo test -q -p fltk-cst-core --features python

# cargo-clippy covers test crates at their python-on feature set (the only non-default
# feature that adds code; default features for fegen-rust are already python-on).
cargo-clippy:
	cargo clippy -q -- -D warnings
	cargo clippy -q --manifest-path crates/fegen-rust/Cargo.toml -- -D warnings
	cargo clippy -q --manifest-path tests/rust_poc_cst/Cargo.toml -- -D warnings
	cargo clippy -q --manifest-path tests/rust_parser_fixture/Cargo.toml --features python -- -D warnings

# python-off lane: feature isolation requires -p selection (workspace unification would
# re-enable pyo3 via fltk-native's dependency).
cargo-test-no-python:
	cargo test -q -p fltk-cst-core --no-default-features
	cargo test -q -p fltk-parser-core
	cargo test -q --manifest-path tests/rust_parser_fixture/Cargo.toml
	cargo test -q --manifest-path crates/fegen-rust/Cargo.toml --no-default-features
	cargo test -q --manifest-path tests/rust_poc_cst/Cargo.toml --no-default-features
	cargo test -q --manifest-path crates/fltkfmt/Cargo.toml

cargo-clippy-no-python:
	cargo clippy -q -p fltk-cst-core --no-default-features -- -D warnings
	cargo clippy -q -p fltk-parser-core -- -D warnings
	cargo clippy -q --manifest-path tests/rust_parser_fixture/Cargo.toml -- -D warnings
	cargo clippy -q --manifest-path crates/fegen-rust/Cargo.toml --no-default-features -- -D warnings
	cargo clippy -q --manifest-path tests/rust_poc_cst/Cargo.toml --no-default-features -- -D warnings
	cargo clippy -q --manifest-path crates/fltkfmt/Cargo.toml --all-targets -- -D warnings
	# python-on clippy for rust_poc_cst is covered by cargo-clippy (default features = extension-module)

# Mechanical check: verify pyo3 is absent from the python-off dependency graphs.
# Uses a positive control (a crate guaranteed present in that graph) before the negative
# assertion to prevent false passes when cargo tree fails silently.
check-no-pyo3:
	@set -e; \
	core="$$(cargo tree -p fltk-cst-core --no-default-features --edges normal,build)"; \
	echo "$$core" | grep -q fltk-cst-core || { echo "FAIL: check-no-pyo3 broken: cargo tree output lacks fltk-cst-core"; exit 1; }; \
	! echo "$$core" | grep -q pyo3 || { echo "FAIL: pyo3 present in fltk-cst-core --no-default-features graph"; exit 1; }; \
	parser="$$(cargo tree -p fltk-parser-core --edges normal,build)"; \
	echo "$$parser" | grep -q fltk-cst-core || { echo "FAIL: check-no-pyo3 broken: cargo tree output lacks fltk-cst-core"; exit 1; }; \
	! echo "$$parser" | grep -q pyo3 || { echo "FAIL: pyo3 present in fltk-parser-core dependency graph"; exit 1; }; \
	fixture="$$(cargo tree --manifest-path tests/rust_parser_fixture/Cargo.toml --edges normal,build)"; \
	echo "$$fixture" | grep -q fltk-parser-core || { echo "FAIL: check-no-pyo3 broken: cargo tree output lacks fltk-parser-core"; exit 1; }; \
	! echo "$$fixture" | grep -q pyo3 || { echo "FAIL: pyo3 present in rust_parser_fixture default-features graph"; exit 1; }; \
	fegen="$$(cargo tree --manifest-path crates/fegen-rust/Cargo.toml --no-default-features --edges normal,build)"; \
	echo "$$fegen" | grep -q fltk-parser-core || { echo "FAIL: check-no-pyo3 broken: cargo tree output lacks fltk-parser-core"; exit 1; }; \
	! echo "$$fegen" | grep -q pyo3 || { echo "FAIL: pyo3 present in fegen-rust --no-default-features graph"; exit 1; }; \
	poc="$$(cargo tree --manifest-path tests/rust_poc_cst/Cargo.toml --no-default-features --edges normal,build)"; \
	echo "$$poc" | grep -q fltk-cst-core || { echo "FAIL: check-no-pyo3 broken: cargo tree output lacks fltk-cst-core"; exit 1; }; \
	! echo "$$poc" | grep -q pyo3 || { echo "FAIL: pyo3 present in rust_poc_cst --no-default-features graph"; exit 1; }; \
	fltkfmt="$$(cargo tree --manifest-path crates/fltkfmt/Cargo.toml --edges normal,build)"; \
	echo "$$fltkfmt" | grep -q fltk-parser-core || { echo "FAIL: check-no-pyo3 broken: cargo tree output lacks fltk-parser-core"; exit 1; }; \
	! echo "$$fltkfmt" | grep -q pyo3 || { echo "FAIL: pyo3 present in fltkfmt dependency graph"; exit 1; }; \
	echo "check-no-pyo3: pyo3 absent from python-off graphs"

# Supply-chain gate: RustSec advisories, license allow-list, banned/duplicate crates,
# and source allow-listing (cargo-deny). The standalone fixture crates have their own
# Cargo.lock, so each is checked explicitly; all share the single root deny.toml policy
# via --config (path resolves from cwd = repo root).
cargo-deny:
	cargo deny --manifest-path Cargo.toml check --config deny.toml
	cargo deny --manifest-path crates/fegen-rust/Cargo.toml check --config deny.toml
	cargo deny --manifest-path tests/rust_cst_fixture/Cargo.toml check --config deny.toml
	cargo deny --manifest-path tests/rust_parser_fixture/Cargo.toml check --config deny.toml
	cargo deny --manifest-path tests/rust_poc_cst/Cargo.toml check --config deny.toml
	cargo deny --manifest-path crates/fltkfmt/Cargo.toml check --config deny.toml

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
# Produces the importable module 'fegen_rust_cst' used by
# parse_grammar(rust_fegen_cst_module="fegen_rust_cst.cst") and the AC8 Tier-2 test
# (real Cst2Gsm on Rust fegen backend).
build-fegen-rust-cst:
	cd crates/fegen-rust && uv run --group dev maturin develop

# Build the fixture Rust parser extension (separate cdylib crate).
# Produces the importable module 'rust_parser_fixture' used by parity tests.
build-rust-parser-fixture:
	cd tests/rust_parser_fixture && uv run --group dev maturin develop --features extension-module

# Build the PoC CST fixture extension (separate cdylib crate).
# Produces the importable module 'poc_cst' used by PoC CST tests.
build-poc-cst:
	cd tests/rust_poc_cst && uv run --group dev maturin develop

# Emit Rust CST source from a grammar (no compilation).
# Usage: make gen-rust-cst GRAMMAR=path/to/grammar.fltkg RS_OUT=path/to/output.rs [EXTRA_ARGS=...]
gen-rust-cst:
	uv run python -m fltk.fegen.genparser gen-rust-cst $(GRAMMAR) $(RS_OUT) $(EXTRA_ARGS)

# Emit Rust parser source from a grammar (no compilation).
# Usage: make gen-rust-parser GRAMMAR=path/to/grammar.fltkg RS_OUT=path/to/output.rs
gen-rust-parser:
	uv run python -m fltk.fegen.genparser gen-rust-parser $(GRAMMAR) $(RS_OUT)

# Emit Rust unparser source from a grammar (no compilation).
# Usage: make gen-rust-unparser GRAMMAR=path/to/grammar.fltkg RS_OUT=path/to/output.rs [EXTRA_ARGS=...]
gen-rust-unparser:
	uv run python -m fltk.fegen.genparser gen-rust-unparser $(GRAMMAR) $(RS_OUT) $(EXTRA_ARGS)

# Regenerate the parser for the fegen grammar into the fegen-rust crate.
build-fegen-rust-parser:
	uv run python -m fltk.fegen.genparser gen-rust-parser \
		fltk/fegen/fegen.fltkg crates/fegen-rust/src/parser.rs

# Run native (no-Python) Rust parser tests for the fegen grammar.
test-native-parser:
	cd crates/fegen-rust && cargo test --no-default-features

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
	uv run python -m fltk.fegen.genparser generate --protocol \
		fltk/fegen/fegen.fltkg fltk fltk.fegen.fltk_cst \
		--output-dir fltk/fegen
	# Python: bootstrap grammar → bootstrap_cst.py, bootstrap_cst_protocol.py, bootstrap_parser.py, bootstrap_trivia_parser.py
	uv run python -m fltk.fegen.genparser generate --protocol \
		fltk/fegen/bootstrap.fltkg bootstrap fltk.fegen.bootstrap_cst \
		--output-dir fltk/fegen
	# Python: toy grammar (toy_cst.py, toy_cst_protocol.py, toy_parser.py, toy_trivia_parser.py)
	uv run python -m fltk.fegen.genparser generate --protocol \
		fltk/unparse/toy.fltkg toy fltk.unparse.toy_cst \
		--output-dir fltk/unparse
	# Python: unparsefmt grammar (unparsefmt_cst.py, unparsefmt_cst_protocol.py, unparsefmt_parser.py, unparsefmt_trivia_parser.py)
	uv run python -m fltk.fegen.genparser generate --protocol \
		fltk/unparse/unparsefmt.fltkg unparsefmt fltk.unparse.unparsefmt_cst \
		--output-dir fltk/unparse
	# Python: regex grammar (regex_cst.py, regex_cst_protocol.py, regex_parser.py, regex_trivia_parser.py)
	uv run python -m fltk.fegen.genparser generate --protocol \
		fltk/fegen/regex.fltkg regex fltk.fegen.regex_cst \
		--output-dir fltk/fegen
	# Rust: src/lib.rs (fltk._native module wiring — span-only runtime, no grammar submodules)
	uv run python -m fltk.fegen.genparser gen-rust-lib src/lib.rs \
		--module-name _native --register-span-types --unknown-span-static --no-cst --no-parser
	# Rust: tests/rust_poc_cst/src/cst.rs (PoC grammar — fltk/fegen/test_data/poc_grammar.fltkg)
	uv run python -m fltk.fegen.genparser gen-rust-cst \
		fltk/fegen/test_data/poc_grammar.fltkg tests/rust_poc_cst/src/cst.rs
	# Rust: tests/rust_cst_fixture/src/cst.rs (phase4_roundtrip.fltkg)
	$(MAKE) gen-rust-cst GRAMMAR=fltk/fegen/test_data/phase4_roundtrip.fltkg RS_OUT=tests/rust_cst_fixture/src/cst.rs
	# Rust: crates/fegen-rust/src/cst.rs (fegen.fltkg) + fltk/_stubs/fegen_rust_cst/cst.pyi stub +
	# fltk/_stubs/fegen_rust_cst/__init__.pyi stub-package marker (dogfooded via --init-pyi-output)
	$(MAKE) gen-rust-cst GRAMMAR=fltk/fegen/fegen.fltkg RS_OUT=crates/fegen-rust/src/cst.rs \
		EXTRA_ARGS="--protocol-module fltk.fegen.fltk_cst_protocol --pyi-output fltk/_stubs/fegen_rust_cst/cst.pyi \
		            --init-pyi-output fltk/_stubs/fegen_rust_cst/__init__.pyi --extension-name fegen_rust_cst --submodules cst,parser,unparser"
	# Rust: crates/fegen-rust/src/parser.rs (fegen.fltkg) — generated Rust parser.
	$(MAKE) build-fegen-rust-parser
	# Rust: crates/fegen-rust/src/unparser.rs (fegen.fltkg, fegen.fltkfmt-baked) +
	# fltk/_stubs/fegen_rust_cst/unparser.pyi stub.  Powers the pure-Rust fltkfmt binary.
	$(MAKE) gen-rust-unparser GRAMMAR=fltk/fegen/fegen.fltkg \
		RS_OUT=crates/fegen-rust/src/unparser.rs \
		EXTRA_ARGS="--format-config fltk/fegen/fegen.fltkfmt \
		            --protocol-module fltk.fegen.fltk_cst_protocol \
		            --pyi-output fltk/_stubs/fegen_rust_cst/unparser.pyi"
	# Rust: tests/rust_parser_fixture/src/cst.rs, parser.rs, and unparser.rs (rust_parser_fixture.fltkg)
	$(MAKE) gen-rust-cst GRAMMAR=fltk/fegen/test_data/rust_parser_fixture.fltkg RS_OUT=tests/rust_parser_fixture/src/cst.rs
	$(MAKE) gen-rust-parser GRAMMAR=fltk/fegen/test_data/rust_parser_fixture.fltkg RS_OUT=tests/rust_parser_fixture/src/parser.rs
	# Fixture CST protocol module: the Python typing source the committed unparser .pyi (OQ-3) types
	# `node` params against.  The Rust backend supplies cst/parser; only the protocol is needed for
	# typing, so --protocol-only emits just rust_parser_fixture_cst_protocol.py (no CST, no parsers).
	uv run python -m fltk.fegen.genparser generate --protocol-only \
		fltk/fegen/test_data/rust_parser_fixture.fltkg rust_parser_fixture rust_parser_fixture_cst \
		--output-dir tests
	# unparser.rs (.fltkfmt-baked) + the committed fixture unparser .pyi stub (OQ-3, pyright-checked
	# via fltk/_stubs) + fltk/_stubs/rust_parser_fixture/__init__.pyi stub-package marker (dogfooded
	# via --init-pyi-output; the fixture's gen-rust-cst writes no cst.pyi, so the marker rides the
	# unparser path).  --pyi-output names the stub by the compiled submodule's import name.
	$(MAKE) gen-rust-unparser GRAMMAR=fltk/fegen/test_data/rust_parser_fixture.fltkg RS_OUT=tests/rust_parser_fixture/src/unparser.rs \
		EXTRA_ARGS="--format-config fltk/fegen/test_data/rust_parser_fixture.fltkfmt --protocol-module tests.rust_parser_fixture_cst_protocol --pyi-output fltk/_stubs/rust_parser_fixture/unparser.pyi \
		            --init-pyi-output fltk/_stubs/rust_parser_fixture/__init__.pyi --extension-name rust_parser_fixture --submodules cst,parser,unparser,unparser_default,collision_cst,collision_parser"
	# Default-FormatterConfig variant (no --format-config) for default-config cross-backend parity (§4).
	$(MAKE) gen-rust-unparser GRAMMAR=fltk/fegen/test_data/rust_parser_fixture.fltkg RS_OUT=tests/rust_parser_fixture/src/unparser_default.rs
	# Rust: tests/rust_parser_fixture/src/collision_cst.rs and collision_parser.rs (collision_fixture.fltkg)
	# Demonstrates that a cdylib can host multiple grammars; proves Parser/ApplyResult CST
	# classes and the parser machinery coexist without collision after the cst/parser split.
	$(MAKE) gen-rust-cst GRAMMAR=fltk/fegen/test_data/collision_fixture.fltkg RS_OUT=tests/rust_parser_fixture/src/collision_cst.rs
	uv run python -m fltk.fegen.genparser gen-rust-parser --cst-mod-path super::collision_cst \
		fltk/fegen/test_data/collision_fixture.fltkg tests/rust_parser_fixture/src/collision_parser.rs
	# Normalize formatting. Order matters:
	# 1. ruff check --fix: upgrades typing.Union[X,Y] → X|Y and similar, so ruff format can then
	#    wrap the resulting X|Y chains correctly.  Exit code ignored — residuals handled by step 2.
	# 2. ruff format: applies canonical line-length formatting.
	# 3. ruff check --fix again: cleans up any issues exposed after formatting.
	# make check (the gate) is the definitive clean check; intermediate exits are informational.
	uv run --group lint ruff check --fix . || true
	uv run --group lint ruff format .
	uv run --group lint ruff check --fix . || true
