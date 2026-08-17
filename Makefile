.PHONY: check check-ci check-common cargo-deny \
        check-cargo-lock check-bazel-locks bazel-toolchain-guard \
        bazel-test bazel-lint bazel-consumer-check fix regen-seed

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
# ADD new steps here by appending the target name to CHECK_STEPS below.
# DO NOT add new steps directly to `check` or `check-ci` — they inherit via this target.
#
# Single source for the step list, consumed by both the loop and the success echo
# (no duplicated literal to drift).  ORDER IS LOAD-BEARING, and the rule behind it is
# general: a step that only DIFFS a generated file must run after the step that REWRITES
# it, or it passes vacuously on the stale committed copy.
#   - check-bazel-locks must run AFTER bazel-test and bazel-consumer-check, and therefore
#     stays LAST.  Those two lanes are the writer that repairs a stale MODULE.bazel.lock in
#     place (bzlmod's default lockfile_mode is `update`).  A new step appended after it that
#     rewrites a lockfile would reopen the blind spot; put such a step before it.
#   - Nothing rewrites a Cargo.lock: no cargo build step survives, and every cargo command
#     left in the tree passes --locked.  check-cargo-lock therefore carries its own staleness
#     probe rather than depending on an earlier step.
#
# Three Bazel lanes plus two lock diffs is the whole gate: `bazel test //...` runs every
# test (Python, Rust, Starlark) and `bazel build --config lint //...` runs every linter, so
# a step that duplicates either belongs in the build graph instead of here.
CHECK_STEPS := bazel-toolchain-guard bazel-test bazel-lint bazel-consumer-check \
               check-cargo-lock check-bazel-locks

check-common:
	@steps="$(CHECK_STEPS)"; \
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
	echo "check-common: all steps passed ($(CHECK_STEPS))"

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

# All ruff invocations (fix, check, format) share the same pin and config.
fix:
	bazel run //:ruff_fix

# Regenerate the committed self-hosting seed (fltk_cst.py, fltk_cst_protocol.py,
# fltk_parser.py, fltk_trivia_parser.py) from fegen.fltkg.  Run it after editing
# fegen.fltkg or a Python-backend generator; tests/test_seed_fixed_point.py fails when
# the committed seed and the generator disagree.  Output is already normalized.
regen-seed:
	bazel run //:regen_seed

# The pytest suite runs under Bazel: one py_test per file, each depending on the extension
# modules it imports, so there is no lane in which a stale cdylib can be imported.  Run the
# whole suite with `make bazel-test`, or one file with `bazel test //tests:test_<name>`.

# There are no cargo build/test/lint lanes.  Every crate in the tree has Bazel targets in
# both of its feature flavors, so `bazel test //...` compiles and runs them and the
# rules_rust clippy aspect in `bazel build --config lint //...` lints them — over strictly
# more configurations than the retired lanes covered (the fegen-rust, fltkfmt and fixture
# crates have no Cargo manifest at all).  The feature carve-outs the cargo lanes used to own
# are named targets now: //crates/fltk-ast-core:no_features_test (every feature off, the only
# build compiling the `cfg(not(feature = "indexmap"))` arms — the uuid and decimal gates are
# additive, so the all-features flavor subsumes the default one),
# //crates/fltk-cst-core:python_test (the `python` feature set), and every crate's
# :no_python_test.  check-no-pyo3 is gone the same way: the cquery loop in bazel-test below
# asserts the same property over every :no_python target and every rust_binary.
#
# cargo itself is still required: cargo-deny runs on it, check-cargo-lock probes with it, and
# the three compile-gate py_tests hand a throwaway crate to it.  Those gates resolve
# --offline, and no step here fetches anymore, so a fresh clone (and CI) needs one
# `cargo fetch --locked` to warm the registry cache.

# Cargo lock drift gate.  `cargo metadata --locked` is the staleness detector: nothing in
# the tree rewrites a Cargo.lock anymore, so the git diff below cannot see a lock that no
# step regenerated -- each tracked manifest is asked directly whether its lock still
# resolves, and --locked makes a stale one an error rather than a silent repair.  The diff
# then catches a lock edited by hand or left half-staged.
#
# requirements_lock.txt is deliberately absent: //:requirements.test is its gate, and it
# runs inside `make bazel-test`.
#
# The manifest set is DERIVED from the tracked Cargo.lock files rather than written out here,
# the same way bazel-toolchain-guard derives its mirror list: a hand-written list covers what
# it happens to name, so a crate that later regains a tracked lock would drift with both halves
# of the gate agreeing that it does not exist.  A derivation that ends up checking nothing
# fails rather than passing vacuously.
#
# The same derived set pins .github/dependabot.yml's cargo `directories`, which is otherwise a
# hand-written restatement of it: a manifest that gains a tracked lock would be probed and
# diffed here but never receive dependency updates, and a directory that leaves the tree would
# make the updater error out weekly on a file nobody reads.
check-cargo-lock:
	@set -e; \
	locks="$$(git ls-files '*Cargo.lock')"; \
	test -n "$$locks" || { echo "FAIL: no tracked Cargo.lock found; check-cargo-lock is checking nothing"; exit 1; }; \
	for lock in $$locks; do \
	    manifest="$${lock%Cargo.lock}Cargo.toml"; \
	    cargo metadata --locked --format-version 1 --manifest-path $$manifest >/dev/null \
	        || { echo "FAIL: $$manifest and its lockfile disagree; re-resolve it (cargo metadata --manifest-path $$manifest) and commit the result"; exit 1; }; \
	done; \
	derived="$$(for lock in $$locks; do dir="$${lock%Cargo.lock}"; printf '/%s\n' "$${dir%/}"; done | sort)"; \
	declared="$$(awk '/package-ecosystem:/ { cargo = ($$0 ~ /"cargo"/); dirs = 0 } cargo && /^ *directories:/ { dirs = 1; next } dirs { if ($$0 ~ /^ *- "/) { sub(/^ *- "/, ""); sub(/".*$$/, ""); print } else { dirs = 0 } }' .github/dependabot.yml | sort)"; \
	test -n "$$declared" || { echo "FAIL: .github/dependabot.yml declares no cargo directories; the manifests get no dependency updates"; exit 1; }; \
	test "$$derived" = "$$declared" || { echo "FAIL: the cargo updater covers [$$declared] but the tracked locks live in [$$derived]; update .github/dependabot.yml"; exit 1; }
	@set -e; \
	git diff --exit-code -- $$(git ls-files '*Cargo.lock') \
	    || { echo "FAIL: lockfiles drifted; commit the regenerated files"; exit 1; }

# Bazel lock drift gate.  MODULE.bazel.lock and tests/bazel_consumer/MODULE.bazel.lock are
# tracked, generated files, and bzlmod's default lockfile_mode is `update`: a Bazel run
# rewrites a stale one in place and still reports green, so nothing ever demands the repair
# be committed.  The Bazel lanes above are the regenerating half of the usual
# regenerate-in-place + diff pattern, which is why this step is a pure diff and why it runs
# last (see the CHECK_STEPS comment).  Run standalone without a prior Bazel run it passes
# vacuously; `make check` is the gate that clears these.
check-bazel-locks:
	git diff --exit-code -- MODULE.bazel.lock tests/bazel_consumer/MODULE.bazel.lock \
		|| { echo "FAIL: Bazel lockfiles drifted; commit the regenerated files"; exit 1; }

# Drift detector for the Rust version: rust-toolchain.toml is the single source of
# truth, but bzlmod cannot read TOML, so every Bazel module that pulls in rules_rust
# must mirror the version in a rust.toolchain tag.  Without a mirrored tag a module
# silently compiles with rules_rust's own default toolchain — a different compiler
# over the same source.  The mirror list is DERIVED from the tracked MODULE.bazel
# files, not hardcoded, so a newly added Bazel workspace is guarded the moment it
# depends on rules_rust; a module that never mentions rules_rust is skipped, and a
# guard that ends up checking nothing fails rather than passing vacuously.
# Read-only, and it fails in milliseconds — before a potentially cold multi-minute
# build with the wrong compiler.
bazel-toolchain-guard:
	@want="$$(sed -n 's/^channel *= *"\(.*\)"/\1/p' rust-toolchain.toml)"; \
	test -n "$$want" || { echo "FAIL: no channel found in rust-toolchain.toml"; exit 1; }; \
	checked=0; \
	for f in $$(git ls-files 'MODULE.bazel' '*/MODULE.bazel'); do \
	    grep -qE '@rules_rust|"rules_rust"' $$f || continue; \
	    checked=$$((checked + 1)); \
	    grep -qF "versions = [\"$$want\"]" $$f \
	        || { echo "FAIL: $$f rust.toolchain pin does not match rust-toolchain.toml channel ($$want); edit it to match"; exit 1; }; \
	done; \
	test "$$checked" -gt 0 \
	    || { echo "FAIL: no tracked MODULE.bazel references rules_rust; the toolchain guard is checking nothing"; exit 1; }

# Bazel verification lane for fltk's OWN Bazel surface.  Consumer-facing breakage
# (a downstream module importing @fltk) is caught by bazel-consumer-check below.
#
# bazel-consumer-check only reaches the :no_python flavors its two consumer targets happen
# to link, which leaves any unlinked :no_python target (fltk-serde-core's, today) with no
# gate at all — and a :no_python target whose deps point at the python flavor still builds
# and still passes its tests, it just links libpython.
#
# The query spans //... rather than //crates/...: the fixture extensions under tests/ carry
# :no_python flavors of their own.  It also takes in every rust_binary, which is the only way
# fltkfmt is covered: it is a pure-Rust binary rather than a two-flavor library, so it has no
# target named no_python, and swapping its fegen dependency to the python flavor would
# otherwise link libpython with nothing objecting.
bazel-test: bazel-toolchain-guard
	bazel test //...
	@set -e; \
	err="$$(mktemp)"; trap 'rm -f "$$err"' EXIT; \
	labels="$$(bazel query 'attr(name, "^no_python$$", //...) union kind("rust_binary rule", //...)' 2>"$$err")" \
	    || { echo "FAIL: bazel-test broken: query for pyo3-free targets failed"; cat "$$err"; exit 1; }; \
	test -n "$$labels" || { echo "FAIL: bazel-test broken: no pyo3-free targets found"; exit 1; }; \
	for target in $$labels; do \
	    graph="$$(bazel cquery "deps($$target)" 2>"$$err")" \
	        || { echo "FAIL: bazel-test broken: cquery for $$target failed"; cat "$$err"; exit 1; }; \
	    echo "$$graph" | grep -q 'fltk-cst-core:no_python' \
	        || { echo "FAIL: bazel-test broken: cquery output for $$target lacks fltk-cst-core:no_python"; cat "$$err"; exit 1; }; \
	    ! echo "$$graph" | grep -qi pyo3 \
	        || { echo "FAIL: pyo3 present in the $$target Bazel graph"; exit 1; }; \
	    echo "bazel-test: pyo3 absent from $$target"; \
	done

# The whole lint surface, via one Bazel invocation (config in .bazelrc): the rules_rust
# clippy aspect over every Rust target, plus the flag-gated Python lint targets
# (//:ruff_check, //:ruff_format_check, //:pyright).  `-D warnings` comes from the
# clippy_flags setting; without it clippy prints and passes.
bazel-lint: bazel-toolchain-guard
	bazel build --config lint //...

# Bazel verification lane for fltk's CONSUMER surface: exercises the cross-module
# @fltk// load path that `bazel test //...` in the root cannot cover (same-repo //).
#
# The cquery step is the consumer-side twin of the pyo3 guard in bazel-test: //:consumer_ast
# and //:consumer_fmt_bin are the pure-Rust consumer configurations (AST and
# unparser/formatter), and a pyo3 edge reaching either means a runtime crate's :no_python
# flavor started carrying the python one.  Nothing about the build fails when that happens —
# the crate still compiles, it just links libpython — so the assertion is the only witness.
# Positive control first: a silently failing cquery would otherwise pass the negative
# assertion vacuously.
#
# The second cquery step is the serde-injection twin: //:consumer_serde must be on the consumer
# module's own hub serde and on no other, which is what proves the
# //crates/fltk-serde-core:serde flag reaches fltk-serde-core.  Unlike the pyo3 assertion this
# one has a build-time backstop (a mixed graph does not compile), so it is here to name the
# failure rather than to be the only witness of it.
#
# cquery's stderr goes to a file rather than /dev/null so the ordinary progress output stays
# out of a passing run while the reason for a failing one (analysis error, renamed label,
# stale crate_universe repos wanting CARGO_BAZEL_REPIN) is printed with the failure — the
# gate has to be diagnosable from a CI log alone.
bazel-consumer-check: bazel-toolchain-guard
	cd tests/bazel_consumer && bazel test //...
	@set -e; cd tests/bazel_consumer; \
	err="$$(mktemp)"; trap 'rm -f "$$err"' EXIT; \
	for target in //:consumer_ast //:consumer_fmt_bin //:consumer_serde; do \
	    graph="$$(bazel cquery "deps($$target)" 2>"$$err")" \
	        || { echo "FAIL: bazel-consumer-check broken: cquery for $$target failed"; cat "$$err"; exit 1; }; \
	    echo "$$graph" | grep -q 'fltk-cst-core:no_python' \
	        || { echo "FAIL: bazel-consumer-check broken: cquery output for $$target lacks fltk-cst-core:no_python"; cat "$$err"; exit 1; }; \
	    ! echo "$$graph" | grep -qi pyo3 \
	        || { echo "FAIL: pyo3 present in the $$target Bazel graph"; exit 1; }; \
	    echo "bazel-consumer-check: pyo3 absent from $$target"; \
	done
	@set -e; cd tests/bazel_consumer; \
	err="$$(mktemp)"; trap 'rm -f "$$err"' EXIT; \
	graph="$$(bazel cquery "deps(//:consumer_serde)" 2>"$$err")" \
	    || { echo "FAIL: bazel-consumer-check broken: cquery for //:consumer_serde failed"; cat "$$err"; exit 1; }; \
	echo "$$graph" | grep -q 'consumer_crates.*:serde' \
	    || { echo "FAIL: bazel-consumer-check broken: //:consumer_serde links no serde from the consumer hub"; cat "$$err"; exit 1; }; \
	! echo "$$graph" | grep -q 'fltk_crates.*:serde' \
	    || { echo "FAIL: fltk's own serde is in the //:consumer_serde graph; the serde flag is not reaching fltk-serde-core"; exit 1; }; \
	echo "bazel-consumer-check: //:consumer_serde is on the consumer hub's serde alone"

# Supply-chain gate: RustSec advisories, license allow-list, banned/duplicate crates,
# and source allow-listing (cargo-deny). The two tracked lockfiles are the root workspace's
# and the consumer module's serde hub; both share the single root deny.toml policy via --config
# (path resolves from cwd = repo root).  The Bazel-only crates draw their third-party deps
# from the root lock through @fltk_crates, so they are covered by the first line.
cargo-deny:
	cargo deny --manifest-path Cargo.toml check --config deny.toml
	cargo deny --manifest-path tests/bazel_consumer/serde_hub/Cargo.toml check --config deny.toml

# ── Generated Rust artifacts ─────────────────────────────────────────────────
# There is no `gencode` target and there are no `gen-*` wrappers: every generated Rust source
# in this repo is a Bazel action output, produced by the generate_rust_parser targets in
# crates/fegen-rust, tests/rust_poc_cst, tests/rust_cst_fixture and tests/rust_parser_fixture.
# For ad-hoc generation run the CLI directly:
#
#     bazel run --run_under="cd $(CURDIR) &&" //:genparser -- gen-rust-cst <grammar> <out.rs>
#
# --run_under is what makes a relative output path mean a source-tree path: `bazel run` would
# otherwise execute in the runfiles tree.  `make regen-seed` above is the one target that
# writes generated code into the tree, and the seed is the one artifact it writes.
