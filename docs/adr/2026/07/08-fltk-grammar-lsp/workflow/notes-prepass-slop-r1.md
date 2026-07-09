slop-1
File: fltk/lsp/test_dogfood.py:40-41 (new function `test_dogfood_committed_spec_defines_rule_config_name`)
Quote: `# The committed spec now carries \`def rule_name: type;\` inside the \`rule rule_config\` block, so a`
What's wrong: Changelog-style comment phrased relative to the diff ("now carries") rather than describing what the spec currently does.
Consequence: Reads as the author narrating their own edit rather than documenting the code; a reviewer skimming for LLM-authoring tells will flag it, and the "now" language will be stale/confusing once this commit is old history.
Suggested fix: State the invariant directly, e.g. "The spec defines \`def rule_name: type;\` inside \`rule rule_config\`, so a \`rule NAME { ... }\` heads the outline and its name is a find-references target."

slop-2
File: fltk/lsp/test_grammar_lsp.py:957-959 (`client` fixture teardown)
Quote: `with contextlib.suppress(Exception): await lsp_client.shutdown_session()`
What's wrong: Broad `Exception` suppression around session shutdown, matching the "swallowed error" pattern called out for review, even though this is test-teardown code.
Consequence: If shutdown starts failing for a real reason (e.g. server hang, protocol break), the test will pass silently with no signal — minor but worth a one-line comment justifying why any failure here is safe to ignore.
Suggested fix: Either narrow the caught exception type or add a short comment explaining why swallowing all exceptions during teardown is intentional/safe.

No other diff-visible issues (no narrative/self-explanatory comment sludge elsewhere, no obvious silent fallbacks in production code, no visible workarounds for existing bugs). The rest of the diff (BUILD.bazel target, grammar_cli.py, server_cli.py refactor into `serve`, VS Code extension, new .fltklsp/.fltkfmt sidecar files) reads as clean, intentional, and ready for review.
