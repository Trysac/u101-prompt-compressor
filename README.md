# prompt-compressor

Long prompts built from retrieved context, chat history, and boilerplate cost money and dilute the instructions that matter. Ad hoc trimming either cuts an instruction or an identifier the model needed, or saves nothing measurable. This library compresses a prompt with a fixed, explainable set of rules that never touch protected spans and reports exactly how many tokens each rule saved.

## Installation

```bash
pip install trysac-prompt-compressor
```

## Usage

```python
from prompt_compressor import compress

text = "Run tests in order to ship. In order to win, play."
res = compress(text, target_ratio=1.0)
print(res.text)  # "Run tests to ship. To win, play."
print(f"Saved: {res.saved_ratio:.1%}")
```

## API Summary

- `compress(text, *, target_ratio=0.6, counter=word_count, keep=(), max_input_chars=500_000) -> Compression`: Main entry point. Returns `Compression` dataclass containing result text, token stats, steps, and protected spans.
- `find_protected(text, keep=()) -> tuple[str, ...]`: Returns identified protected strings.
- `word_count(text) -> int`: Simple whitespace-based counter.
- `CompressorError`: Base class. Codes: `input_too_large`, `invalid_ratio`, `invalid_counter`, `invalid_pattern`.
- `InputTooLargeError`: Raised if input exceeds `max_input_chars` (default 500k).

## Why not LLMLingua / Best-known alternatives?

This library is fully deterministic, explainable, and requires no GPU or LLM interaction. It is safe for instructions because it guarantees zero modification of protected code blocks or instruction lines.

## Security

See [docs/SECURITY.md](docs/SECURITY.md).
