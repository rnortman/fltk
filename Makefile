.PHONY: check check-ci check-common \
        check-bazel-locks bazel-toolchain-guard \
        bazel-test bazel-lint bazel-consumer-check fix regen-seed

# ══════════════════════════════════════════════════════════════════════════════
# CHECK TARGET FAMILY — READ BEFORE TOUCHING
# ══════════════════════════════════════════════════════════════════════════════
#
# ONE gate, no divergence:
#
#   check-common  — every check step.  This is the whole gate.
#
#   check         — check-common.  LOCAL / PRECOMMIT lane; the git pre-commit
#                   hook runs it.
#
#   check-ci      — an alias for `check`, kept because .github/workflows/ci.yml
#                   and muscle memory name it.
#
# Add every new step to check-common: a step added directly to `check` or
# `check-ci` would reintroduce local/CI divergence.
#
# ══════════════════════════════════════════════════════════════════════════════

# ADD new steps here by appending the target name to CHECK_STEPS below.
#
# Single source for the step list, consumed by both the loop and the success echo
# (no duplicated literal to drift).  ORDER IS LOAD-BEARING, and the rule behind it is
# general: a step that only DIFFS a generated file must run after the step that REWRITES
# it, or it passes vacuously on the stale committed copy.
#   - check-bazel-locks must run AFTER bazel-test and bazel-consumer-check, and therefore
#     stays LAST.  Those two lanes are the writer that repairs a stale MODULE.bazel.lock in
#     place (bzlmod's default lockfile_mode is `update`) and the writer that rewrites the
#     crate_universe locks on a repin.  A new step appended after it that rewrites a lockfile
#     would reopen the blind spot; put such a step before it.
#
# Three Bazel lanes plus one lock diff is the whole gate: `bazel test //...` runs every
# test (Python, Rust, Starlark) and `bazel build --config lint //...` runs every linter, so
# a step that duplicates either belongs in the build graph instead of here.
CHECK_STEPS := bazel-toolchain-guard bazel-test bazel-lint bazel-consumer-check \
               check-bazel-locks

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

# The gate.  DO NOT add steps here directly — add them to check-common.
check: check-common

# Alias for `check`, so the CI workflow and existing habits keep working.  There is no
# local/CI divergence left for it to name.
check-ci: check

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

# There are no cargo lanes, and no cargo.  Every crate in the tree has Bazel targets in
# both of its feature flavors, so `bazel test //...` compiles and runs them and the
# rules_rust clippy aspect in `bazel build --config lint //...` lints them.  Feature
# carve-outs are named targets: //crates/fltk-ast-core:no_features_test (every feature off,
# the only build compiling the `cfg(not(feature = "indexmap"))` arms), and
# //crates/fltk-cst-core:python_test (the `python` feature set).  The cquery loop in
# bazel-test asserts pyo3 absence over every :no_python target and every rust_binary.
#
# tests/test_cargo_retirement.py is what keeps it that way: no tracked manifest, no cargo
# invocation in this file, the CI workflow, .bazelrc or any BUILD file.

# Bazel lock drift gate.  Six tracked, Bazel-written locks: the two MODULE.bazel.lock files
# and the crate_universe pair in each workspace (cargo-bazel-lock.json, the render, and
# cargo-bazel-resolved.lock, the resolution it was rendered from).  bzlmod's default
# lockfile_mode is `update`, so a Bazel run rewrites a stale MODULE.bazel.lock in place and
# still reports green, and a repin rewrites the crate_universe pair the same way; nothing ever
# demands the repair be committed.  The Bazel lanes above are the regenerating half of the
# usual regenerate-in-place + diff pattern, which is why this step is a pure diff and why it
# runs last (see the CHECK_STEPS comment).  Run standalone without a prior Bazel run it passes
# vacuously; `make check` is the gate that clears these.
#
# requirements_lock.txt is deliberately absent: //:requirements.test is its gate, and it
# runs inside `make bazel-test`.
#
# The set is DERIVED from git rather than listed: a list covers only what it happens to name,
# so a third Bazel workspace, or a second crate_universe hub in an existing one, would add a
# tracked lock that no step diffs and nothing notices.  A derivation that comes back empty is a
# gate checking nothing and fails rather than passing.
check-bazel-locks:
	@set -e; \
	locks="$$(git ls-files '*MODULE.bazel.lock' '*cargo-bazel-lock.json' '*cargo-bazel-resolved.lock')"; \
	test -n "$$locks" || { echo "FAIL: no tracked Bazel-written lockfile found; this gate is checking nothing"; exit 1; }; \
	git diff --exit-code -- $$locks \
		|| { echo "FAIL: Bazel lockfiles drifted; commit the regenerated files"; exit 1; }

# Drift detector for the Rust version.  The root MODULE.bazel's rust.toolchain tag is the
# single pin — there is no host toolchain and no rust-toolchain.toml — and every other Bazel
# module that pulls in rules_rust must mirror it.  Without a mirrored tag a module silently
# compiles with rules_rust's own default toolchain: a different compiler over the same source.
# The mirror list is DERIVED from the tracked MODULE.bazel files, not hardcoded, so a newly
# added Bazel workspace is guarded the moment it depends on rules_rust; a module that never
# mentions rules_rust is skipped, and a guard that ends up checking nothing fails rather than
# passing vacuously.  Read-only, and it fails in milliseconds — before a potentially cold
# multi-minute build with the wrong compiler.
bazel-toolchain-guard:
	@want="$$(sed -n 's/^ *versions *= *\["\([^"]*\)"\].*/\1/p' MODULE.bazel)"; \
	test -n "$$want" || { echo "FAIL: no rust.toolchain versions pin found in MODULE.bazel"; exit 1; }; \
	checked=0; \
	for f in $$(git ls-files 'MODULE.bazel' '*/MODULE.bazel'); do \
	    grep -qE '@rules_rust|"rules_rust"' $$f || continue; \
	    checked=$$((checked + 1)); \
	    grep -qF "versions = [\"$$want\"]" $$f \
	        || { echo "FAIL: $$f rust.toolchain pin does not match the root MODULE.bazel pin ($$want); edit it to match"; exit 1; }; \
	done; \
	test "$$checked" -gt 1 \
	    || { echo "FAIL: only the root MODULE.bazel references rules_rust; the toolchain guard is checking nothing"; exit 1; }

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
#
# //tests:rust_gate_lib is named explicitly for the same reason: the compile gate crate links
# the :no_python flavor of every runtime crate but is neither named no_python nor a binary, so
# neither pattern sweeps it.
#
# The second query is the cargo retirement gate's blind-spot check.  That gate reads a runfiles
# tree, so it sees a package only through the package's own cargo_file_probe: a package that
# never declares one can carry a Cargo.toml (including one with its own [workspace] table) and
# a cargo invocation in its BUILD file with every test green.  Only a query over the build graph
# can see a package that opted out, which is why this lives here and not in a py_test.
bazel-test: bazel-toolchain-guard
	bazel test //...
	@set -e; \
	err="$$(mktemp)"; trap 'rm -f "$$err"' EXIT; \
	labels="$$(bazel query 'attr(name, "^no_python$$", //...) union kind("rust_binary rule", //...) union set(//tests:rust_gate_lib)' 2>"$$err")" \
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
	@set -e; \
	err="$$(mktemp)"; trap 'rm -f "$$err"' EXIT; \
	probed="$$(bazel query 'attr(name, "^cargo_file_probe$$", //...)' --output package 2>"$$err" | sort -u)" \
	    || { echo "FAIL: bazel-test broken: query for cargo_file_probe targets failed"; cat "$$err"; exit 1; }; \
	test -n "$$probed" || { echo "FAIL: bazel-test broken: no cargo_file_probe target found"; exit 1; }; \
	packages="$$(bazel query '//...' --output package 2>"$$err" | sort -u)" \
	    || { echo "FAIL: bazel-test broken: query for packages failed"; cat "$$err"; exit 1; }; \
	unprobed="$$(echo "$$packages" | while read -r pkg; do echo "$$probed" | grep -qxF "$$pkg" || echo "$$pkg"; done)"; \
	test -z "$$unprobed" \
	    || { echo "FAIL: these packages declare no cargo_file_probe, so the retirement gate cannot see them:"; echo "$$unprobed"; exit 1; }; \
	echo "bazel-test: every package declares a cargo_file_probe"

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
