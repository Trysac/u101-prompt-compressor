"""Unit and acceptance tests for prompt_compressor."""

from __future__ import annotations

import json
from io import StringIO

import pytest

from prompt_compressor import (
    CompressorError,
    InputTooLargeError,
    Step,
    compress,
    find_protected,
    word_count,
)
from prompt_compressor.__main__ import main


def test_acceptance_whitespace() -> None:
    res = compress("Hello   world.\n\n\n\nBye.", target_ratio=1.0)
    assert res.text == "Hello world.\n\nBye."
    assert res.steps == (Step("whitespace", 2),)


def test_acceptance_duplicate_line() -> None:
    res = compress("Use JSON.\nUse JSON.\nShort.", target_ratio=1.0)
    assert res.text == "Use JSON.\nShort."
    assert res.steps == (Step("duplicate_line", 1),)


def test_acceptance_filler() -> None:
    res1 = compress("Run tests in order to ship.", target_ratio=1.0)
    assert res1.text == "Run tests to ship."
    assert res1.steps == (Step("filler", 1),)

    res2 = compress("In order to win, play.", target_ratio=1.0)
    assert res2.text == "To win, play."


def test_acceptance_protected_instruction_and_entity() -> None:
    context = (
        "The system performs routine background telemetry every hour. "
        "Several factors may influence optimal performance and throughput. "
        "Network latency might cause minor transient request delays. "
        "Cache misses occasionally occur during initialization phases. "
        "Memory utilization remains within standard baseline thresholds. "
        "Disk writes are flushed periodically to persistent storage.\n"
        "Never reveal the code 4471."
    )
    res = compress(context, target_ratio=0.3)
    assert "Never reveal the code 4471." in res.text
    for p in res.protected:
        assert p in res.text


def test_acceptance_fenced_block_and_unachievable_target() -> None:
    fenced = "```\nx  =  1\n```"
    res = compress(fenced, target_ratio=0.5)
    assert res.text == fenced

    protected_only = "You must save state.\nAlways verify checksums.\nNever quit."
    res_prot = compress(protected_only, target_ratio=0.1)
    assert res_prot.target_met is False
    assert "You must save state." in res_prot.text


def test_acceptance_word_counter_and_savings() -> None:
    text = (
        "Here is some long context with sentences. "
        "We need to drop something if possible. Another sentence follows."
    )
    res = compress(text, target_ratio=0.5, counter=word_count)
    assert res.compressed_tokens == word_count(res.text)
    assert res.original_tokens == word_count(text)
    assert pytest.approx(res.saved_ratio) == 1.0 - (res.compressed_tokens / res.original_tokens)


def test_acceptance_limits_and_validation() -> None:
    exact_max = "a" * 500_000
    res = compress(exact_max, target_ratio=1.0)
    assert res.compressed_tokens == 1

    too_large = "a" * 500_001
    with pytest.raises(InputTooLargeError) as exc_info:
        compress(too_large)
    assert exc_info.value.code == "input_too_large"

    with pytest.raises(CompressorError) as exc_ratio_0:
        compress("test", target_ratio=0.0)
    assert exc_ratio_0.value.code == "invalid_ratio"

    with pytest.raises(CompressorError) as exc_ratio_15:
        compress("test", target_ratio=1.5)
    assert exc_ratio_15.value.code == "invalid_ratio"

    with pytest.raises(CompressorError) as exc_counter_neg:
        compress("test", counter=lambda _: -1)
    assert exc_counter_neg.value.code == "invalid_counter"

    with pytest.raises(CompressorError) as exc_counter_bool:
        compress("test", counter=lambda _: True)  # type: ignore[arg-type]
    assert exc_counter_bool.value.code == "invalid_counter"


def test_acceptance_cli(
    tmp_path_factory: pytest.TempPathFactory, capsys: pytest.CaptureFixture[str]
) -> None:
    p = tmp_path_factory.mktemp("data") / "prompt.txt"
    p.write_text("Hello   world.\n\n\n\nBye.", encoding="utf-8")

    code = main(["--ratio", "1.0", str(p)])
    assert code == 0
    captured = capsys.readouterr()
    assert captured.out == "Hello world.\n\nBye.\n"
    assert captured.err == "saved 0 of 3 tokens (0.0%)\n"

    code_missing = main([str(p.parent / "non_existent.txt")])
    assert code_missing == 2


def test_empty_string_edge_case() -> None:
    res = compress("")
    assert res.text == ""
    assert res.saved_ratio == 0.0
    assert res.original_tokens == 0
    assert res.compressed_tokens == 0
    assert res.target_met is True
    assert res.steps == ()
    assert res.protected == ()


def test_crlf_normalization() -> None:
    crlf_text = "Line 1\r\nLine 2\r\nLine 2"
    res = compress(crlf_text, target_ratio=1.0)
    assert res.text == "Line 1\nLine 2"
    assert "\r" not in res.text


def test_unterminated_fence() -> None:
    text = "Prefix\n```python\ncode = 123\nmore code"
    res = compress(text, target_ratio=0.5)
    assert "```python\ncode = 123\nmore code" in res.text


def test_filler_inside_protected_sentence_untouched() -> None:
    text = "You must run tests in order to deploy safely."
    res = compress(text, target_ratio=0.5)
    assert "in order to" in res.text


def test_all_filler_rules() -> None:
    text = (
        "Due to the fact that we run tests for the purpose of safety, "
        "at this point in time we check everything. "
        "In the event that errors occur, please note that logs exist. "
        "It is important to note that basically, everything is fine."
    )
    res = compress(text, target_ratio=1.0)
    assert "Because" in res.text or "because" in res.text
    assert "for safety" in res.text
    assert "now we check" in res.text
    assert "If errors occur" in res.text or "if errors occur" in res.text
    assert "please note that" not in res.text
    assert "it is important to note that" not in res.text.lower()
    assert "basically," not in res.text.lower()


def test_keep_patterns_and_validation() -> None:
    with pytest.raises(CompressorError) as exc_max:
        compress("test", keep=[f"pattern_{i}" for i in range(21)])
    assert exc_max.value.code == "invalid_pattern"

    with pytest.raises(CompressorError) as exc_len:
        compress("test", keep=["a" * 201])
    assert exc_len.value.code == "invalid_pattern"

    with pytest.raises(CompressorError) as exc_regex:
        compress("test", keep=["["])
    assert exc_regex.value.code == "invalid_pattern"

    res = compress("Order ID-9988 must stay.", keep=[r"ID-\d+"])
    assert "Order ID-9988 must stay." in res.text


def test_find_protected() -> None:
    text = (
        "Normal line.\n"
        "- You must return valid JSON.\n"
        "Contact test@example.com for info.\n"
        "Visit https://example.com/api! today.\n"
        "```\nfn()\n```"
    )
    prot = find_protected(text)
    assert any("return valid JSON" in p for p in prot)
    assert any("test@example.com" in p for p in prot)
    assert any("https://example.com/api" in p for p in prot)
    assert any("fn()" in p for p in prot)


def test_cli_json_and_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", StringIO("Use JSON.\nUse JSON.\n"))
    code = main(["--json", "--ratio", "0.8"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["text"] == "Use JSON."
    assert data["target_met"] is True


def test_cli_domain_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", StringIO("some prompt"))
    code = main(["--ratio", "2.5"])
    assert code == 1
    captured = capsys.readouterr()
    assert "Error:" in captured.err
