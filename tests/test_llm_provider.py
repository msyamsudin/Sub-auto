"""
Tests for LLM provider abstractions.
Covers ModelInfo/GenerationResult helpers and response parsing for all three
providers, with the HTTP layer mocked out (no network access).
"""

import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from core.llm_provider import (
    GenerationResult,
    GroqProvider,
    ModelInfo,
    OllamaProvider,
    OpenRouterProvider,
    PolicyViolationError,
)


# ---------------------------------------------------------------- helpers

def test_model_info_short_name():
    info = ModelInfo("models/gemini-pro", "Gemini Pro", "OpenRouter")
    assert info.short_name == "gemini-pro"


def test_model_info_calculate_cost():
    info = ModelInfo(
        "m", "M", "OpenRouter",
        prompt_price=2.0,    # USD per 1M prompt tokens
        completion_price=6.0,  # USD per 1M completion tokens
    )
    assert info.calculate_cost(1_000_000, 1_000_000) == pytest.approx(8.0)
    assert info.calculate_cost(0, 0) == 0.0


def test_generation_result_total():
    g = GenerationResult("text", prompt_tokens=10, completion_tokens=5)
    assert g.text == "text"
    assert g.total_tokens == 15


# ------------------------------------------------------------- OpenRouter

class TestOpenRouter:
    def _provider(self, monkeypatch, fake_response):
        provider = OpenRouterProvider("test-key")
        monkeypatch.setattr(provider, "_request", lambda *a, **k: fake_response)
        return provider

    def test_generate_content_parses_usage(self, monkeypatch):
        provider = self._provider(monkeypatch, {
            "choices": [{"message": {"content": "Halo"}}],
            "usage": {"prompt_tokens": 111, "completion_tokens": 222},
        })
        result = provider.generate_content("model-x", "prompt")
        assert result.text == "Halo"
        assert result.prompt_tokens == 111
        assert result.completion_tokens == 222

    def test_generate_content_without_usage_defaults_to_zero(self, monkeypatch):
        provider = self._provider(monkeypatch, {
            "choices": [{"message": {"content": "Halo"}}],
        })
        result = provider.generate_content("model-x", "prompt")
        assert result.text == "Halo"
        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0

    def test_generate_content_api_error(self, monkeypatch):
        provider = self._provider(monkeypatch, {"error": {"message": "boom"}})
        with pytest.raises(RuntimeError, match="boom"):
            provider.generate_content("model-x", "prompt")

    def test_generate_content_empty_choices(self, monkeypatch):
        provider = self._provider(monkeypatch, {"choices": []})
        assert provider.generate_content("model-x", "prompt").text == ""

    def test_validate_connection_reports_missing_key(self):
        provider = OpenRouterProvider("")
        ok, msg = provider.validate_connection()
        assert ok is False
        assert "API key" in msg

    def test_policy_violation_detected(self, monkeypatch):
        class FakeBody:
            def read(self):
                return b'{"error": {"message": "This request was blocked by moderation policy"}}'

            def close(self):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, FakeBody())

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        provider = OpenRouterProvider("test-key")
        with pytest.raises(PolicyViolationError):
            provider._request("GET", "/models")

    def test_plain_403_is_not_policy_violation(self, monkeypatch):
        class FakeBody:
            def read(self):
                return b'{"error": {"message": "invalid api key"}}'

            def close(self):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, FakeBody())

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        provider = OpenRouterProvider("test-key")
        with pytest.raises(RuntimeError):
            provider._request("GET", "/models")


# ------------------------------------------------------------------- Groq

class TestGroq:
    def _provider(self, monkeypatch, fake_response):
        provider = GroqProvider("test-key")
        monkeypatch.setattr(provider, "_request", lambda *a, **k: fake_response)
        return provider

    def test_generate_content_parses_usage(self, monkeypatch):
        provider = self._provider(monkeypatch, {
            "choices": [{"message": {"content": "Halo"}}],
            "usage": {"prompt_tokens": 33, "completion_tokens": 44},
        })
        result = provider.generate_content("model-x", "prompt")
        assert result.text == "Halo"
        assert result.prompt_tokens == 33
        assert result.completion_tokens == 44

    def test_generate_content_without_usage(self, monkeypatch):
        provider = self._provider(monkeypatch, {"choices": [{"message": {"content": "Halo"}}]})
        result = provider.generate_content("model-x", "prompt")
        assert result.text == "Halo"
        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0


# ----------------------------------------------------------------- Ollama

class TestOllama:
    def _provider_with_fake_opener(self, monkeypatch, body_bytes, timeout_expected=120):
        class FakeResponse:
            def read(self):
                return body_bytes

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        captured = {}

        class FakeOpener:
            def open(self, req, timeout=None):
                captured["timeout"] = timeout
                return FakeResponse()

        provider = OllamaProvider()
        monkeypatch.setattr(provider, "_get_opener", lambda: FakeOpener())
        return provider, captured

    def test_generate_content_parses_counts_and_uses_timeout(self, monkeypatch):
        provider, captured = self._provider_with_fake_opener(
            monkeypatch, b'{"response": "Halo", "prompt_eval_count": 7, "eval_count": 3}'
        )
        result = provider.generate_content("llama3", "prompt")
        assert result.text == "Halo"
        assert result.prompt_tokens == 7
        assert result.completion_tokens == 3
        assert captured["timeout"] == 120  # D1: explicit timeout must be sent

    def test_generate_content_missing_counts(self, monkeypatch):
        provider, _ = self._provider_with_fake_opener(monkeypatch, b'{"response": "Halo"}')
        result = provider.generate_content("llama3", "prompt")
        assert result.text == "Halo"
        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0
