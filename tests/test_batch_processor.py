"""
Tests for core/batch_processor.py: token/result models, response parsing,
token estimation, and the progressive-smaller-batch recovery loop.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from core.batch_processor import (
    TokenUsage,
    TranslationResult,
    estimate_tokens,
    parse_translation_response,
    translate_with_recovery,
)
from core.subtitle_parser import SubtitleLine


class _StubLogger:
    def info(self, message):
        pass

    def warning(self, message):
        pass

    def error(self, message):
        pass


def _lines(n, start=1):
    return [
        SubtitleLine(i, i * 1000, i * 1000 + 500, f"L{i}")
        for i in range(start, start + n)
    ]


def _ok_result(chunk):
    return TranslationResult(True, [(line.index, f"TR{line.index}") for line in chunk])


class TestTokenUsage:
    def test_add_and_reset(self):
        usage = TokenUsage()
        usage.add(prompt=10, completion=5)
        assert usage.total_tokens == 15
        usage.add(prompt=1)
        assert usage.prompt_tokens == 11
        assert usage.completion_tokens == 5
        usage.reset()
        assert usage.prompt_tokens == 0
        assert usage.total_tokens == 0

    def test_str(self):
        assert "Tokens: 0" in str(TokenUsage())


class TestTranslationResult:
    def test_defaults(self):
        result = TranslationResult(success=True, translated_lines=[])
        assert result.error_message == ""
        assert result.tokens_used.total_tokens == 0


class TestEstimateTokens:
    def test_estimate(self):
        assert estimate_tokens("") == 0
        assert estimate_tokens("abcd") == 1
        assert estimate_tokens("abcdefgh") == 2


class TestParseResponse:
    def test_normal(self):
        parsed = parse_translation_response("[1] Halo\n[2] Apa kabar?\n[3] Sampai", _lines(3))
        assert [i for i, _ in parsed] == [1, 2, 3]

    def test_multiline_and_brackets_preserved(self):
        parsed = parse_translation_response(
            "[1] Baris pertama\nbaris kedua\n[2] Lihat [3] orang itu", _lines(2)
        )
        assert parsed[0] == (1, "Baris pertama\nbaris kedua")
        assert parsed[1] == (2, "Lihat [3] orang itu")

    def test_unknown_format_returns_empty(self):
        assert parse_translation_response("1. Halo\n2. Apa kabar", _lines(2)) == []

    def test_invalid_indices_filtered(self):
        parsed = parse_translation_response("[1] Halo\n[99] Tidak valid\n[2] Hai", _lines(2))
        assert [i for i, _ in parsed] == [1, 2]


class TestTranslateWithRecovery:
    def test_all_resolved_first_round(self):
        calls = []

        def translate_fn(chunk):
            calls.append(len(chunk))
            return _ok_result(chunk)

        resolved, pending, reasons, tokens = translate_with_recovery(
            translate_fn, _lines(3), stop_check=lambda: False, logger=_StubLogger()
        )
        assert len(resolved) == 3
        assert pending == []
        assert calls == [3]

    def test_missing_line_retried_in_smaller_chunk(self):
        state = {"dropped": False}

        def translate_fn(chunk):
            if len(chunk) == 3 and not state["dropped"]:
                state["dropped"] = True
                return TranslationResult(
                    True,
                    [(line.index, f"TR{line.index}") for line in chunk[:-1]],
                    error_message="Partial: expected 3, got 2",
                )
            return _ok_result(chunk)

        resolved, pending, reasons, tokens = translate_with_recovery(
            translate_fn, _lines(3), stop_check=lambda: False, logger=_StubLogger()
        )
        assert len(resolved) == 3
        assert pending == []

    def test_stop_check_aborts_without_translating(self):
        calls = []

        def translate_fn(chunk):
            calls.append(chunk)
            return _ok_result(chunk)

        translations, pending, reasons, tokens = translate_with_recovery(
            translate_fn, _lines(3), stop_check=lambda: True, logger=_StubLogger()
        )
        assert translations == []
        assert len(pending) == 3
        assert calls == []

    def test_unresolved_lines_reported_with_reasons(self):
        def translate_fn(chunk):
            return TranslationResult(False, [], error_message="API down")

        translations, pending, reasons, tokens = translate_with_recovery(
            translate_fn, _lines(2), stop_check=lambda: False,
            logger=_StubLogger(), max_recovery_rounds=0,
        )
        assert translations == []
        assert len(pending) == 2
        assert all(reason == "API down" for reason in reasons.values())

    def test_recovery_tokens_accumulated(self):
        calls = 0

        def translate_fn(chunk):
            nonlocal calls
            calls += 1
            result = _ok_result(chunk)
            result.tokens_used.add(prompt=7, completion=3)
            return result

        _, _, _, tokens = translate_with_recovery(
            translate_fn, _lines(3), stop_check=lambda: False,
            logger=_StubLogger(), max_recovery_rounds=0,
        )
        assert calls == 1
        assert tokens.prompt_tokens == 7
        assert tokens.completion_tokens == 3
