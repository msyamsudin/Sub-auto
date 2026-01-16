"""
Network Retry Logic for Sub-auto
Handles network failures with robust exponential backoff.
"""

import time
import re
import random
import socket
import urllib.error
import http.client
from typing import Optional, Callable, Dict, Any, TypeVar
from dataclasses import dataclass

from .logger import get_logger

# Generic type for return values
T = TypeVar('T')

# Network-related exceptions to catch for retry
NETWORK_ERRORS = (
    socket.timeout,
    socket.error,
    urllib.error.URLError,
    http.client.HTTPException,
    ConnectionError,
    TimeoutError,
    OSError,
)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 5                    # Maximum number of retry attempts
    initial_delay: float = 1.0              # Initial delay in seconds
    max_delay: float = 60.0                 # Maximum delay in seconds
    exponential_base: float = 2.0           # Base for exponential backoff
    jitter: bool = True                     # Add random jitter to delays
    retry_on_rate_limit: bool = True        # Retry on rate limit errors
    retry_on_server_error: bool = True      # Retry on 5xx server errors


class NetworkRetryHandler:
    """
    Handles network failures with robust retry logic.
    Implements exponential backoff with jitter.
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.consecutive_failures = 0
        self.last_error: Optional[str] = None
        self.total_retries = 0
        self.logger = get_logger()
        
    def reset(self):
        """Reset failure counters."""
        self.consecutive_failures = 0
        self.last_error = None
    
    def calculate_delay(self, attempt: int, error: Optional[Exception] = None) -> float:
        """
        Calculate delay for the next retry with exponential backoff.
        Parses API-suggested retry delays from error messages when available.
        
        Args:
            attempt: Current attempt number (0-based)
            error: Optional exception that may contain retry-after information
            
        Returns:
            Delay in seconds
        """
        # Check if error contains specific retry time (e.g., Groq's "Please try again in X.XXs")
        if error:
            error_str = str(error)
            # Match patterns like "try again in 1.57s" or "retry after 2.5s"
            match = re.search(r'(?:try again in|retry after)\s+([\d.]+)\s*s', error_str, re.IGNORECASE)
            if match:
                suggested_delay = float(match.group(1))
                # Add small buffer (10%) to be safe
                suggested_delay = suggested_delay * 1.1
                self.logger.info(f"Using API-suggested retry delay: {suggested_delay:.2f}s")
                return max(suggested_delay, 0.1)
        
        # Fallback to exponential backoff
        delay = self.config.initial_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            # Add ±25% random jitter
            jitter_range = delay * 0.25
            delay = delay + random.uniform(-jitter_range, jitter_range)
        
        return max(0.1, delay)  # Minimum 100ms delay
    
    def is_retryable_error(self, error: Exception) -> bool:
        """
        Check if an error is retryable.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if the error should trigger a retry
        """
        error_str = str(error).lower()
        
        # Network-related errors
        if isinstance(error, NETWORK_ERRORS):
            return True
        
        # Check error message for common network issues
        network_keywords = [
            "connection", "timeout", "timed out", "network",
            "unreachable", "reset", "refused", "broken pipe",
            "eof", "ssl", "certificate", "handshake",
            "dns", "resolve", "socket", "connect", "incomplete"
        ]
        if any(kw in error_str for kw in network_keywords):
            return True
        
        # Rate limiting errors
        if self.config.retry_on_rate_limit:
            rate_limit_keywords = ["rate", "limit", "quota", "429", "too many"]
            if any(kw in error_str for kw in rate_limit_keywords):
                return True
        
        # Server errors (5xx)
        if self.config.retry_on_server_error:
            server_error_keywords = ["500", "502", "503", "504", "server error", "internal error"]
            if any(kw in error_str for kw in server_error_keywords):
                return True
        
        # Google API specific errors
        google_retryable = [
            "resource_exhausted", "unavailable", "deadline_exceeded",
            "internal", "aborted"
        ]
        if any(kw in error_str for kw in google_retryable):
            return True
        
        return False
    
    def execute_with_retry(
        self, 
        func: Callable[[], T], 
        on_retry: Optional[Callable[[int, float, str], None]] = None,
        stop_check: Optional[Callable[[], bool]] = None
    ) -> T:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            on_retry: Callback(attempt, delay, error_msg)
            
        Returns:
            Result of the function
            
        Raises:
            Exception: If max retries exceeded
        """
        self.retry_count = 0
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if stop_check and stop_check():
                     raise KeyboardInterrupt("Stopped by user")
                
                if attempt > 0:
                    self.logger.info(f"Retry attempt {attempt}/{self.config.max_retries}...")
                return func()
            except Exception as e:
                last_error = e
                if not self.is_retryable_error(e) or attempt == self.config.max_retries:
                    self.logger.error(f"Non-retriable error or max retries reached: {e}")
                    raise e
                
                # Calculate delay (pass error for smart retry-after parsing)
                delay = self.calculate_delay(attempt, e)
                error_msg = str(e)
                
                self.logger.warning(f"Error: {error_msg}. Retrying in {delay:.2f}s...")
                
                # Call callbacks
                if on_retry:
                    on_retry(attempt + 1, delay, str(e))
                
                # Sleep with interrupt check
                sleep_step = 0.1
                slept = 0.0
                while slept < delay:
                    if stop_check and stop_check():
                        raise KeyboardInterrupt("Stopped by user")
                    time.sleep(min(sleep_step, delay - slept))
                    slept += sleep_step
        
        # All retries exhausted
        if last_error:
            raise last_error
    
    def get_status(self) -> Dict[str, Any]:
        """Get current retry handler status."""
        return {
            "consecutive_failures": self.consecutive_failures,
            "total_retries": self.total_retries,
            "last_error": self.last_error
        }
