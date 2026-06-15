# User design-gate directive — regex-grammar-spike

One note: We should not hard-code a path to the clockwork.fltkg in anything we commit to the repo. We can provide the path as a CLI arg. And really nothing about this is clockwork-specific; we should be able to use the same script to extract regexes from any grammar file and test against them.
