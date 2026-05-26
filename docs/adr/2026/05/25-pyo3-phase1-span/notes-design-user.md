# User notes on design (verbatim)

1. OK, this has completely misunderstood the assignment. The idea is to end up with *two swappable backends* with substantially similar APIs. One Python, one Rust. This design replaces Python with Rust for Span. We must retain a pure-python version of this. The pure-python version can be updated to have the new/better API as part of this, or we can have the new API only on the Rust version for now.

2. I'd suggest that we create a `Span` protocol class, and anybody that wants to write code compatible with both backends should use that protocol for all type annotations. And `isinstance` is typically a code smell anyway for something like this, but we could provide a type alias that is a union of the rust type and the python type for when you need to do that.

3. Another comment: `span.ensure_text()` should be added as a version of `span.text()` that throws if not source-backed instead of returning None. Or the designer can pick a better name since "ensure_text" is actually a really shitty name; is there a better conversion for this? The point of this method is to reduce the `if text is None: raise SomeError(...)` boilerplate that you inevitably have with an api that returns `| None`.
