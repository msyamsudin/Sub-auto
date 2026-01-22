"""
Translator for Sub-auto
Handles translation of subtitle text using LLM providers.
"""

from typing import List, Tuple, Optional, Callable, Dict, Any, TypeVar
from dataclasses import dataclass, field
import threading
import time
import re

from .subtitle_parser import SubtitleLine
from .logger import get_logger
from .llm_provider import PolicyViolationError
from .style_handler import StyleHandler
from .retry_handler import NetworkRetryHandler, RetryConfig
from .model_manager import ModelManager, get_api_manager, validate_and_save_api_key
from .prompt_manager import PromptManager

# Generic type for return values
T = TypeVar('T')


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


class Translator:
    """Translator using configured LLM provider."""

    def __init__(
        self, 
        model_manager: Optional[ModelManager] = None,
        retry_config: Optional[RetryConfig] = None,
        prompt_manager: Optional[PromptManager] = None
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
        self.style_handler = StyleHandler()  # Initialize StyleHandler
        self.prompt_manager = prompt_manager or PromptManager()  # Initialize PromptManager
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
            context_processed = []
            for line in context_lines[-3:]:
                 # Use simple clean for context to avoid confusion
                text, _ = self.style_handler.prepare_for_translation(line.text, line.style)
                context_processed.append(f"[PREV] {text}")
            context = "\n".join(context_processed)
        else:
            context = "(No previous context)"
        
        # Prepare lines and store metadata
        lines_text_parts = []
        style_metadata = {}
        
        for line in lines:
            prepared_text, metadata = self.style_handler.prepare_for_translation(line.text, line.style)
            style_metadata[line.index] = metadata
            lines_text_parts.append(f"[{line.index}] {prepared_text}")
            
        lines_text = "\n".join(lines_text_parts)
        
        # Build prompt - get from PromptManager
        prompt_template = self.prompt_manager.get_active_prompt()
        prompt = prompt_template.format(
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
            
            # Restore styles
            final_translated = []
            for idx, text in translated:
                if idx in style_metadata:
                    restored_text = self.style_handler.restore_styles(text, style_metadata[idx])
                    final_translated.append((idx, restored_text))
                else:
                    final_translated.append((idx, text))

            if len(final_translated) == len(lines):
                self.logger.info(f"✅ Batch complete: {len(final_translated)} lines translated in {batch_elapsed:.2f}s")
                return TranslationResult(
                    success=True,
                    translated_lines=final_translated,
                    tokens_used=batch_tokens
                )
            else:
                self.logger.warning(f"⚠️ Partial batch: got {len(final_translated)}/{len(lines)} lines in {batch_elapsed:.2f}s")
                return TranslationResult(
                    success=True,
                    translated_lines=final_translated,
                    error_message=f"Partial: expected {len(lines)}, got {len(final_translated)}",
                )
                    
        except PolicyViolationError as e:
            # Handle Policy Violation (Fallback)
            self.logger.warning(f"⚠️ Policy Violation detected with model {self.current_model_name}: {e}")
            
            # Determine fallback model
            fallback_model = self.model_manager.config.fallback_model
            
            if not fallback_model:
                # Auto-select fallback (non-Bedrock)
                self.logger.info("Configuration 'fallback_model' not set. Attempting auto-selection...")
                for model in self.model_manager.available_models:
                    name_lower = model.name.lower()
                    # Filter out Bedrock and current model
                    if "bedrock" not in name_lower and model.name != self.current_model_name:
                        # Prefer known stable providers if possible
                        if "openai" in name_lower or "google" in name_lower or "meta" in name_lower:
                            fallback_model = model.name
                            break
                
                # If still no fallback, just take the first non-current, non-bedrock one
                if not fallback_model:
                    for model in self.model_manager.available_models:
                        if "bedrock" not in model.name.lower() and model.name != self.current_model_name:
                            fallback_model = model.name
                            break
            
            if fallback_model:
                self.logger.warning(f"🛡️ FALLBACK ACTIVATED: Routing segment to {fallback_model} due to policy violation.")
                try:
                     # Calculate prompt tokens again as we are retrying
                    fallback_start = time.time()
                    self.logger.info(f"🌐 Calling API (Fallback): {fallback_model}")
                    
                    response_text = self.model_manager.provider.generate_content(
                        fallback_model,
                        prompt
                    )
                    
                    fallback_elapsed = time.time() - fallback_start
                    
                    # Track tokens (approx info)
                    estimated_completion_tokens = len(response_text) // 4
                    batch_tokens.add(
                        prompt=estimated_prompt_tokens,
                        completion=estimated_completion_tokens
                    )
                    self.token_usage.add(
                        prompt=estimated_prompt_tokens,
                        completion=estimated_completion_tokens
                    )
                    
                    self.logger.info(f"✅ Fallback response received: {len(response_text)} chars in {fallback_elapsed:.2f}s")
                    
                    # Parse response
                    translated = self._parse_response(response_text, lines)
                     
                    # Restore styles for fallback too
                    final_translated = []
                    for idx, text in translated:
                        if idx in style_metadata:
                            restored_text = self.style_handler.restore_styles(text, style_metadata[idx])
                            final_translated.append((idx, restored_text))
                        else:
                            final_translated.append((idx, text))

                    batch_elapsed = time.time() - batch_start_time
                    return TranslationResult(
                        success=True,
                        translated_lines=final_translated,
                        error_message="Success (Fallback used)",
                        tokens_used=batch_tokens
                    )

                except Exception as fallback_error:
                    self.logger.error(f"❌ Fallback failed: {fallback_error}")
                    # Fall through to return failure
            else:
                 self.logger.error("❌ No suitable fallback model found.")

            return TranslationResult(
                success=False,
                translated_lines=[],
                error_message=f"Policy Violation: {e} (Fallback failed or unavailable)",
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
                     pass

            else:
                error_msg = f"Batch {batch_idx + 1} failed: {result.error_message}"
                self.logger.error(error_msg)
                errors.append(error_msg)
                # Keep original lines for failed ones
                for line in batch:
                    if line.index not in completed_indices:
                        all_translations.append((line.index, line.text))
            
            # Delay between batches to avoid rate limits
            time_module.sleep(1.5)
        
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
