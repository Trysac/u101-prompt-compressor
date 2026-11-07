# prompt-compressor

[![PyPI version](https://img.shields.io/pypi/v/trysac-prompt-compressor)](https://pypi.org/project/trysac-prompt-compressor/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-prompt-compressor)](LICENSE)
[![CI](https://github.com/Trysac/u101-prompt-compressor/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u101-prompt-compressor/actions/workflows/ci.yml)

Deterministic prompt compression that keeps instructions, code and entities byte-exact, removes filler and redundant context, and reports token savings per rule

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-prompt-compressor
# or
uv add trysac-prompt-compressor
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import prompt_compressor

# normalize() trims surrounding whitespace and lower-cases the text.
print(prompt_compressor.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    prompt_compressor.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
