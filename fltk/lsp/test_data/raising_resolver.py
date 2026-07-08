"""A test-only resolver whose ``resolve`` always raises.

Loaded by ``test_server_crossfile`` via ``--resolver`` to pin the server's degradation policy: a
buggy resolver must downgrade read-only navigation to the same-file answer and fail the rename
guard closed, never break the server. Not a real resolver -- it resolves nothing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fltk.lsp.resolver import CrossFileResolution, ResolvedDocument, ResolverHost


def create_resolver() -> RaisingResolver:
    return RaisingResolver()


class RaisingResolver:
    file_suffixes = (".gear",)

    def resolve(self, doc: ResolvedDocument, host: ResolverHost) -> CrossFileResolution:  # noqa: ARG002
        msg = "synthetic resolver failure"
        raise RuntimeError(msg)
