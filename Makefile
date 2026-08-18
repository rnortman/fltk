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

# Verbose in CI (GitHub Actions sets CI=true), quiet locally.  $(filter true,...) is an
# exact-word match: CI=false, CI=1 and an empty CI all stay quiet.  `?=` lets an explicit
# VERBOSE on the command line or environment win in both directions.
VERBOSE ?= $(if $(filter true,$(CI)),1,0)

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
# Three Bazel lanes plus one lock diff is the whole gate: `bazel test --config lint //...`
# runs every test (Python, Rust, Starlark) and `bazel build --config lint //...` runs every
# linter, so a step that duplicates either belongs in the build graph instead of here.  Both
# root-workspace lanes run under the SAME configuration on purpose: alternating
# configurations mid-gate discards Bazel's in-memory analysis cache, which cost this gate
# tens of seconds on every hot run.
CHECK_STEPS := bazel-toolchain-guard bazel-test bazel-lint bazel-consumer-check \
               check-bazel-locks

# The heartbeat/timing echoes sit outside the VERBOSE branch: both modes report which step
# is running and how long it took, giving step-granular timing without instrumentation.  A
# failing step reports its wall time too — "the gate failed and it took forever" is the case
# where the number matters most.
#
# The per-step notes exist because the step NAMES no longer partition the work: bazel-test's
# invocation builds the lint surface as well, which makes bazel-lint's time a cache-hit
# confirmation rather than the cost of linting.  Without the notes the timing surface reads as
# "lint is free", pointing the next person at the wrong lane.
check-common:
	@steps="$(CHECK_STEPS)"; gate_start=$$(date +%s); \
	for step in $$steps; do \
	    case "$$step" in \
	        bazel-test) note=" [builds the lint surface too: same --config lint configuration]";; \
	        bazel-lint) note=" [same-configuration cache-hit confirmation; lint's cost is in bazel-test]";; \
	        *) note="";; \
	    esac; \
	    echo "check-common: running $$step$$note"; \
	    step_start=$$(date +%s); \
	    if [ "$(VERBOSE)" = "1" ]; then \
	        $(MAKE) $$step || { echo "FAILED: $$step after $$(( $$(date +%s) - step_start ))s (gate ran $$(( $$(date +%s) - gate_start ))s)"; exit 1; }; \
	    else \
	        tmpfile=$$(mktemp); \
	        if ! $(MAKE) $$step >"$$tmpfile" 2>&1; then \
	            echo "FAILED: $$step after $$(( $$(date +%s) - step_start ))s (gate ran $$(( $$(date +%s) - gate_start ))s)"; \
	            cat "$$tmpfile"; \
	            rm -f "$$tmpfile"; \
	            exit 1; \
	        fi; \
	        rm -f "$$tmpfile"; \
	    fi; \
	    echo "check-common: $$step passed in $$(( $$(date +%s) - step_start ))s$$note"; \
	done; \
	echo "check-common: all steps passed in $$(( $$(date +%s) - gate_start ))s ($(CHECK_STEPS))"

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
# both of its feature flavors, so `bazel test --config lint //...` compiles and runs them and
# the rules_rust clippy aspect it carries lints them.  Feature
# carve-outs are named targets: //crates/fltk-ast-core:no_features_test (every feature off,
# the only build compiling the `cfg(not(feature = "indexmap"))` arms), and
# //crates/fltk-cst-core:python_test (the `python` feature set).  The cquery guard in
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
#
# The pyo3 assertion is ONE cquery over the union of the derived targets, not one per
# target: `deps(set(a b c))` is `deps(a) ∪ deps(b) ∪ deps(c)`, so the property is the same
# and a cquery costs ~6s even fully hot.  On a hit the per-target loop attributes the
# failure; the gate fails unconditionally after it (including when the loop finds nothing —
# a union/per-target disagreement is itself a bug).
#
# The positive control is TWO facts, because a negative assertion over a graph that is not
# what you think it is passes vacuously:
#   - the union cquery's output reaches fltk-cst-core:no_python, which is what proves the
#     cquery itself ran and printed a real graph rather than nothing;
#   - EVERY derived target reaches it, which a union-level control cannot prove: over a
#     union, one member reaching the
#     runtime crates satisfies the control for all the others, so a target that stopped
#     reaching them at all (retargeted, stubbed, aliased somewhere harmless) would go on
#     passing "no pyo3" while proving nothing about itself.
# The second is `rdeps(set($labels), X)`, which names every member on a path to X.  It runs
# as a loading-phase `bazel query` (~2s) rather than a cquery (~25s here, reverse-dep
# inversion over the whole configured graph): "this target still reaches the runtime crates"
# is a structural fact about the unconfigured graph, where `query` unions every select()
# branch.
#
# Residual, accepted: no per-target CONFIGURED fact is asserted anywhere.  A target whose edge
# to the runtime crates sits in a select() branch the gate's configuration does not take passes
# the unconfigured control while contributing nothing to the union, whose own control the other
# members satisfy — so that one target's pyo3 assertion is vacuous again.  Buying the fact back
# costs a cquery per target, which is the 53s this guard was batched to remove.
#
# TODO(pyo3-guard-shared-helper): this block and its twin in bazel-consumer-check are
# near-duplicate shell, and the attribution arm of each runs only on a red gate, so a
# divergence introduced there surfaces on the one day it must not be wrong.
#
# Every configured invocation here carries --config lint, matching bazel-test and bazel-lint:
# a different configuration mid-gate discards the analysis cache.  Plain `bazel query` is
# exempt — query is loading-phase only.
#
# That narrows what the pyo3 assertion states, deliberately: it holds at --//bzl:lint=true, not
# at the default configuration a downstream consumer builds.  A pyo3 edge behind a select() on
# the lint setting would therefore be invisible here.  No such select exists on a Rust dep
# today, and a second union cquery at the default configuration would cost ~6s plus the
# config-switch penalty this lane's uniform configuration exists to avoid;
# TODO(pyo3-guard-shared-helper) is where restoring the default-config fact belongs.
bazel-test: bazel-toolchain-guard
	bazel test --config lint //...
	@set -e; \
	err="$$(mktemp)"; trap 'rm -f "$$err"' EXIT; \
	labels="$$(bazel query 'attr(name, "^no_python$$", //...) union kind("rust_binary rule", //...) union set(//tests:rust_gate_lib)' 2>"$$err")" \
	    || { echo "FAIL: bazel-test broken: query for pyo3-free targets failed"; cat "$$err"; exit 1; }; \
	test -n "$$labels" || { echo "FAIL: bazel-test broken: no pyo3-free targets found"; exit 1; }; \
	reaching="$$(bazel query "rdeps(set($$(echo $$labels)), //crates/fltk-cst-core:no_python)" 2>"$$err")" \
	    || { echo "FAIL: bazel-test broken: rdeps query for the positive control failed"; cat "$$err"; exit 1; }; \
	for target in $$labels; do \
	    echo "$$reaching" | grep -qxF "$$target" \
	        || { echo "FAIL: bazel-test broken: $$target does not reach fltk-cst-core:no_python, so its pyo3 assertion proves nothing"; cat "$$err"; exit 1; }; \
	done; \
	graph="$$(bazel cquery --config lint "deps(set($$(echo $$labels)))" 2>"$$err")" \
	    || { echo "FAIL: bazel-test broken: union cquery over the pyo3-free targets failed"; cat "$$err"; exit 1; }; \
	echo "$$graph" | grep -q 'fltk-cst-core:no_python' \
	    || { echo "FAIL: bazel-test broken: union cquery output lacks fltk-cst-core:no_python"; cat "$$err"; exit 1; }; \
	if echo "$$graph" | grep -qi pyo3; then \
	    echo "FAIL: pyo3 present in the union of the pyo3-free Bazel graphs; attributing per target:"; \
	    for target in $$labels; do \
	        one="$$(bazel cquery --config lint "deps($$target)" 2>"$$err")" \
	            || { echo "  cquery for $$target failed"; cat "$$err"; continue; }; \
	        ! echo "$$one" | grep -qi pyo3 || echo "  pyo3 present in the $$target Bazel graph"; \
	    done; \
	    exit 1; \
	fi; \
	echo "bazel-test: pyo3 absent from every derived pyo3-free target"
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
#
# Hot after bazel-test this is a cache-hit confirmation (same --config lint configuration).
# It stays: it keeps the lint surface addressable on its own (`make bazel-lint`) and is the
# backstop if `test` ever stops covering an output group the `build` form does.
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
# assertion vacuously.  All three targets go into one union cquery (same `deps(set(...))`
# equivalence as in bazel-test), with the per-target loop kept for failure attribution, and
# the control stays per target through one loading-phase `rdeps(set(...), X)` query — over a
# union it would be one fact, and a consumer target that stopped reaching fltk's runtime
# crates at all would pass the negative assertion vacuously.  Same accepted residual as the
# root lane: `query` unions every select() branch, so a target reaching the runtime crates only
# through an untaken branch still passes its own control.
#
# TODO(pyo3-guard-shared-helper): near-duplicate of the guard in bazel-test.
#
# The second cquery step is the serde-injection twin: //:consumer_serde must be on the consumer
# module's own hub serde and on no other, which is what proves the
# //crates/fltk-serde-core:serde flag reaches fltk-serde-core.  Unlike the pyo3 assertion this
# one has a build-time backstop (a mixed graph does not compile), so it is here to name the
# failure rather than to be the only witness of it.  It stays on //:consumer_serde's own graph
# rather than riding the union above: "the serde target links the consumer hub's serde" asserted
# over a union is satisfiable by any member, which is a weaker claim than the one intended.
#
# TODO(consumer-serde-single-traversal): //:consumer_serde's graph is walked twice per run,
# once inside the union above and once here.
#
# cquery's stderr goes to a file rather than /dev/null so the ordinary progress output stays
# out of a passing run while the reason for a failing one (analysis error, renamed label,
# stale crate_universe repos wanting CARGO_BAZEL_REPIN) is printed with the failure — the
# gate has to be diagnosable from a CI log alone.
bazel-consumer-check: bazel-toolchain-guard
	cd tests/bazel_consumer && bazel test //...
	@set -e; cd tests/bazel_consumer; \
	err="$$(mktemp)"; trap 'rm -f "$$err"' EXIT; \
	targets="//:consumer_ast //:consumer_fmt_bin //:consumer_serde"; \
	reaching="$$(bazel query "rdeps(set($$targets), @fltk//crates/fltk-cst-core:no_python)" 2>"$$err")" \
	    || { echo "FAIL: bazel-consumer-check broken: rdeps query for the positive control failed"; cat "$$err"; exit 1; }; \
	for target in $$targets; do \
	    echo "$$reaching" | grep -qxF "$$target" \
	        || { echo "FAIL: bazel-consumer-check broken: $$target does not reach fltk-cst-core:no_python, so its pyo3 assertion proves nothing"; cat "$$err"; exit 1; }; \
	done; \
	graph="$$(bazel cquery "deps(set($$targets))" 2>"$$err")" \
	    || { echo "FAIL: bazel-consumer-check broken: union cquery over $$targets failed"; cat "$$err"; exit 1; }; \
	echo "$$graph" | grep -q 'fltk-cst-core:no_python' \
	    || { echo "FAIL: bazel-consumer-check broken: union cquery output lacks fltk-cst-core:no_python"; cat "$$err"; exit 1; }; \
	if echo "$$graph" | grep -qi pyo3; then \
	    echo "FAIL: pyo3 present in the union of the consumer Bazel graphs; attributing per target:"; \
	    for target in $$targets; do \
	        one="$$(bazel cquery "deps($$target)" 2>"$$err")" \
	            || { echo "  cquery for $$target failed"; cat "$$err"; continue; }; \
	        ! echo "$$one" | grep -qi pyo3 || echo "  pyo3 present in the $$target Bazel graph"; \
	    done; \
	    exit 1; \
	fi; \
	echo "bazel-consumer-check: pyo3 absent from $$targets"
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
