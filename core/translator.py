"""
Translator for Sub-auto
Handles translation of subtitle text using LLM providers.
"""

from typing import List, Tuple, Optional, Callable, Dict, Any
import time

from .subtitle_parser import SubtitleLine
from .logger import get_logger
from .llm_provider import PolicyViolationError
from .exceptions import TranslationCancelled
from .style_handler import StyleHandler
from .retry_handler import NetworkRetryHandler, RetryConfig
from .model_manager import ModelManager, get_api_manager
from .prompt_manager import PromptManager
from .batch_processor import (
    TokenUsage,
    TranslationResult,
    estimate_tokens,
    parse_translation_response,
    translate_with_recovery,
)


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
        on_retry: Optional[Callable[[int, float, str], None]] = None,
        anime_title: Optional[str] = None
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
        context_parts = []
        if anime_title:
            context_parts.append(f"Konteks Anime: {anime_title}")

        if context_lines:
            context_processed = []
            for line in context_lines[-3:]:
                 # Use simple clean for context to avoid confusion
                text, _ = self.style_handler.prepare_for_translation(line.text, line.style)
                context_processed.append(f"[PREV] {text}")
            context_parts.append("\n".join(context_processed))
            
        context = "\n".join(context_parts) if context_parts else "(No previous context)"
        
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
        estimated_prompt_tokens = estimate_tokens(prompt)
        self.logger.info(f"📝 Prompt size: {len(prompt)} chars (~{estimated_prompt_tokens} tokens)")
        
        def do_translation():
            """Inner function to execute translation."""
            if not self.model_manager.provider:
                raise ValueError("Provider not initialized")
            
            self.logger.info(f"🌐 Calling API: {self.current_model_name}")
            generation = self.model_manager.provider.generate_content(
                self.current_model_name,
                prompt
            )
            
            if not generation.text:
                raise ValueError("Empty response from API")
            
            if self.should_stop:
                raise TranslationCancelled("Stopped by user")
            
            return generation
        
        def on_retry_internal(attempt: int, delay: float, error_msg: str):
            """Internal retry callback."""
            self.logger.warning(f"🔄 Retry {attempt}: waiting {delay:.1f}s - {error_msg[:50]}...")
            self._reinitialize_model()
            if retry_callback:
                retry_callback(attempt, delay, error_msg)
        
        try:
            # Use retry handler for robust API calls
            api_start = time.time()
            generation = self.retry_handler.execute_with_retry(
                do_translation,
                on_retry=on_retry_internal,
                stop_check=lambda: self.should_stop
            )
            api_elapsed = time.time() - api_start
            response_text = generation.text
            
            # Track tokens: prefer real usage reported by the provider, fall
            # back to a rough estimate when the provider omits usage data.
            prompt_tokens = generation.prompt_tokens or estimated_prompt_tokens
            completion_tokens = generation.completion_tokens or estimate_tokens(response_text)
            batch_tokens.add(
                prompt=prompt_tokens,
                completion=completion_tokens
            )
            self.token_usage.add(
                prompt=prompt_tokens,
                completion=completion_tokens
            )
            
            self.logger.info(
                f"✅ API response received: {len(response_text)} chars "
                f"({prompt_tokens:,} prompt + {completion_tokens:,} completion tokens) "
                f"in {api_elapsed:.2f}s"
            )
            
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
                    tokens_used=batch_tokens,
                )
                    
        except TranslationCancelled:
            # User-initiated cancellation: propagate cleanly so the worker
            # thread exits without being treated as a translation failure.
            raise

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
                    
                    generation = self.model_manager.provider.generate_content(
                        fallback_model,
                        prompt
                    )
                    response_text = generation.text
                    
                    fallback_elapsed = time.time() - fallback_start
                    
                    # Track tokens: prefer real usage, fall back to estimate
                    prompt_tokens = generation.prompt_tokens or estimated_prompt_tokens
                    completion_tokens = generation.completion_tokens or estimate_tokens(response_text)
                    batch_tokens.add(
                        prompt=prompt_tokens,
                        completion=completion_tokens
                    )
                    self.token_usage.add(
                        prompt=prompt_tokens,
                        completion=completion_tokens
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
        return parse_translation_response(response_text, original_lines)

    def _translate_batch_with_recovery(
        self,
        lines: List[SubtitleLine],
        source_lang: str,
        target_lang: str,
        context_lines: List[SubtitleLine],
        anime_title: Optional[str],
        on_recovery: Optional[Callable[[str], None]] = None,
        max_recovery_rounds: int = 2,
    ) -> Tuple[List[Tuple[int, str]], List[SubtitleLine], Dict[int, str], TokenUsage]:
        """Retry missing lines with progressively smaller batches."""

        def translate_chunk(chunk: List[SubtitleLine]) -> TranslationResult:
            return self.translate_batch(
                lines=chunk,
                source_lang=source_lang,
                target_lang=target_lang,
                context_lines=context_lines,
                anime_title=anime_title,
            )

        return translate_with_recovery(
            translate_fn=translate_chunk,
            lines=lines,
            stop_check=lambda: self.should_stop,
            logger=self.logger,
            on_recovery=on_recovery,
            max_recovery_rounds=max_recovery_rounds,
        )
    
    def translate_all(
        self,
        lines: List[SubtitleLine],
        source_lang: str = "English",
        target_lang: str = "Indonesian",
        batch_size: int = 25,
        progress_callback: Optional[Callable[[int, int, str, TokenUsage], None]] = None,
        state_manager: Any = None,
        anime_title: Optional[str] = None
    ) -> Tuple[List[Tuple[int, str]], List[Dict[str, Any]], TokenUsage]:
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
        
        # Delay between batches to avoid rate limits (configurable; set to 0
        # for local providers like Ollama).
        batch_delay = getattr(self.model_manager.config, "batch_delay_seconds", 1.5) or 0.0
        batch_delay = max(0.0, float(batch_delay))
        
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
            
            def recovery_progress(message: str):
                if progress_callback:
                    progress_callback(
                        len(completed_indices), total_lines, message, self.token_usage
                    )

            pending_batch = [line for line in batch if line.index not in completed_indices]
            recovered, unresolved, failure_reasons, batch_tokens = self._translate_batch_with_recovery(
                lines=pending_batch,
                source_lang=source_lang,
                target_lang=target_lang,
                context_lines=context_lines,
                anime_title=anime_title,
                on_recovery=recovery_progress,
            )

            new_translations = []
            for idx, text in recovered:
                if idx not in completed_indices:
                    all_translations.append((idx, text))
                    new_translations.append((idx, text))
                    completed_indices.add(idx)

            if state_manager:
                state_manager.update_progress(
                    new_translations=new_translations,
                    batch_index=batch_idx,
                    prompt_tokens=batch_tokens.prompt_tokens,
                    completion_tokens=batch_tokens.completion_tokens,
                )

            context_lines = batch[-3:] if len(batch) >= 3 else batch

            for line in unresolved:
                reason = failure_reasons.get(line.index, "Automatic recovery exhausted")
                self.logger.error(
                    f"Line {line.index} failed after automatic recovery: {reason}"
                )
                errors.append({
                    "entry_index": line.index,
                    "severity": "error",
                    "reason": f"Automatic recovery exhausted: {reason}"[:240],
                })
                if line.index not in completed_indices:
                    all_translations.append((line.index, line.text))
            
            # Delay between batches to avoid rate limits (skipped after the last batch)
            if batch_idx < total_batches - 1 and batch_delay > 0:
                time_module.sleep(batch_delay)
        
        all_translations.sort(key=lambda x: x[0])
        
        if progress_callback:
            status = (
                f"Translation complete with {len(errors)} issue(s)"
                if errors
                else "Translation complete!"
            )
            progress_callback(total_lines, total_lines, status, self.token_usage)
        
        job_elapsed = time_module.time() - job_start_time
        
        self.logger.info("=" * 50)
        self.logger.info(f"🎉 Translation job complete!")
        self.logger.info(f"📊 Lines translated: {len(all_translations)}/{total_lines}")
        self.logger.info(f"⏱️ Total time: {job_elapsed:.1f}s ({job_elapsed/60:.1f} minutes)")
        self.logger.info(f"🔢 Tokens: {self.token_usage.prompt_tokens:,} prompt + {self.token_usage.completion_tokens:,} completion = {self.token_usage.total_tokens:,} total")
        if errors:
            self.logger.warning(f"⚠️ Errors: {len(errors)} lines failed after automatic recovery")
        self.logger.info("=" * 50)
        
        return all_translations, errors, self.token_usage
