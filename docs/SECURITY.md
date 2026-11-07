# Security notes

## Threat model

### Defended

- **Logic injection/Exec**: The library contains no `eval` or `exec`. It is a pure logic implementation of regex-based transformations.
- **Input validation**: Inputs exceeding 500,000 characters are rejected with `InputTooLargeError`. Regex patterns in `keep` are limited to 20 patterns, each max 200 characters to prevent ReDoS.
- **Dependency security**: No runtime dependencies. The code uses standard library features only.

### Not defended

- **Malicious caller input**: The library trusts the input string provided by the caller. If the input string is crafted to exploit regex backtracking in complex patterns, performance may degrade, although constraints on input size and pattern length mitigate significant abuse.

## Publishing

Releases are published to PyPI using secure, token-less OIDC publishing.
