# Reuse review notes

## reuse-1

- File: `tests/test_span_protocol.py:59-99`
- What's duplicated: the four-line "save `fltk._native` from `sys.modules`, install a fake,
  run the reload under `pytest.raises`/`warnings.catch_warnings`, then in `finally` pop, restore
  the saved module, and re-reload the real module" dance is repeated verbatim in
  `test_span_selector_broken_native_propagates` (lines 59-70), `test_span_protocol_broken_native_propagates`
  (72-83), and `test_span_protocol_absent_native_falls_back_silently` (85-99) — three new
  copies of the exact save/restore/reload boilerplate already present in the pre-existing
  `test_reload_without_native_emits_no_warning` (lines 23-40). The design's own test plan
  even calls this a "shared fixture/helper" but only the `_BrokenNative` fake class ended up
  shared; the sys.modules save/restore/reload ceremony was copy-pasted instead of being
  factored into a fixture or context manager.
- Existing function/utility: none in-repo generalizes this; the closest sibling is the
  pre-existing `test_reload_without_native_emits_no_warning` (`tests/test_span_protocol.py:23-40`),
  which the new tests copy rather than call through a shared helper.
- Consequence: the module-name string, the pop-then-`sys.modules.update(saved)`-then-reload
  restoration order, and the "must restore the saved object, never delete-and-reimport"
  invariant (called out in the design doc as required because of the PyO3 double-init panic)
  now live in four separate places. A future edit to the restoration logic (e.g. adding
  `fegen_rust_cst` to the set of modules that need saving, or fixing a subtle restore-order
  bug) requires updating all four call sites in lockstep; missing one reintroduces the
  double-init panic risk this exact code was written to avoid, and nothing enforces the
  four copies stay in sync as the file grows.
