"""
Behavioral tests for NetworkRetryHandler.
Covers retry counting, backoff, retryability classification, stop checks,
and the callback notification path.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from core.exceptions import TranslationCancelled
from core.retry_handler import NetworkRetryHandler, RetryConfig


def _handler(**kwargs):
    """Handler with fast backoff for tests."""
    defaults = dict(initial_delay=0.01, max_delay=0.05)
    defaults.update(kwargs)
    return NetworkRetryHandler(RetryConfig(**defaults))


def test_succeeds_on_first_attempt():
    handler = _handler()
    assert handler.execute_with_retry(lambda: "ok") == "ok"
    assert handler.total_retries == 0


def test_retries_until_success_and_counts():
    state = {"calls": 0}

    def flaky():
        state["calls"] += 1
        if state["calls"] < 3:
            raise ConnectionError("connection reset by peer")
        return "ok"

    handler = _handler(max_retries=5)
    assert handler.execute_with_retry(flaky) == "ok"
    assert state["calls"] == 3
    assert handler.total_retries == 2
    assert handler.consecutive_failures == 2
    assert handler.last_error == "connection reset by peer"


def test_gives_up_after_max_retries():
    def always_fails():
        raise TimeoutError("timed out")

    handler = _handler(max_retries=3)
    with pytest.raises(TimeoutError):
        handler.execute_with_retry(always_fails)
    assert handler.total_retries == 3


def test_non_retryable_error_raised_immediately():
    def boom():
        raise ValueError("bad request")

    handler = _handler(max_retries=5)
    with pytest.raises(ValueError):
        handler.execute_with_retry(boom)
    assert handler.total_retries == 0


def test_rate_limit_error_is_retryable():
    def rate_limited():
        raise RuntimeError("429 Too Many Requests")

    handler = _handler(max_retries=2)
    with pytest.raises(RuntimeError):
        handler.execute_with_retry(rate_limited)
    assert handler.total_retries == 2


def test_server_error_is_retryable():
    def server_error():
        raise RuntimeError("OpenRouter API error (502): bad gateway")

    handler = _handler(max_retries=1)
    with pytest.raises(RuntimeError):
        handler.execute_with_retry(server_error)
    assert handler.total_retries == 1


def test_stop_check_raises_cancellation():
    handler = _handler(max_retries=5)
    with pytest.raises(TranslationCancelled):
        handler.execute_with_retry(lambda: "never", stop_check=lambda: True)


def test_api_suggested_delay_used():
    handler = _handler()
    delay = handler.calculate_delay(0, RuntimeError("Please try again in 2.0s"))
    assert delay == pytest.approx(2.2)  # 2.0s * 1.1 buffer


def test_retry_callback_notified():
    events = []

    def flaky():
        raise ConnectionError("reset")

    handler = _handler(max_retries=1)
    with pytest.raises(ConnectionError):
        handler.execute_with_retry(
            flaky,
            on_retry=lambda attempt, delay, err: events.append((attempt, delay, err)),
        )
    assert len(events) == 1
    assert events[0][0] == 1  # 1-based attempt number
    assert events[0][2] == "reset"


def test_reset_clears_counters():
    state = {"calls": 0}

    def flaky():
        state["calls"] += 1
        if state["calls"] < 2:
            raise ConnectionError("reset")
        return "ok"

    handler = _handler(max_retries=3)
    handler.execute_with_retry(flaky)
    assert handler.total_retries == 1

    handler.reset()
    assert handler.total_retries == 0
    assert handler.consecutive_failures == 0
    assert handler.last_error is None
