"""
Translator for Sub-auto
Handles translation of subtitle text using LLM providers.
Includes API validation, model selection, token tracking, and robust retry logic.
"""

from typing import List, Tuple, Optional, Callable, Dict, Any, TypeVar
from dataclasses import dataclass, field
import time
import re
import random
import socket
import urllib.error
import http.client

from .config_manager import get_config
from .subtitle_parser import SubtitleLine
from .logger import get_logger
from .logger import get_logger
from .llm_provider import LLMProvider, OpenRouterProvider, OllamaProvider, GroqProvider, ModelInfo

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
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the next retry with exponential backoff.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
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
                
                # Calculate delay
                delay = self.calculate_delay(attempt)
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


import threading

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


@dataclass
class APIValidationResult:
    """Result of API key validation."""
    is_valid: bool
    message: str
    available_models: List[ModelInfo] = field(default_factory=list)


class ModelManager:
    """Manages LLM providers and model selection."""
    
    def __init__(self):
        self.provider_name: str = "openrouter"
        self.provider: Optional[LLMProvider] = None
        self.is_configured = False
        self.available_models: List[ModelInfo] = []
        self.selected_model: Optional[str] = None
        self.config = get_config()
    
    def configure(self, provider_name: Optional[str] = None):
        """Configure the active provider."""
        self.provider_name = provider_name or self.config.provider
        
        if self.provider_name == "openrouter":
            self.provider = OpenRouterProvider(self.config.openrouter_api_key)
        elif self.provider_name == "ollama":
            self.provider = OllamaProvider(
                base_url=self.config.ollama_base_url
            )
        elif self.provider_name == "groq":
            self.provider = GroqProvider(self.config.groq_api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider_name}")

    def validate_connection(self) -> APIValidationResult:
        """
        Validate provider connection and retrieve available models.
        
        Returns:
            APIValidationResult with validation status and available models
        """
        self.configure()  # Re-configure to ensure latest settings
        
        if not self.provider:
            return APIValidationResult(False, "Provider not initialized")
            
        is_valid, message = self.provider.validate_connection()
        
        if not is_valid:
            return APIValidationResult(False, message)
            
        try:
            models = self.provider.list_models()
            
            if not models:
                return APIValidationResult(
                    is_valid=False,
                    message="Connection valid but no models found"
                )
            
            # Store state
            self.is_configured = True
            self.available_models = models
            
            # Auto-select model
            self._auto_select_model()
            
            return APIValidationResult(
                is_valid=True,
                message=f"Connected! Found {len(models)} models.",
                available_models=models
            )
            
        except Exception as e:
            return APIValidationResult(False, f"Validation error: {str(e)}")
    
    def _auto_select_model(self):
        """Auto-select the best default model or use user's saved preference."""
        # First, check if user has a saved model preference in config
        if self.provider_name == "openrouter":
            saved_model = self.config.openrouter_model
            if saved_model:
                # Try to find and select the saved model
                for model in self.available_models:
                    if model.name == saved_model:
                        self.selected_model = model.name
                        return
            
            # Fallback to preferred free models
            preferred_models = [
                "google/gemini-2.0-flash-exp:free",
                "meta-llama/llama-3-8b-instruct:free",
                "huggingfaceh4/zephyr-7b-beta:free",
                "mistralai/mistral-7b-instruct:free",
                "openai/gpt-3.5-turbo"
            ]
        elif self.provider_name == "ollama":
            preferred_models = [
                self.config.ollama_model,
                "llama3",
                "mistral",
                "gemma"
            ]
        elif self.provider_name == "groq":
            preferred_models = [
                self.config.groq_model,
                "llama3-70b-8192",
                "llama3-8b-8192"
            ]
        else:
            preferred_models = []
        
        for preferred in preferred_models:
            for model in self.available_models:
                if preferred.lower() in model.name.lower():
                    self.selected_model = model.name
                    return
        
        # Fallback
        if self.available_models:
            self.selected_model = self.available_models[0].name
    
    def select_model(self, model_name: str) -> bool:
        """Select a model by name."""
        # Try exact match
        for model in self.available_models:
            if model.name == model_name or model.short_name == model_name:
                self.selected_model = model.name
                return True
        
        # Try partial match (case-insensitive)
        for model in self.available_models:
            if model_name.lower() in model.name.lower():
                self.selected_model = model.name
                return True
                
        return False
    
    def get_model_display_names(self) -> List[str]:
        """Get list of model display names."""
        return [model.short_name for model in self.available_models]
    
    def get_selected_model_info(self) -> Optional[ModelInfo]:
        """Get the ModelInfo for the currently selected model."""
        if not self.selected_model:
            return None
        
        for model in self.available_models:
            if model.name == self.selected_model or model.short_name == self.selected_model:
                return model
        
        return None


class Translator:
    """Translator using configured LLM provider."""
    
    # Translation prompt template
    TRANSLATION_PROMPT = """You are a professional subtitle translator. Translate the following subtitle lines from {source_lang} to {target_lang}.

CRITICAL RULES:
1. Use natural, spoken Indonesian suitable for subtitles
2. Prioritize meaning, tone, and emotion over literal translation
3. Do not force-translate commonly used loanwords
4. Keep names, proper nouns, and Japanese honorifics unchanged
5. Preserve formatting markers like \\N exactly
6. If a line is already in the target language or is a non-dialogue cue, keep it as-is
7. Keep translations concise and subtitle-friendly

CONTEXT:
{context}

TRANSLATE:
{lines}

OUTPUT:
[NUMBER] translated text"""

    def __init__(
        self, 
        model_manager: Optional[ModelManager] = None,
        retry_config: Optional[RetryConfig] = None
    ):
        """Initialize Translator."""
        if model_manager:
            self.model_manager = model_manager
        else:
            self.model_manager = ModelManager()
            # Try to validate if enabled
            if self.model_manager.config.provider == "openrouter" and self.model_manager.config.openrouter_api_key:
                self.model_manager.validate_connection()
            elif self.model_manager.config.provider == "ollama":
                self.model_manager.validate_connection()
            elif self.model_manager.config.provider == "groq" and self.model_manager.config.groq_api_key:
                self.model_manager.validate_connection()
        
        self.token_usage = TokenUsage()
        self.retry_handler = NetworkRetryHandler(retry_config)
        self._on_retry_callback: Optional[Callable[[int, float, str], None]] = None
        self.logger = get_logger()
        self.should_stop = False
        self.is_paused = False
    
    @property
    def current_model_name(self) -> str:
        """Get the current model name."""
        return self.model_manager.selected_model or "unknown"
    
    def initialize(self) -> Tuple[bool, str]:
        """Initialize the provider connection."""
        if not self.model_manager.is_configured:
            return False, "Provider not configured. Please validate connection first."
            
        try:
            self.model_manager.configure()
            # Ensure provider is ready
            valid, msg = self.model_manager.provider.validate_connection()
            if not valid:
                return False, msg
                
            self.token_usage.reset()
            return True, f"Initialized with model: {self.current_model_name}"
                
        except Exception as e:
            self.logger.error(f"Failed to initialize translator: {e}")
            return False, f"Failed to initialize: {str(e)}"
    
    def set_retry_callback(self, callback: Callable[[int, float, str], None]):
        """Set a callback to be notified of retry attempts."""
        self._on_retry_callback = callback
    
    def _reinitialize_model(self) -> bool:
        """Attempt to reinitialize the model connection."""
        try:
            self.model_manager.configure()
            return True
        except Exception:
            return False
    
    def translate_batch(
        self,
        lines: List[SubtitleLine],
        source_lang: str = "English",
        target_lang: str = "Indonesian",
        context_lines: Optional[List[SubtitleLine]] = None,
        on_retry: Optional[Callable[[int, float, str], None]] = None
    ) -> TranslationResult:
        """Translate a batch of subtitle lines."""
        import time
        batch_start_time = time.time()
        
        self.logger.info(f"📦 Starting batch translation: {len(lines)} lines ({source_lang} → {target_lang})")
        
        if not self.model_manager.is_configured:
            success, msg = self.initialize()
            if not success:
                self.logger.error(f"Failed to initialize: {msg}")
                return TranslationResult(False, [], msg)
        
        batch_tokens = TokenUsage()
        retry_callback = on_retry or self._on_retry_callback
        
        # Build context string
        context = ""
        if context_lines:
            context = "\n".join([
                f"[PREV] {line.clean_text()}" 
                for line in context_lines[-3:]  # Last 3 lines for context
            ])
        else:
            context = "(No previous context)"
        
        # Build lines to translate
        lines_text = "\n".join([
            f"[{line.index}] {line.text}"
            for line in lines
        ])
        
        # Build prompt
        prompt = self.TRANSLATION_PROMPT.format(
            source_lang=source_lang,
            target_lang=target_lang,
            context=context,
            lines=lines_text
        )
        
        # Estimate prompt tokens (rough estimate: ~4 chars per token)
        estimated_prompt_tokens = len(prompt) // 4
        self.logger.info(f"📝 Prompt size: {len(prompt)} chars (~{estimated_prompt_tokens} tokens)")
        
        def do_translation():
            """Inner function to execute translation."""
            if not self.model_manager.provider:
                raise ValueError("Provider not initialized")
            
            self.logger.info(f"🌐 Calling API: {self.current_model_name}")
            response_text = self.model_manager.provider.generate_content(
                self.current_model_name,
                prompt
            )
            
            if not response_text:
                raise ValueError("Empty response from API")
            
            if self.should_stop:
                raise KeyboardInterrupt("Stopped by user")
            
            return response_text
        
        def on_retry_internal(attempt: int, delay: float, error_msg: str):
            """Internal retry callback."""
            self.logger.warning(f"🔄 Retry {attempt}: waiting {delay:.1f}s - {error_msg[:50]}...")
            self._reinitialize_model()
            if retry_callback:
                retry_callback(attempt, delay, error_msg)
        
        try:
            # Use retry handler for robust API calls
            api_start = time.time()
            response_text = self.retry_handler.execute_with_retry(
                do_translation,
                on_retry=on_retry_internal,
                stop_check=lambda: self.should_stop
            )
            api_elapsed = time.time() - api_start
            
            # Track tokens
            estimated_completion_tokens = len(response_text) // 4
            batch_tokens.add(
                prompt=estimated_prompt_tokens,
                completion=estimated_completion_tokens
            )
            self.token_usage.add(
                prompt=estimated_prompt_tokens,
                completion=estimated_completion_tokens
            )
            
            self.logger.info(f"✅ API response received: {len(response_text)} chars (~{estimated_completion_tokens} tokens) in {api_elapsed:.2f}s")
            
            # Parse response
            translated = self._parse_response(response_text, lines)
            
            batch_elapsed = time.time() - batch_start_time
            
            if len(translated) == len(lines):
                self.logger.info(f"✅ Batch complete: {len(translated)} lines translated in {batch_elapsed:.2f}s")
                return TranslationResult(
                    success=True,
                    translated_lines=translated,
                    tokens_used=batch_tokens
                )
            else:
                self.logger.warning(f"⚠️ Partial batch: got {len(translated)}/{len(lines)} lines in {batch_elapsed:.2f}s")
                return TranslationResult(
                    success=True,
                    translated_lines=translated,
                    error_message=f"Partial: expected {len(lines)}, got {len(translated)}",
                    tokens_used=batch_tokens
                )
                    
        except Exception as e:
            error_msg = str(e)
            retry_status = self.retry_handler.get_status()
            batch_elapsed = time.time() - batch_start_time
            
            self.logger.error(f"❌ Batch failed after {retry_status['total_retries']} retries in {batch_elapsed:.2f}s: {error_msg[:100]}")
            
            return TranslationResult(
                success=False,
                translated_lines=[],
                error_message=f"Translation failed after {retry_status['total_retries']} retries: {error_msg}",
                tokens_used=batch_tokens
            )
    
    def _parse_response(
        self, 
        response_text: str, 
        original_lines: List[SubtitleLine]
    ) -> List[Tuple[int, str]]:
        """Parse the API response to extract translations."""
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
    
    def translate_all(
        self,
        lines: List[SubtitleLine],
        source_lang: str = "English",
        target_lang: str = "Indonesian",
        batch_size: int = 25,
        progress_callback: Optional[Callable[[int, int, str, TokenUsage], None]] = None,
        state_manager: Any = None
    ) -> Tuple[List[Tuple[int, str]], List[str], TokenUsage]:
        """Translate all subtitle lines with progress tracking (Sequential)."""
        import time as time_module
        
        job_start_time = time_module.time()
        
        all_translations = []
        errors = []
        total_lines = len(lines)
        
        self.token_usage.reset()
        
        self.logger.info(f"🚀 Starting translation job: {total_lines} lines, batch size {batch_size}")
        self.logger.info(f"⚡ Mode: Sequential")
        self.logger.info(f"🔤 Languages: {source_lang} → {target_lang}")
        self.logger.info(f"🤖 Model: {self.current_model_name}")
        
        # Check if resuming
        completed_indices = set()
        if state_manager:
            completed_indices = state_manager.get_completed_indices()
            all_translations = state_manager.get_completed_translations()
            all_translations.sort(key=lambda x: x[0])
            
            if state_manager.current_state:
                self.token_usage.prompt_tokens = state_manager.current_state.prompt_tokens_used
                self.token_usage.completion_tokens = state_manager.current_state.completion_tokens_used
                self.token_usage.total_tokens = self.token_usage.prompt_tokens + self.token_usage.completion_tokens
            
            if completed_indices:
                self.logger.info(f"📂 Resuming: {len(completed_indices)} lines already completed")
        
        # Split into batches
        batches = [lines[i:i + batch_size] for i in range(0, len(lines), batch_size)]
        total_batches = len(batches)
        
        self.logger.info(f"📦 Total batches: {total_batches}")
        
        context_lines = []
        
        for batch_idx, batch in enumerate(batches):
            # Check for stop
            if self.should_stop:
                self.logger.info("🛑 Translation stopped by user")
                break
            
            # Check for pause
            while self.is_paused:
                if self.should_stop: break
                time_module.sleep(0.5)
            
            # Check if this batch is already fully translated
            batch_indices = {line.index for line in batch}
            if batch_indices.issubset(completed_indices):
                self.logger.info(f"⏭️ Batch {batch_idx + 1}/{total_batches}: skipped (already completed)")
                context_lines = batch[-3:] if len(batch) >= 3 else batch
                continue
            
            self.logger.info(f"📦 Batch {batch_idx + 1}/{total_batches}: processing {len(batch)} lines...")
            
            current_count = len(completed_indices) + len(batch) # Approximation for UI
            
            if progress_callback:
                progress_callback(
                    len(completed_indices), 
                    total_lines,
                    f"Translating batch {batch_idx + 1}/{total_batches}...",
                    self.token_usage
                )
            
            result = self.translate_batch(
                lines=batch,
                source_lang=source_lang,
                target_lang=target_lang,
                context_lines=context_lines
            )
            
            if result.success:
                new_translations = []
                for idx, text in result.translated_lines:
                    if idx not in completed_indices:
                        all_translations.append((idx, text))
                        new_translations.append((idx, text))
                        completed_indices.add(idx)
                
                # Update progress
                if state_manager:
                    state_manager.update_progress(
                        new_translations=new_translations,
                        batch_index=batch_idx,
                        prompt_tokens=result.tokens_used.prompt_tokens,
                        completion_tokens=result.tokens_used.completion_tokens
                    )
                
                context_lines = batch[-3:] if len(batch) >= 3 else batch
                
                # Check for partiality in a "successful" batch
                if len(result.translated_lines) < len(batch):
                     self.logger.warning(f"⚠️ Batch {batch_idx+1} partial: {len(result.translated_lines)}/{len(batch)}")
                     # In sequential mode, we could try to retry missing lines immediately, 
                     # but translate_batch already retries internally. 
                     # We'll just accept what we got or log it.
                     pass

            else:
                error_msg = f"Batch {batch_idx + 1} failed: {result.error_message}"
                self.logger.error(error_msg)
                errors.append(error_msg)
                # Keep original lines for failed ones
                for line in batch:
                    if line.index not in completed_indices:
                        all_translations.append((line.index, line.text))
            
            # Small delay between batches to be nice to API
            time_module.sleep(0.5)
        
        all_translations.sort(key=lambda x: x[0])
        
        if progress_callback:
            progress_callback(total_lines, total_lines, "Translation complete!", self.token_usage)
        
        job_elapsed = time_module.time() - job_start_time
        
        self.logger.info("=" * 50)
        self.logger.info(f"🎉 Translation job complete!")
        self.logger.info(f"📊 Lines translated: {len(all_translations)}/{total_lines}")
        self.logger.info(f"⏱️ Total time: {job_elapsed:.1f}s ({job_elapsed/60:.1f} minutes)")
        self.logger.info(f"🔢 Tokens: {self.token_usage.prompt_tokens:,} prompt + {self.token_usage.completion_tokens:,} completion = {self.token_usage.total_tokens:,} total")
        if errors:
            self.logger.warning(f"⚠️ Errors: {len(errors)} batches failed")
        self.logger.info("=" * 50)
        
        return all_translations, errors, self.token_usage


# Global API manager instance
_model_manager: Optional[ModelManager] = None


def get_api_manager() -> ModelManager:
    """Get the global ModelManager instance."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager


def validate_and_save_api_key(api_key: str) -> APIValidationResult:
    """Validate API key (legacy bridge)."""
    # This is slightly broken in new design as validation depends on provider
    # But usually this is called when user enters OpenRouter key
    manager = get_api_manager()
    manager.config.openrouter_api_key = api_key
    manager.config.provider = "openrouter"
    return manager.validate_connection()
