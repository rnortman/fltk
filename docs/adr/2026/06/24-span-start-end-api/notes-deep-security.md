# Deep Security Review — span-start-end-api

Commit reviewed: 1144c7f615093b087550946f4dbe79653821b852 (base 1f75363fd198f3264aa9ade30a9455d0cabc521d)

Files changed:
- fltk/fegen/pyrt/span_protocol.py
- tests/test_span_protocol.py

No findings.

The change adds `.start`/`.end` `@property` declarations to a `typing.Protocol`
(`SpanProtocol`), revises a docstring, and updates a test class. A Protocol
declaration carries no runtime behavior beyond `runtime_checkable` structural
membership checks; the property bodies are `...`. No trust boundary is crossed:
no untrusted input is parsed, no injection sink, no filesystem/network/command/
deserialization operation, no auth/authz path, no secrets, and no crypto or
randomness. The exposed `start`/`end` are integer index accessors that already
existed on both concrete backends; surfacing them in the protocol type does not
introduce any new data flow or capability. The test additions are read-only
assertions over span objects.
