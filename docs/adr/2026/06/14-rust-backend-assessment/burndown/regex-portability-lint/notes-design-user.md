# User design-gate directive — regex-portability-lint

For regex-portability: Why not create an FLTK *grammar* of the supported regexes, and actually parse the regex using a generated FLTK parser. Otherwise we're basically building a janky (and probably unreliable) regex-based parser inside a parser generation library, which seems like we don't trust our own product. Send that idea back to a designer to think about.
