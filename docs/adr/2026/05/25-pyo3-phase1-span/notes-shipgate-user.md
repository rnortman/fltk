# User notes at ship-gate (verbatim)

1. The protocol has no docstrings, and neither do the implementations in Python nor Rust. This is very poor hygiene. Please fix.

2. intersect() should return UnknownSpan sentinel on empty intersection instead of `None`, across the protocol and both implementations.

3. Remove `struct Ping` from the Rust; it was only there so the mod wouldn't be empty.
