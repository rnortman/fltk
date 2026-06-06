<!-- Concise. Precise. No fluff. -->

# Ship-gate dispositions — `_cst_const` removal

## Finding (user directive)

Label-compare sites in `fltk2gsm.py` still read `_cst_const.Items.Label.NO_WS` instead of the
clean `cst.Items.Label.NO_WS` form required as in-tree proof of AC10.

## Disposition: Fixed

**Root cause:** the original §2.5 wording in design.md (last bullet) explicitly suggested using
`_cst_const` for runtime constants and keeping `cst` for type-checker annotations only — but
the investigation in `cst-const-investigation.md` identified a clean alternative: import
`fltk_cst as cst` unconditionally, then let the `TYPE_CHECKING` block shadow it with the Protocol.

**Change applied** (`fltk/fegen/fltk2gsm.py`):

- Line 8: `from fltk.fegen import fltk_cst as cst` (unconditional, replaces `fltk_cst as _cst_const`)
- Line 11-12: `if TYPE_CHECKING: from fltk.fegen import fltk_cst_protocol as cst` (unchanged shadow
  for pyright; ruff does not flag the redefinition inside `TYPE_CHECKING` so no `noqa` needed)
- All `_cst_const.` occurrences (10 sites) replaced with `cst.` — label-compare sites now read
  `cst.Items.Label.NO_WS`, `cst.Disposition.Label.INCLUDE`, etc.

**Validation:**
- `uv run pyright fltk/fegen/fltk2gsm.py` → 0 errors, 0 warnings
- `make check` → all checks passed, 852 tests passed
- Existing test `test_fltk2gsm_does_not_import_protocol_at_runtime` continues to pass (runtime
  `cst` is `fltk_cst`, not `fltk_cst_protocol`; the test checks `sys.modules` after import and
  the protocol module is absent from the runtime namespace)
