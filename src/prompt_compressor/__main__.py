"""CLI interface for prompt_compressor."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from prompt_compressor import CompressorError, compress


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic prompt compressor")
    parser.add_argument("file", nargs="?", help="Input prompt file (reads stdin if omitted)")
    parser.add_argument(
        "--ratio", type=float, default=0.6, help="Target token ratio (0.0 < ratio <= 1.0)"
    )
    parser.add_argument(
        "--keep", action="append", default=[], help="Regex patterns for entities to keep"
    )
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else 2

    try:
        if args.file:
            with open(args.file, encoding="utf-8") as f:
                text = f.read()
        else:
            text = sys.stdin.read()
    except OSError as err:
        sys.stderr.write(f"Error reading file: {err}\n")
        return 2

    try:
        result = compress(text, target_ratio=args.ratio, keep=args.keep)
    except CompressorError as err:
        sys.stderr.write(f"Error: {err}\n")
        return 1
    except Exception as err:
        sys.stderr.write(f"Unexpected error: {err}\n")
        return 2

    saved_tokens = result.original_tokens - result.compressed_tokens
    saved_pct = result.saved_ratio * 100.0
    sys.stderr.write(
        f"saved {saved_tokens} of {result.original_tokens} tokens ({saved_pct:.1f}%)\n"
    )

    if args.json:
        sys.stdout.write(json.dumps(asdict(result), indent=2) + "\n")
    else:
        sys.stdout.write(result.text + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
