"""Assertions shared by the CST mutator suites."""

from __future__ import annotations

import typing

import pytest


def assert_rejected(node: typing.Any, call: typing.Callable[[], object], rejected: object) -> None:
    """``call`` raises the rejected-child ``TypeError`` naming ``rejected`` and leaves ``node`` as it was.

    The message is the template both backends emit for a child a write refuses:
    ``<Class>: unsupported child type <module>.<qualname>``.
    """
    before = list(node.children)
    with pytest.raises(TypeError) as exc_info:
        call()
    rejected_type = type(rejected)
    expected = f"{type(node).__name__}: unsupported child type {rejected_type.__module__}.{rejected_type.__qualname__}"
    assert str(exc_info.value) == expected
    assert list(node.children) == before
