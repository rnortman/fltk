No findings.

The diff adds `start`/`end` as `@property` entries on `SpanProtocol` and flips one test class.
The pure-Python `Span` dataclass in `terminalsrc.py` has always exposed `start` and `end` as
dataclass fields — no new implementation is added, only a protocol declaration.  No inline
hand-rolled reimplementation of these accessors appears anywhere in the changed files.

Pre-existing note (not a finding on this diff): `gsm2parser.py` lines 541 and 749 contain
comments that say `result.span.start` is "unavailable on the Rust backend" and work around
it by saving the initial `pos` in a local `_span_start` variable.  Now that `SpanProtocol`
formally declares `start`/`end`, those workarounds are stale in intent (though not incorrect
in behaviour).  Unwinding them is a separate, elective cleanup; they are not a product of
this diff and fall outside the scope of a reuse review.
