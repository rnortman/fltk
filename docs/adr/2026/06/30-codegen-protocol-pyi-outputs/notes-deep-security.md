# Deep security review — codegen protocol + .pyi outputs

Commit reviewed: 19348b3a8900ae0eaf883f3f7b3531b029d9a814 (base f0edfd757571310a83ac08a361c5af8ec4028001)

No findings.

## Scope considered

The diff adds opt-in flags to a developer-facing code-generation CLI (`generate
--protocol`; `gen-rust-cst`/`gen-rust-unparser` `--protocol-output`,
`--init-pyi-output`, `--extension-name`, `--submodules`), a new
`render_stub_package_init` helper, `RustCstGenerator.generate_protocol`, and
Bazel rule attrs (`generate_parser.protocol`,
`generate_rust_parser.protocol_module` / `generate_protocol`).

## Trust-boundary analysis (why no findings)

- No untrusted input crosses a boundary. All inputs (grammar path, output paths,
  module/extension/submodule names) are build configuration supplied by the same
  developer invoking the generator. No network, request, or external-data path is
  involved.
- Injection into generated output is guarded. `render_stub_package_init`
  interpolates `extension_name` and each `--submodules` entry into comment-only
  `.pyi` text, but every value is validated by `_validate_rust_ident` against the
  anchored regex `^[A-Za-z_][A-Za-z0-9_]*$` (gsm2lib_rs.py:17,20-24,47-52). Anchoring
  excludes newlines/special chars, so comment-injection or escaping the comment is
  not possible. Empty submodule list is rejected.
- `_render_init_pyi` validates up front (before grammar parse and any file open),
  so a malformed marker never reaches disk (genparser.py:_render_init_pyi).
- `--protocol-module` continues to be validated by the pre-existing
  `_validate_protocol_module`.
- `generate_protocol` constructs a `CstGenerator` with a fixed placeholder
  `py_module=pyreg.Module(["_protocol"])`; no user data is interpolated into code,
  and output is `ast.unparse` of a built AST (gsm2tree_rs.py:generate_protocol).
- Arbitrary output-path writes (`_write_output_file`, `*.open("w")`) are the
  intended function of a codegen tool and are developer-controlled; not a path-
  traversal boundary.
- Bazel changes pass all values via `ctx.actions.args()` / `args.add()` (argv
  list, no shell), and `--extension-name` is the rule `name`. No shell injection.

No secrets, crypto, deserialization, SSRF, auth, redirect, or timing surface is
touched by this diff.
