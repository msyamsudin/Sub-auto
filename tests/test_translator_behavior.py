"""
Behavioral tests for Translator using a fake LLM provider.

The fake provider echoes ``[idx]`` lines back with their original indices and
optionally reports real token usage, fails with network errors, or triggers
policy violations -- no network access is ever made. The prompt repository is
isolated in a tmp directory so tests do not depend on the user's prompts file.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from core.exceptions import TranslationCancelled
from core.llm_provider import LLMProvider, ModelInfo, GenerationResult, PolicyViolationError
from core.model_manager import ModelManager
from core.prompt_manager import PromptManager
from core.prompt_repository import PromptRepository
from core.state_manager import StateManager
from core.subtitle_parser import SubtitleLine
from core.translator import Translator


class EchoProvider(LLMProvider):
    """Echoes [idx] lines with original indices; configurable failure modes."""

    def __init__(self, prompt_tokens=0, completion_tokens=0, policy_times=0, fail_times=0):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.policy_times = policy_times
        self.fail_times = fail_times
        self.calls = 0

    def validate_connection(self):
        return True, "ok"

    def list_models(self):
        return [ModelInfo("fake", "fake", "fake")]

    def generate_content(self, model_name, prompt):
        self.calls += 1
        if self.policy_times > 0:
            self.policy_times -= 1
            raise PolicyViolationError("OpenRouter Policy Violation: blocked")
        if self.fail_times > 0:
            self.fail_times -= 1
            raise ConnectionError("connection reset by peer")
        idxs = [int(m) for m in re.findall(r"\[(\d+)\]", prompt)]
        return GenerationResult(
            text="\n".join(f"[{i}] TR{i}" for i in idxs),
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
        )


def _make_translator(provider, tmp_path, batch_delay=0.0):
    """Translator with a hermetic prompt repo and a pre-configured model manager."""
    repo = PromptRepository(storage_path=str(tmp_path / "prompts.json"))
    prompt_manager = PromptManager(repository=repo)

    mm = ModelManager()
    mm.provider = provider
    mm.is_configured = True
    mm.selected_model = "fake"
    mm.available_models = [ModelInfo("fake", "fake", "fake")]
    mm.config.provider = "openrouter"
    mm.config.batch_delay_seconds = batch_delay

    return Translator(model_manager=mm, prompt_manager=prompt_manager)


def _lines(n, start=1):
    return [
        SubtitleLine(i, i * 1000, i * 1000 + 500, f"Line {i}")
        for i in range(start, start + n)
    ]


def test_translate_batch_happy_path(tmp_path):
    t = _make_translator(EchoProvider(), tmp_path)
    result = t.translate_batch(_lines(3))
    assert result.success
    assert len(result.translated_lines) == 3
    assert result.translated_lines[0] == (1, "TR1")


def test_translate_batch_uses_real_token_usage(tmp_path):
    t = _make_translator(EchoProvider(prompt_tokens=500, completion_tokens=100), tmp_path)
    result = t.translate_batch(_lines(3))
    assert result.tokens_used.prompt_tokens == 500
    assert result.tokens_used.completion_tokens == 100


def test_translate_all_translates_every_line(tmp_path):
    t = _make_translator(EchoProvider(), tmp_path)
    translations, errors, tokens = t.translate_all(_lines(20), batch_size=5)
    assert len(translations) == 20
    assert errors == []
    assert translations[0] == (1, "TR1")


def test_translate_all_accumulates_real_tokens_across_batches(tmp_path):
    t = _make_translator(EchoProvider(prompt_tokens=100, completion_tokens=20), tmp_path)
    _, _, tokens = t.translate_all(_lines(10), batch_size=5)
    assert tokens.prompt_tokens == 100 * 2
    assert tokens.completion_tokens == 20 * 2


def test_translate_all_falls_back_to_estimate_without_usage(tmp_path):
    t = _make_translator(EchoProvider(), tmp_path)
    translations, errors, tokens = t.translate_all(_lines(5), batch_size=5)
    assert len(translations) == 5
    assert tokens.prompt_tokens > 0
    assert tokens.completion_tokens > 0


def test_stop_before_call_raises_cancellation(tmp_path):
    t = _make_translator(EchoProvider(), tmp_path)
    t.should_stop = True
    with pytest.raises(TranslationCancelled):
        t.translate_batch(_lines(3))


def test_cancellation_propagates_out_of_translate_all(tmp_path):
    """B4: cancel must surface as TranslationCancelled (an Exception), not an
    unhandled BaseException, so the orchestrator can exit cleanly."""
    t = _make_translator(EchoProvider(), tmp_path)

    def callback(*args):
        raise TranslationCancelled("Cancelled")

    with pytest.raises(TranslationCancelled):
        t.translate_all(_lines(10), batch_size=5, progress_callback=callback)


def test_partial_response_filled_by_recovery(tmp_path):
    """A response that drops one line is completed by the recovery rounds."""

    class PartialProvider(EchoProvider):
        def generate_content(self, model_name, prompt):
            idxs = [int(m) for m in re.findall(r"\[(\d+)\]", prompt)]
            return GenerationResult(text="\n".join(f"[{i}] TR{i}" for i in idxs[:-1]))

    t = _make_translator(PartialProvider(), tmp_path)
    translations, errors, tokens = t.translate_all(_lines(3), batch_size=3)
    # The missing line falls back to the original text, but all lines present
    assert len(translations) == 3
    assert len(errors) >= 1


def test_policy_violation_uses_fallback_model(tmp_path):
    t = _make_translator(EchoProvider(policy_times=1), tmp_path)
    t.model_manager.config.fallback_model = "backup-model"
    result = t.translate_batch(_lines(2))
    assert result.success
    assert result.error_message == "Success (Fallback used)"
    assert len(result.translated_lines) == 2


def test_network_failure_retried_then_fails(tmp_path):
    t = _make_translator(EchoProvider(fail_times=10), tmp_path)
    result = t.translate_batch(_lines(2))
    assert result.success is False
    assert "retries" in result.error_message
    assert t.retry_handler.total_retries > 0


def test_resume_skips_completed_lines(tmp_path):
    sm = StateManager(state_dir=str(tmp_path / "state"))
    sm.create_state(
        source_file="C:/x.mkv",
        track_id=1,
        total_lines=3,
        source_lang="English",
        target_lang="Indonesian",
        model_name="fake",
    )
    sm.update_progress([(1, "TR1"), (2, "TR2")], 0)

    t = _make_translator(EchoProvider(), tmp_path)
    translations, errors, tokens = t.translate_all(_lines(3), batch_size=3, state_manager=sm)
    assert len(translations) == 3
    mapping = {idx: text for idx, text in translations}
    assert mapping[1] == "TR1"  # from saved state, not re-translated
    assert mapping[2] == "TR2"
    assert mapping[3] == "TR3"


def test_parse_response_filters_invalid_indices(tmp_path):
    t = _make_translator(EchoProvider(), tmp_path)
    lines = _lines(3)
    parsed = t._parse_response("[1] Halo\n[99] Bukan index\n[2] Hai\n[3] Apa kabar", lines)
    assert [i for i, _ in parsed] == [1, 2, 3]
