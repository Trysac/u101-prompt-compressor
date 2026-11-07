# Architecture

## Overview
`prompt_compressor` applies sequential, explainable compression stages to prompts while protecting sensitive instructions, entities, and code blocks.

### Pipeline Stages
1. **Segmentation**: Fenced code blocks (` ``` `) are separated from prose lines. Unterminated fences treat remaining lines as code to avoid syntax alteration.
2. **Protection Tagging**: Lines starting with instruction keywords (`you must`, `always`, `never`, etc., optionally prefixed by bullets), and sentences matching entity patterns (URLs, emails, numbers, quoted strings, custom keep patterns) are marked protected.
3. **Whitespace Normalization**: Space/tab runs are collapsed to a single space; 3+ newlines are collapsed to 2.
4. **Duplicate Line Removal**: Identical prose lines are removed after whitespace normalization.
5. **Filler Replacement**: Idiomatic filler phrases (e.g., `in order to` -> `to`) are replaced outside protected spans with case preservation.
6. **Sentence Dropping**: Unprotected sentences are scored by overlap with protected vocabulary and dropped lowest-score first until `target_ratio` is reached.
