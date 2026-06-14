Commit reviewed: 25bbfef (fltk), ea34388 (clockwork)

test-1
File: fltk/fegen/test_genparser.py — test_gen_rust_lib_invalid_module_name_empty and test_gen_rust_lib_invalid_module_name_has_space
What's wrong: test_gen_rust_lib_invalid_module_name_empty checks only that exit_code != 0 and that no output file was created. It does not verify the error message names the bad value (even an empty string). test_gen_rust_lib_invalid_module_name_has_space checks only exit_code != 0 — it neither checks the error message nor asserts the output file was not created. The design §4 specifies "exits non-zero with a message naming the problem"; test_gen_rust_lib_invalid_module_name_starts_with_digit and test_gen_rust_lib_invalid_module_name_has_hyphen do assert the bad value appears in output.output, but these two tests do not.
Consequence: A regression where the CLI exits 1 silently (no message naming the offending value) would not be caught by these two tests.
Fix: Add `assert "module_name" in result.output or "''" in result.output` (or similar) to the empty test, and add `assert "has space" in result.output` and `assert not output_rs.exists()` to the has-space test, matching the pattern established by the digit and hyphen tests.

test-2
File: fltk/fegen/test_genparser.py — gen-rust-lib CLI tests
What's wrong: There is no test for invoking gen-rust-lib with --module-name omitted entirely. The design §4 names "Missing/empty --module-name exits non-zero with a message naming the problem" as a CLI test requirement. Omitting the flag is a distinct code path from passing an empty string: typer handles missing required options itself (exit code 2, typer-generated message), confirmed by manual inspection (exit 2 with "Missing option '--module-name'"). The "missing" case is untested.
Consequence: If the option were accidentally given a default value (making it optional and silently accepting blank), existing tests would not catch the regression.
Fix: Add a test that invokes `["gen-rust-lib", str(output_rs)]` (no --module-name) and asserts exit_code != 0 (or == 2).

test-3
File: fltk/fegen/gsm2lib_rs.py — LibSpec.cfg_python_gate field
What's wrong: cfg_python_gate is declared on LibSpec (line 62) and included in the docstring scope, but the generate() method in RustLibGenerator never reads it (confirmed by grep: the word "cfg_python_gate" appears only in the dataclass definition). No test verifies that setting cfg_python_gate=True produces any particular output, nor that the standard output is free of #[cfg(feature="python")] gates. If a future contributor adds cfg_python_gate support to generate() incorrectly — or if they pass cfg_python_gate=True expecting it to work and it silently does nothing — no test catches either failure.
Consequence: The field is effectively dead: it accepts a True value without effect. Any test that would cover this behavior is absent, so either the documented contract ("emit #[cfg(feature = python)] gates") is unimplemented and undetected, or the field is purely reserved for future use with no coverage obligation — but the latter should be explicit.
Fix: Either (a) add a test asserting that cfg_python_gate=True raises NotImplementedError or is otherwise gated, making the unimplemented state explicit; or (b) remove the field from the dataclass until it is implemented (at which point tests should be added as part of that work).

test-4
File: fltk/fegen/test_gsm2lib_rs.py — native_spec() tests
What's wrong: The native_spec tests each call RustLibGenerator(native_spec()).generate() independently in a separate test function. This is not a quality problem per se, but the tests do not verify the order of mod declarations relative to each other: the design specifies mod span; before mod cst_generated; before mod cst_fegen;, and the submodule registration order is similarly significant (poc_cst before fegen_cst). Each test only checks for the presence of individual strings, not their relative order. A transposition of mod declarations or registration calls would compile (Rust does not require declaration order) but would change observable behavior if init order matters, and would not be caught.
Consequence: If the generator accidentally swapped the two cst mod declarations or the two register_submodule calls, all existing tests would still pass.
Fix: Add one test that checks relative ordering, e.g. `assert src.index("mod cst_generated;") < src.index("mod cst_fegen;")` and `assert src.index('"poc_cst"') < src.index('"fegen_cst"')`. A single combined ordering test avoids redundancy.
