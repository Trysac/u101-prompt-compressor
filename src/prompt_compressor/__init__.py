"""Deterministic prompt compression library."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

logging.getLogger(__name__).addHandler(logging.NullHandler())

__version__ = "0.1.0"
__all__ = [
    "Compression",
    "CompressorError",
    "InputTooLargeError",
    "Rule",
    "Step",
    "__version__",
    "compress",
    "find_protected",
    "word_count",
]

Rule = Literal["whitespace", "duplicate_line", "filler", "drop_sentence"]


class CompressorError(ValueError):
    """Base error class for prompt compressor exceptions."""

    def __init__(
        self,
        code: Literal["input_too_large", "invalid_ratio", "invalid_counter", "invalid_pattern"],
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code


class InputTooLargeError(CompressorError):
    """Raised when input exceeds the configured character limit."""

    def __init__(self, message: str) -> None:
        super().__init__("input_too_large", message)


@dataclass(frozen=True)
class Step:
    """Represents a compression rule execution count."""

    rule: Rule
    count: int


@dataclass(frozen=True)
class Compression:
    """Result of prompt compression."""

    text: str
    original_tokens: int
    compressed_tokens: int
    saved_ratio: float
    target_met: bool
    steps: tuple[Step, ...]
    protected: tuple[str, ...]


def word_count(text: str) -> int:
    """Default token counter using whitespace splitting."""
    return len(text.split())


_INSTRUCTION_PREFIXES: tuple[str, ...] = (
    "you must",
    "you should",
    "do not",
    "never",
    "always",
    "must",
    "only",
    "return",
    "respond",
    "output",
    "answer",
    "format",
)

_BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s*")

# Entity regexes
_NUMBER_RE = re.compile(r"\b\d[\d.,:/-]*\b")
_URL_RE = re.compile(r"https?://\S+")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_QUOTED_RE = re.compile(r'"[^"]*"')
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[a-zA-Z]{4,}")

_FILLER_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("in order to", "to"),
    ("due to the fact that", "because"),
    ("at this point in time", "now"),
    ("in the event that", "if"),
    ("for the purpose of", "for"),
    ("please note that ", ""),
    ("it is important to note that ", ""),
    ("basically, ", ""),
)


def _clean_url_match(match_str: str) -> str:
    return match_str.rstrip(".,;:!?)\"'")


def _is_protected_instruction_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    after_bullet = _BULLET_RE.sub("", stripped)
    lower = after_bullet.lower()
    for prefix in _INSTRUCTION_PREFIXES:
        if (
            lower == prefix
            or lower.startswith(prefix + " ")
            or lower.startswith(prefix + ":")
            or lower.startswith(prefix + ",")
        ):
            return True
    return False


def _line_has_entity(sentence: str, compiled_keeps: list[re.Pattern[str]]) -> bool:
    if _NUMBER_RE.search(sentence):
        return True
    m = _URL_RE.search(sentence)
    if m and _clean_url_match(m.group(0)):
        return True
    if _EMAIL_RE.search(sentence):
        return True
    if _QUOTED_RE.search(sentence):
        return True
    return any(kp.search(sentence) for kp in compiled_keeps)


def _validate_keeps(keep: Sequence[str]) -> list[re.Pattern[str]]:
    if len(keep) > 20:
        raise CompressorError("invalid_pattern", "Too many keep patterns; maximum 20 allowed.")
    compiled: list[re.Pattern[str]] = []
    for pattern in keep:
        if len(pattern) > 200:
            raise CompressorError(
                "invalid_pattern", f"Pattern exceeds 200 characters: {pattern[:200]!r}"
            )
        try:
            compiled.append(re.compile(pattern))
        except re.error as err:
            raise CompressorError("invalid_pattern", f"Invalid regex pattern: {err}") from err
    return compiled


def _extract_blocks(text: str) -> list[tuple[bool, list[str]]]:
    """Split into alternating prose and code blocks.

    Returns a list of (is_code, lines).
    Unterminated fence treats the rest of text as code.
    """
    lines = text.split("\n")
    blocks: list[tuple[bool, list[str]]] = []
    curr_lines: list[str] = []
    in_code = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                # Closing code block
                curr_lines.append(line)
                blocks.append((True, curr_lines))
                curr_lines = []
                in_code = False
            else:
                # Opening code block
                if curr_lines:
                    blocks.append((False, curr_lines))
                    curr_lines = []
                curr_lines.append(line)
                in_code = True
        else:
            curr_lines.append(line)

    if curr_lines:
        blocks.append((in_code, curr_lines))
    return blocks


def find_protected(text: str, keep: Sequence[str] = ()) -> tuple[str, ...]:
    """Find protected strings (code blocks, instruction lines, entity sentences)."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    compiled_keeps = _validate_keeps(keep)
    blocks = _extract_blocks(normalized)
    protected_list: list[str] = []

    for is_code, lines in blocks:
        if is_code:
            protected_list.append("\n".join(lines))
            continue
        for line in lines:
            if not line.strip():
                continue
            if _is_protected_instruction_line(line):
                protected_list.append(line)
            else:
                sentences = _SENTENCE_SPLIT_RE.split(line)
                for s in sentences:
                    s_clean = s.strip()
                    if s_clean and _line_has_entity(s, compiled_keeps):
                        protected_list.append(s)
    return tuple(protected_list)


def _apply_filler(sentence: str) -> tuple[str, int]:
    """Apply filler replacements on an unprotected sentence."""
    replacements_done = 0
    res = sentence
    for phrase, target in _FILLER_REPLACEMENTS:
        # Word boundaries matching, preserving case of the first letter
        # Build pattern for phrase
        is_trailing_space = phrase.endswith(" ")
        core = phrase.strip()
        words = [re.escape(w) for w in core.split()]
        core_pat = r"\s+".join(words)
        if is_trailing_space:
            pat_str = (
                r"(?i)"
                + (r"\b" if core[0].isalnum() else "")
                + core_pat
                + (r"\b" if core[-1].isalnum() else "")
                + r"\s+"
            )
        else:
            pat_str = (
                r"(?i)"
                + (r"\b" if core[0].isalnum() else "")
                + core_pat
                + (r"\b" if core[-1].isalnum() else "")
            )
        pat = re.compile(pat_str)

        def repl(match: re.Match[str], tgt: str = target) -> str:
            nonlocal replacements_done
            replacements_done += 1
            matched_str = match.group(0)
            if not tgt:
                return ""
            if matched_str and matched_str[0].isupper():
                return tgt[0].upper() + tgt[1:]
            return tgt

        res = pat.sub(repl, res)
    return res, replacements_done


def compress(
    text: str,
    *,
    target_ratio: float = 0.6,
    counter: Callable[[str], int] = word_count,
    keep: Sequence[str] = (),
    max_input_chars: int = 500_000,
) -> Compression:
    """Compress a prompt deterministically while protecting instructions, entities and code."""
    if len(text) > max_input_chars:
        preview = text[:200]
        raise InputTooLargeError(
            f"Input text length {len(text)} exceeds limit {max_input_chars} "
            f"(first 200 chars: {preview!r})"
        )
    if not (0.0 < target_ratio <= 1.0):
        raise CompressorError(
            "invalid_ratio", f"target_ratio must be in (0.0, 1.0], got {target_ratio}"
        )

    # Normalize CRLF to LF
    norm_text = text.replace("\r\n", "\n").replace("\r", "\n")

    def run_counter(s: str) -> int:
        cnt = counter(s)
        if isinstance(cnt, bool) or not isinstance(cnt, int) or cnt < 0:
            raise CompressorError("invalid_counter", f"Counter returned invalid token count: {cnt}")
        return cnt

    # Normalize CRLF to LF and strip trailing newline to preserve exact string lines
    had_trailing_newline = norm_text.endswith("\n")
    if had_trailing_newline:
        norm_text = norm_text[:-1]

    orig_tokens = run_counter(norm_text)
    if not norm_text:
        return Compression(
            text="",
            original_tokens=orig_tokens,
            compressed_tokens=orig_tokens,
            saved_ratio=0.0,
            target_met=True,
            steps=(),
            protected=(),
        )

    compiled_keeps = _validate_keeps(keep)
    blocks = _extract_blocks(norm_text)

    # Classify blocks & lines
    # Each block is (is_code, lines)
    # Prose lines are analyzed for protected status and entities
    # Step counts
    whitespace_count = 0
    duplicate_count = 0
    filler_count = 0
    drop_sentence_count = 0

    # Rule 4: Whitespace collapse
    # Collapse runs of spaces/tabs to one space and 3+ newlines to 2, count = runs collapsed
    ws_collapsed_blocks: list[tuple[bool, list[str]]] = []
    space_run_re = re.compile(r"[ \t]{2,}")

    for is_code, blk_lines in blocks:
        if is_code:
            ws_collapsed_blocks.append((True, list(blk_lines)))
        else:
            new_blk_lines: list[str] = []
            for line in blk_lines:
                # Count runs of 2+ spaces/tabs
                matches = space_run_re.findall(line)
                whitespace_count += len(matches)
                cleaned_line = space_run_re.sub(" ", line)
                new_blk_lines.append(cleaned_line)
            ws_collapsed_blocks.append((False, new_blk_lines))

    # Also collapse runs of 3+ newlines between/within prose
    # To do this safely across whole prose structure while keeping code fences untouched:
    # Notice: consecutive empty lines in prose blocks correspond to newline runs.
    # If there are N empty lines (N+1 newlines), if N >= 2, collapse to 1 empty line (2 newlines).
    # The collapsed run count is the number of 3+ newline occurrences.
    final_ws_blocks: list[tuple[bool, list[str]]] = []
    for is_code, blk_lines in ws_collapsed_blocks:
        if is_code:
            final_ws_blocks.append((True, blk_lines))
        else:
            condensed_lines: list[str] = []
            empty_streak = 0
            for line in blk_lines:
                if line == "":
                    empty_streak += 1
                else:
                    if empty_streak > 0:
                        if empty_streak >= 2:
                            whitespace_count += 1
                            condensed_lines.append("")
                        else:
                            condensed_lines.extend([""] * empty_streak)
                        empty_streak = 0
                    condensed_lines.append(line)
            if empty_streak > 0:
                if empty_streak >= 2:
                    whitespace_count += 1
                    condensed_lines.append("")
                else:
                    condensed_lines.extend([""] * empty_streak)
            final_ws_blocks.append((False, condensed_lines))

    # Rule 5: 'duplicate_line' (blank lines never count)
    # drop a non-blank prose line equal (after whitespace collapse) to an earlier one
    seen_prose_lines: set[str] = set()
    dedup_blocks: list[tuple[bool, list[str]]] = []
    for is_code, blk_lines in final_ws_blocks:
        if is_code:
            dedup_blocks.append((True, blk_lines))
        else:
            surviving_lines: list[str] = []
            for line in blk_lines:
                if line == "":
                    surviving_lines.append(line)
                elif line in seen_prose_lines:
                    duplicate_count += 1
                else:
                    seen_prose_lines.add(line)
                    surviving_lines.append(line)
            dedup_blocks.append((False, surviving_lines))

    # Determine protected sentences and lines across all surviving blocks
    # Protected includes:
    # - Code blocks
    # - Instruction lines
    # - Sentences with entities
    # Note: we need to collect protected strings to return in result.protected
    protected_strings: list[str] = []
    for is_code, blk_lines in dedup_blocks:
        if is_code:
            protected_strings.append("\n".join(blk_lines))
        else:
            for line in blk_lines:
                if not line.strip():
                    continue
                if _is_protected_instruction_line(line):
                    protected_strings.append(line)
                else:
                    sentences = _SENTENCE_SPLIT_RE.split(line)
                    for s in sentences:
                        s_clean = s.strip()
                        if s_clean and _line_has_entity(s, compiled_keeps):
                            protected_strings.append(s)

    # Rule 6: 'filler' applied to unprotected prose sentences only
    # never inside protected spans
    filler_blocks: list[tuple[bool, list[str]]] = []
    for is_code, blk_lines in dedup_blocks:
        if is_code:
            filler_blocks.append((True, blk_lines))
        else:
            new_lines: list[str] = []
            for line in blk_lines:
                if not line.strip():
                    new_lines.append(line)
                    continue
                if _is_protected_instruction_line(line):
                    new_lines.append(line)
                else:
                    sentences = _SENTENCE_SPLIT_RE.split(line)
                    replaced_sentences: list[str] = []
                    for s in sentences:
                        if _line_has_entity(s, compiled_keeps):
                            # protected sentence, untouched
                            replaced_sentences.append(s)
                        else:
                            new_s, n_rep = _apply_filler(s)
                            filler_count += n_rep
                            replaced_sentences.append(new_s)
                    # Reconstruct line preserving single spaces between sentences
                    reconstructed = " ".join(s for s in replaced_sentences if s)
                    new_lines.append(reconstructed)
            filler_blocks.append((False, new_lines))

    # Rule 7: 'drop_sentence' only while compressed_tokens > target_ratio * original_tokens
    # sentences split on (?<=[.!?])\s+ inside unprotected prose lines;
    # score = number of distinct lowercase words of length >= 4 also present in a protected line;
    # drop lowest score first, ties drop the later sentence first;
    # emptied lines are removed.

    # Collect protected line words (length >= 4, lowercase)
    protected_words: set[str] = set()
    for is_code, blk_lines in filler_blocks:
        if is_code:
            for w in _WORD_RE.findall("\n".join(blk_lines)):
                protected_words.add(w.lower())
        else:
            for line in blk_lines:
                if _is_protected_instruction_line(line):
                    for w in _WORD_RE.findall(line):
                        protected_words.add(w.lower())

    # Represent prose lines as lists of sentences
    # SentenceRef tracks block, line, sentence index, text, protection status, score, order
    @dataclass
    class SentenceRef:
        blk_idx: int
        line_idx: int
        s_idx: int
        text: str
        is_protected: bool
        score: int
        order: int
        dropped: bool = False

    parsed_structure: list[tuple[bool, list[list[SentenceRef]]]] = []
    droppable_candidates: list[SentenceRef] = []
    order_counter = 0

    for b_i, (is_code, blk_lines) in enumerate(filler_blocks):
        if is_code:
            parsed_structure.append((True, []))
        else:
            blk_sentence_lines: list[list[SentenceRef]] = []
            for l_i, line in enumerate(blk_lines):
                if not line.strip():
                    blk_sentence_lines.append([])
                    continue
                is_instr = _is_protected_instruction_line(line)
                raw_sentences = _SENTENCE_SPLIT_RE.split(line)
                s_refs: list[SentenceRef] = []
                for s_i, s_text in enumerate(raw_sentences):
                    s_clean = s_text.strip()
                    if not s_clean:
                        continue
                    is_prot = is_instr or _line_has_entity(s_text, compiled_keeps)
                    if not is_prot:
                        # compute score
                        words = {w.lower() for w in _WORD_RE.findall(s_clean)}
                        overlap = len(words.intersection(protected_words))
                        s_ref = SentenceRef(
                            blk_idx=b_i,
                            line_idx=l_i,
                            s_idx=s_i,
                            text=s_text,
                            is_protected=False,
                            score=overlap,
                            order=order_counter,
                        )
                        droppable_candidates.append(s_ref)
                    else:
                        s_ref = SentenceRef(
                            blk_idx=b_i,
                            line_idx=l_i,
                            s_idx=s_i,
                            text=s_text,
                            is_protected=True,
                            score=0,
                            order=order_counter,
                        )
                    order_counter += 1
                    s_refs.append(s_ref)
                blk_sentence_lines.append(s_refs)
            parsed_structure.append((False, blk_sentence_lines))

    def assemble_text() -> str:
        block_strs: list[str] = []
        for b_i, (is_code, blk_lines) in enumerate(filler_blocks):
            if is_code:
                block_strs.append("\n".join(blk_lines))
            else:
                lines_out: list[str] = []
                for l_i, s_list in enumerate(parsed_structure[b_i][1]):
                    surviving_sentences = [
                        s.text.strip() for s in s_list if not s.dropped and s.text.strip()
                    ]
                    if surviving_sentences:
                        lines_out.append(" ".join(surviving_sentences))
                    elif not s_list and l_i < len(blk_lines) and blk_lines[l_i] == "":
                        # Preserved empty line
                        lines_out.append("")
                    # Emptied lines that had sentences are removed
                block_strs.append("\n".join(lines_out))
        return "\n".join(block_strs)

    # Sort candidates for dropping: lowest score first; ties drop later sentence first (order desc)
    droppable_candidates.sort(key=lambda s: (s.score, -s.order))

    current_text = assemble_text()
    current_tokens = run_counter(current_text)

    for candidate in droppable_candidates:
        if current_tokens <= target_ratio * orig_tokens:
            break
        candidate.dropped = True
        drop_sentence_count += 1
        current_text = assemble_text()
        current_tokens = run_counter(current_text)

    final_text = assemble_text()
    final_tokens = run_counter(final_text)
    saved_ratio = (1.0 - (final_tokens / orig_tokens)) if orig_tokens > 0 else 0.0
    target_met = final_tokens <= (target_ratio * orig_tokens)

    steps_list: list[Step] = []
    if whitespace_count > 0:
        steps_list.append(Step("whitespace", whitespace_count))
    if duplicate_count > 0:
        steps_list.append(Step("duplicate_line", duplicate_count))
    if filler_count > 0:
        steps_list.append(Step("filler", filler_count))
    if drop_sentence_count > 0:
        steps_list.append(Step("drop_sentence", drop_sentence_count))

    # Protected list must reflect the protected strings present in final text
    # Note: every string in result.protected must be in result.text
    final_protected: tuple[str, ...]
    if not protected_strings:
        final_protected = ()
    else:
        final_protected = tuple(p for p in protected_strings if p in final_text)

    return Compression(
        text=final_text,
        original_tokens=orig_tokens,
        compressed_tokens=final_tokens,
        saved_ratio=saved_ratio,
        target_met=target_met,
        steps=tuple(steps_list),
        protected=final_protected,
    )
