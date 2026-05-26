import pytest

native = pytest.importorskip("fltk._native", reason="Rust extension not built — run `maturin develop`")


def test_ping():
    assert native.Ping().pong() == "pong"
