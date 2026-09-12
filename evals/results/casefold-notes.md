# Casefold evaluation

The original prompt was: "Normalize surrounding whitespace and case."

The first live run was rejected by the withheld tests.
The agent generated text.strip().lower(), which does not convert
"Straße" to "strasse". Its smoke and regression tests passed.

Recorded model usage estimate: $0.00144164, excluding sandbox charges.
The original result is preserved in casefold-live.json.

The prompt was clarified to explicitly require Unicode case folding.
The acceptance tests and reference implementation were unchanged.
Any subsequent run uses a revised prompt and must be reported separately.
