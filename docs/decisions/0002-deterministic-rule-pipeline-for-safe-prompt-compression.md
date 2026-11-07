# Deterministic Rule Pipeline for Safe Prompt Compression

Status: accepted (generated, pending human review)

## Context

Prompt compression methods that use neural models (e.g. LLMLingua) require GPU resources and may inadvertently alter precise instructions, identifiers or code syntax.

## Decision

Implement a deterministic, stdlib-only sequential rule pipeline that isolates fenced code blocks, tags instruction lines and entities as immutable, and applies bounded whitespace, deduplication, filler reduction, and scored sentence pruning.

## Consequences

Compression is 100% deterministic, transparent, and safe for instructions and code blocks, without external dependencies or GPU requirements.
