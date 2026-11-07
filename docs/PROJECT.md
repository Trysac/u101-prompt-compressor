# Project record

## Objective

Provide deterministic prompt compression that keeps instructions, code, and entities byte-exact, removes filler and redundant context, and reports token savings per rule.

## Scope

- Public API: `compress`, `find_protected`, `word_count` functions and associated data classes.
- Deterministic compression rules: whitespace, duplicate lines, filler replacement, and sentence dropping.
- CLI interface: `python -m prompt_compressor`.
- Type safety: `py.typed` compliant.

## Out of scope

- LLM-based or embedding-based compression (e.g., LLMLingua).
- Language-specific filler tables beyond English.
- Built-in tokenizer integration (only supports pluggable counters).

## Effort metrics

| Metric | Value |
|---|---|
| Tokens (input / output) | 811871 / 15562 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.2153 |

## Factory run u101 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | gemini-3.8-flash | yes | 4386 | 10172 | 0 | 0 | 0.0207 |
| fix-1 | gemini-3.8-flash | no | 33076 | 1341 | 0 | 72426 | 0.0353 |
| fix-2 | gemini-3.8-flash | no | 76375 | 2122 | 0 | 295594 | 0.0874 |
| fix-3 | gemini-3.8-flash | no | 20928 | 485 | 0 | 14917 | 0.0186 |
| audit | gemini-3.1-flash-lite | no | 49520 | 239 | 0 | 99579 | 0.0152 |
| docs | gemini-3.1-flash-lite | no | 145070 | 1203 | 0 | 0 | 0.0381 |

Total: $0.2153. Prices: Anthropic list prices.
