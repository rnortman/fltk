# Dispositions: requirements-requirements-reviewer

Source: `docs/workflow/2026-06-27-rust-fltkfmt/notes-requirements-requirements-reviewer.md`
Target: `docs/workflow/2026-06-27-rust-fltkfmt/requirements.md`

---

## requirements-1

- Disposition: Fixed
- Action: Replaced the paragraph at line 80 that enumerated three concrete reuse mechanisms (closure-taking library fn / proc-macro / copy template) with a shorter paragraph that states the constraint — the baked-at-generation-time architecture means the reuse boundary is between grammar-independent CLI scaffolding and grammar-specific parse/unparse calls — without suggesting specific design approaches. Section: "Where this is in tension with the codebase."
- Severity assessment: Low. The original enumeration could anchor the designer toward those three options rather than surveying the full solution space, but the refiner already disclaimed that the choice is a design decision, and the user themselves mentioned "macro or generic."
