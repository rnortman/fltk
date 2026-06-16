# User comments — fltk line/col design gate

1. Can we not fix the crate layout problem to avoid re-implementing pos_to_line_col? We can move that if we need to, but we should only have it in one place. This should be possible somehow.

2. Secondly, I want to expand scope a little: I want to track filenames so that a span can also tell you which file it's in. This clearly would go on TerminalSource/SourceText/SourceInner, not be stored redundantly on each span. The file name can be provided at the time TerminalSource/SourceText are constructed by the caller. It's optional through the whole pipeline (e.g. so dynamic source snippets with no file can be parsed). And then I want a single function that does what Clockwork's error formatter does: Prints the source line with a column indicator along with the error message. No reason every out-of-tree consumer should have to reimplement all of that.
