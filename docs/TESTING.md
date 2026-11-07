# Testing

## Running

```sh
uv run pytest --cov=prompt_compressor
uv run python scripts/check.py
```

## Test Coverage

- `tests/test_prompt_compressor.py` contains acceptance tests for the compression pipeline:
    - `test_acceptance_whitespace`: Verifies whitespace collapse rules.
    - `test_acceptance_duplicate_line`: Verifies removal of identical lines.
    - `test_acceptance_filler`: Verifies idiomatic filler replacements.
    - `test_acceptance_protected_instruction_and_entity`: Verifies instructions and entities are protected correctly.
    - `test_acceptance_fenced_block_and_unachievable_target`: Verifies fenced block handling and target_met logic.
- Tests also cover exception handling for invalid ratios, invalid counters, and input size limits.
