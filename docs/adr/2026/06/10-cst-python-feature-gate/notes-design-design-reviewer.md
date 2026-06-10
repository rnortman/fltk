# Design review findings: cst-python-feature-gate

Style: concise, precise, no padding. Audience: smart LLM/human.
Scope: adversarial fact-check of `design.md` against `requirements.md`, `request.md`, `exploration.md`, and source at e6a9117.

Verified and accurate (not findings): span.rs structure/line claims (pymethods 204-433, coerce_source 194, error string at 196-198, `py_new`/`get_start`/`get_end` precedent, intersect-disjoint → `Span::unknown()` matching `terminalsrc.py:117-127`); generator line claims (`generate` 222, `_preamble` 244, `_register_classes_fn` 916); test-pin line ranges in `tests/test_gsm2tree_rs.py`; root/fixture Cargo.toml feature shapes and `default-features = false` deps; merge error message pinned by `tests/test_span.py:151,188` and `tests/test_rust_span.py:179,215`; PoC `ItemsChild` has Span + node variants (`src/cst_generated.rs:467-471`); maturin builds with default features (`pyproject.toml` `[tool.maturin] features` adds only `pyo3/extension-module`); `make gen-rust-cst GRAMMAR=... RS_OUT=...` parameterization exists (Makefile:69-70). The resolver-2 `-p` feature-isolation claim (§3) was re-verified empirically in a scratch workspace replicating the topology: `cargo tree -p spike` shows no optional dep despite a default-on sibling, and `cargo tree -p core --no-default-features` is clean. Requirements coverage is complete: all five behavior sections, all four open questions, and all verification gates map to design sections.

## design-1: §2.4/§2.7 — the out-of-tree guide does NOT "mirror the fixture"; its template has no `fltk-cst-core` dependency at all

Design §2.4: "**Out-of-tree consumers** (documented pattern in `docs/rust-cst-extension-guide.md:39-56` mirrors the fixture): on upgrading fltk-cst-core and regenerating, they must add the same feature block once."

False. The guide's Cargo.toml template (`docs/rust-cst-extension-guide.md:41-57`) lists exactly one dependency — `pyo3` — with no `fltk-cst-core` entry, and the guide states outright (line 30): "The generated file has no link-time dependency on FLTK's crate. It depends on PyO3 only." That is stale at HEAD (the generated preamble has imported `fltk_cst_core` since the preamble-helpers work — `gsm2tree_rs.py:246`), but it is what is published. The fixture crates (`tests/rust_cst_fixture/Cargo.toml:20`) do depend on `fltk-cst-core` with `default-features = false`; the documented out-of-tree pattern does not match them.

Consequence: §2.7 scopes the doc update as "updated Cargo.toml template (feature block from §2.4) + migration note" — adding only the feature block to a template with no `fltk-cst-core` dependency yields a template that still cannot compile generated code (`fltk-cst-core/python` in a feature list does not create the dependency edge; the `use fltk_cst_core::...` preamble is unresolvable). The migration story in §2.4/§3 and the breaking-change framing in Open question 1 are computed against the wrong consumer baseline: a guide-following consumer's migration is "add the dependency + the feature block," not "add the feature block once." Implementer following §2.7 ships a still-broken guide; user signs off on OQ1 with churn understated.

Fix: §2.7 must specify adding the `fltk-cst-core` dependency (path/version, `default-features = false`, plus forwarding feature) to the guide template and deleting/correcting the line-30 "depends on PyO3 only" claim; OQ1 should note the guide is already stale and the dependency addition is part of the consumer migration.

## design-2: §3 failure-mode enumeration misses the upgrade-without-regeneration path

§3 enumerates two out-of-tree failure modes, both predicated on regenerating: "consumer regenerates without declaring the feature" and "consumer declares `python` but forgets forwarding." A third, likely first-contact case is uncovered: a consumer upgrades `fltk-cst-core` but does **not** regenerate and does not touch their manifest. Per the documented pattern (`crates/fltk-cst-core/Cargo.toml:13` "Downstream crates depend with default-features = false"; both fixture manifests), their dep resolves the new default-on `python` feature **off**. Their committed, ungated, previously-generated `cst.rs` then fails: `use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject, Span}` — three of four symbols gated out of `lib.rs` — plus `Span` no longer a pyclass. Loud, but the diagnostics (unresolved imports inside generated code they didn't touch) don't point at the manifest fix, and neither enumerated failure mode nor the planned migration note covers it.

Consequence: the §2.7 migration note written from this design omits the scenario most existing consumers hit first (dependency upgrade precedes regeneration); requirements' "out-of-tree regeneration with current settings behaves identically by default" tension flagged in OQ1 is adjudicated by the user on an incomplete picture.

Fix: add the case to §3 and the migration note: on upgrading fltk-cst-core, add `features = ["python"]` (or the forwarding feature) to the dep before or independent of regenerating.

## design-3: §2.6 `check-no-pyo3` passes vacuously when `cargo tree` fails

```make
check-no-pyo3:
	@if cargo tree -p fltk-cst-spike --edges normal,build | grep -q pyo3; then \
	    echo "FAIL: ..."; exit 1; fi
```

In make's default `/bin/sh` pipeline, the `if` condition takes grep's exit status; a failing `cargo tree` (package renamed, manifest/lock error, future workspace restructure) produces empty stdout → grep no match → target succeeds. The one mechanical guarantee requirements §3 demands ("the check is automated, not eyeballed") and §5's rot-prevention rationale are defeated exactly in the rot scenario: the gate goes green when the tool it relies on breaks.

Consequence: a silent-pass gate; pyo3 reintroduction (or check bit-rot) ships through CI while the gate reports success.

Fix: capture output and check cargo's exit status separately, and/or add a positive control — assert the same output contains `fltk-cst-core` (proves the tree was actually produced). Optionally also run the literal requirements-§1 acceptance command (`cargo tree -p fltk-cst-core --no-default-features | grep pyo3` empty); the spike tree covers it transitively, but the design never states that mapping.
