import fltk._native as native


def test_module_importable():
    assert native.Span is not None
    assert native.UnknownSpan is not None
    assert native.SourceText is not None
