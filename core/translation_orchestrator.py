"""
Translation Orchestrator Service
Manages the lifecycle of a subtitle translation process (run, pause, resume, cancel).
"""

import time
import threading
from pathlib import Path
from typing import Callable, Optional, Dict, Any

from .config_manager import get_config
from .mkv_handler import MKVHandler
from .subtitle_parser import SubtitleParser
from .translator import Translator, get_api_manager, TokenUsage
from .state_manager import get_state_manager
from .logger import get_logger

logger = get_logger()

class TranslationOrchestrator:
    """Manages the lifecycle of the translation process in the background."""
    
    def __init__(self, mkv_handler: MKVHandler):
        self.mkv_handler = mkv_handler
        self.config = get_config()
        self.state_manager = get_state_manager()
        self.active_translator: Optional[Translator] = None
        
        self.is_processing = False
        self.is_paused = False
        self.should_cancel = False
        
        self.token_usage = TokenUsage()
        
        # Callbacks
        self.on_progress: Optional[Callable[[int, int, str, TokenUsage], None]] = None
        self.on_complete: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
    def set_callbacks(
        self,
        on_progress: Callable[[int, int, str, TokenUsage], None],
        on_complete: Callable[[Dict[str, Any]], None],
        on_error: Callable[[str], None]
    ):
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error
        
    def start_translation(
        self,
        file_path: str,
        track_id: int,
        source_lang: str,
        target_lang: str,
        model_name: str,
        anime_title: Optional[str] = None
    ):
        """Start the translation process in a background thread."""
        self.is_processing = True
        self.is_paused = False
        self.should_cancel = False
        
        thread = threading.Thread(
            target=self._run_translation_thread,
            args=(file_path, track_id, source_lang, target_lang, model_name, anime_title),
            daemon=True
        )
        thread.start()
        
    def _run_translation_thread(
        self,
        file_path: str,
        track_id: int,
        source_lang: str,
        target_lang: str,
        model_name: str,
        anime_title: Optional[str]
    ):
        start_time = time.time()
        lines_count = 0
        
        api_manager = get_api_manager()
        temp_translator = Translator(model_manager=api_manager)
        prompt_used = temp_translator.prompt_manager.get_active_prompt_name()
        
        try:
            # Check for resume state
            resume_state = None
            if self.state_manager.has_resumable_state(file_path):
                state = self.state_manager.load()
                if state and state.track_id == track_id:
                    resume_state = state
            
            # Extract subtitle
            extracted_path = self.mkv_handler.extract_subtitle(file_path, track_id)
            
            # Parse subtitle
            parser = SubtitleParser()
            lines = parser.load(extracted_path)
            total_lines = len(lines)
            lines_count = total_lines
            
            # Initialize translator
            translator = Translator(model_manager=api_manager)
            self.active_translator = translator  # Store reference
            success, msg = translator.initialize()
            
            if not success:
                raise RuntimeError(f"Failed to initialize: {msg}")
            
            # Setup Progress callback proxy
            def progress_proxy(current, total, status, token_usage: TokenUsage):
                self.token_usage = token_usage
                if self.should_cancel or self.is_paused:
                    return
                if self.on_progress:
                    self.on_progress(current, total, status, token_usage)
                    
            # Create state if not resuming
            if not resume_state:
                self.state_manager.create_state(
                    source_file=file_path,
                    track_id=track_id,
                    total_lines=total_lines,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    model_name=model_name
                )
            
            def state_callback(current, total, status, token_usage):
                progress_proxy(current, total, status, token_usage)
                if self.should_cancel:
                    raise KeyboardInterrupt("Cancelled")
            
            # Execute Translation
            translations, errors, final_tokens = translator.translate_all(
                lines=lines,
                source_lang=source_lang,
                target_lang=target_lang,
                batch_size=self.config.batch_size,
                progress_callback=state_callback,
                state_manager=self.state_manager,
                anime_title=anime_title
            )
            
            # Apply translations
            parser.apply_translations(translations)
            
            # Save translated subtitle to a temporary format for review
            input_path = Path(file_path)
            output_dir = self.config.default_output_dir or str(input_path.parent)
            
            sanitized_model = model_name.replace("/", "_").replace(":", "_").replace("\\", "_")
            ext = Path(extracted_path).suffix
            initial_path = Path(output_dir) / f"{input_path.stem}_{sanitized_model}_translated{ext}"
            
            translated_sub_path = parser.save(str(initial_path))
            
            # Construct Payload
            payload = {
                "current_file": file_path,
                "translated_sub_path": str(translated_sub_path),
                "output_dir": output_dir,
                "input_path": input_path,
                "sanitized_model": sanitized_model,
                "model_used": model_name,
                "extracted_path": extracted_path,
                "lines_count": lines_count,
                "start_time": start_time,
                "final_tokens": final_tokens,
                "api_manager": api_manager,
                "prompt_used": prompt_used
            }
            
            if self.on_complete:
                self.on_complete(payload)
                
        except Exception as e:
            if self.is_paused or self.should_cancel:
                return # Exited cleanly due to user action
            logger.error(f"Translation Error: {e}")
            if self.on_error:
                self.on_error(str(e))
        finally:
            self.active_translator = None
            self.is_processing = False
            
    def pause(self):
        """Pause the translation."""
        self.is_paused = True
        self.should_cancel = True
        if self.active_translator:
            self.active_translator.is_paused = True
            
    def resume(self):
        """Resume from paused state (requires calling start_translation again after this or handling it via threading loop logic)."""
        # The logic in app.py restarts the thread, so resume here just clears flags.
        self.is_paused = False
        self.should_cancel = False
        
    def cancel(self):
        """Cancel translation."""
        self.should_cancel = True
        self.is_processing = False
        if self.active_translator:
            self.active_translator.should_stop = True
            self.active_translator = None
            
    def get_status(self):
        """Return basic status dict."""
        return {
            "is_processing": self.is_processing,
            "is_paused": self.is_paused,
            "should_cancel": self.should_cancel
        }
