"""
Batch processing helpers for Sub-auto.

Contains the token/result models and the pure batch-processing logic extracted
from ``core.translator``: response parsing, token estimation, and the
progressive-smaller-batch recovery loop. This module has no provider or UI
knowledge, which makes it easy to unit test in isolation.
"""

import re
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .subtitle_parser import SubtitleLine


@dataclass
class TokenUsage:
    """Tracks token usage during translation."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def add(self, prompt: int = 0, completion: int = 0):
        """Add tokens to the usage."""
        with self._lock:
            self.prompt_tokens += prompt
            self.completion_tokens += completion
            self.total_tokens = self.prompt_tokens + self.completion_tokens
    
    def reset(self):
        """Reset token counts."""
        with self._lock:
            self.prompt_tokens = 0
            self.completion_tokens = 0
            self.total_tokens = 0
    
    def __str__(self) -> str:
        return f"Tokens: {self.total_tokens:,} (prompt: {self.prompt_tokens:,}, completion: {self.completion_tokens:,})"


@dataclass
class TranslationResult:
    """Result of a translation operation."""
    success: bool
    translated_lines: List[Tuple[int, str]]  # (index, translated_text)
    error_message: str = ""
    tokens_used: TokenUsage = field(default_factory=TokenUsage)


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token."""
    return len(text) // 4


def parse_translation_response(
    response_text: str,
    original_lines: List[SubtitleLine]
) -> List[Tuple[int, str]]:
    """Parse the API response to extract translations.

    Expects lines in the form ``[NUMBER] translated text`` and only keeps
    entries whose index exists in ``original_lines`` (invalid/unknown indices
    are filtered out). Returns a list of ``(index, text)`` tuples in the order
    they appear in the response.
    """
    results = []
    
    # Pattern to match [NUMBER] text
    pattern = r'\[(\d+)\]\s*(.+?)(?=\n\[\d+\]|\Z)'
    matches = re.findall(pattern, response_text, re.DOTALL)
    
    # Create a mapping of expected indices
    expected_indices = {line.index for line in original_lines}
    
    for match in matches:
        try:
            index = int(match[0])
            text = match[1].strip()
            
            if index in expected_indices:
                results.append((index, text))
        except (ValueError, IndexError):
            continue
    
    return results


def translate_with_recovery(
    translate_fn: Callable[[List[SubtitleLine]], TranslationResult],
    lines: List[SubtitleLine],
    stop_check: Callable[[], bool],
    logger,
    on_recovery: Optional[Callable[[str], None]] = None,
    max_recovery_rounds: int = 2,
) -> Tuple[List[Tuple[int, str]], List[SubtitleLine], Dict[int, str], TokenUsage]:
    """Retry missing lines with progressively smaller batches.

    Round 0 translates the full batch. Each following round splits the still
    missing lines into smaller chunks (halving the size every round) and
    re-translates them, until everything is resolved or ``max_recovery_rounds``
    is exhausted.

    Args:
        translate_fn: Callable translating one chunk into a TranslationResult.
        lines: The full batch of subtitle lines to resolve.
        stop_check: Callable returning True when the job was cancelled.
        logger: Logger used for recovery warnings (may be None if recovery
            rounds are never expected to fire).
        on_recovery: Optional callback notified with a progress message when
            an automatic recovery round starts.
        max_recovery_rounds: Number of recovery rounds after the initial one.

    Returns:
        Tuple of (resolved translations, still-pending lines, failure reasons
        per missing line index, token usage accumulated across all rounds).
    """
    resolved: Dict[int, str] = {}
    pending = list(lines)
    failure_reasons: Dict[int, str] = {}
    recovery_tokens = TokenUsage()

    for round_index in range(max_recovery_rounds + 1):
        if not pending or stop_check():
            break

        if round_index == 0:
            chunks = [pending]
        else:
            divisor = 2 ** round_index
            chunk_size = max(1, (len(pending) + divisor - 1) // divisor)
            chunks = [pending[i:i + chunk_size] for i in range(0, len(pending), chunk_size)]
            message = (
                f"Automatic recovery {round_index}/{max_recovery_rounds}: "
                f"retrying {len(pending)} missing line(s) in {len(chunks)} smaller batch(es)..."
            )
            if logger:
                logger.warning(message)
            if on_recovery:
                on_recovery(message)

        next_pending: List[SubtitleLine] = []
        for chunk in chunks:
            if stop_check():
                next_pending.extend(chunk)
                continue

            result = translate_fn(chunk)
            recovery_tokens.add(
                prompt=result.tokens_used.prompt_tokens,
                completion=result.tokens_used.completion_tokens,
            )

            returned = {index: text for index, text in result.translated_lines}
            for line in chunk:
                if line.index in returned:
                    resolved[line.index] = returned[line.index]
                    failure_reasons.pop(line.index, None)
                else:
                    next_pending.append(line)
                    failure_reasons[line.index] = (
                        result.error_message or "Model response did not include this line"
                    )

        pending = next_pending

    translations = [
        (line.index, resolved[line.index])
        for line in lines
        if line.index in resolved
    ]
    return translations, pending, failure_reasons, recovery_tokens
