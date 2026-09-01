"""
Translation flow mixin for the main application window.
Manages the start/pause/resume/cancel lifecycle and processing mode switches.
Combined into SubAutoApp via mixins.
"""

from pathlib import Path

import customtkinter as ctk

from core.utils import extract_anime_title


class TranslationFlowMixin:
    """Start, pause, resume, cancel and processing-mode transitions."""

    def _load_saved_api_key(self):
        """Load saved configuration and auto-validate."""
        if self.config.provider == "openrouter" and self.config.openrouter_api_key:
            self.after(1000, self._validate_api)
        elif self.config.provider == "ollama":
            self.after(1000, self._validate_api)
        elif self.config.provider == "groq" and self.config.groq_api_key:
            self.after(1000, self._validate_api)
    
    def _validate_api(self):
        """Validate AI provider connection."""
        self.api_controller.validate_api()
    
    # Removed legacy _do_validate, _on_validate_result, _on_validate_error

    def _enter_processing_mode(self):
        """Switch to processing mode (Step 3)."""
        self.app_state.is_processing = True
        self.title_bar.title_label.configure(text=f"{self.APP_TITLE} - Processing")
        
        # Switch to Step 3
        # Use set_step to update UI selection
        self.progress_header.set_step(3)
        self._update_step_states() # Update completion status
        self.step_controller.show_step(3)
        
        # Show processing buttons in footer
        self.footer.set_processing_mode(True, is_paused=self.app_state.is_paused)
        
        # Set file info in processing view
        if self.app_state.current_file:
            filename = Path(self.app_state.current_file).name
            track_info = ""
            for track in self.app_state.subtitle_tracks:
                if track.track_id == self.app_state.selected_track_id:
                    track_info = f"Track {track.track_id} - {track.language.upper()}"
                    break
            if self.app_state.external_subtitle_path:
                track_info = f"External - {Path(self.app_state.external_subtitle_path).name}"
            
            self.processing_view.set_file_info(filename, track_info)
    
    def _exit_processing_mode(self):
        """Return to normal mode or advance to review."""
        self.app_state.is_processing = False
        self.title_bar.title_label.configure(text=self.APP_TITLE)
        
        # Hide footer buttons
        self.footer.set_processing_mode(False)
        
        # If cancelled, go back to configuration (Step 2)
        if self.app_state.should_cancel:
             self._on_step_change(2)
        # If completed (logic handled in _on_translation_complete), we might stay or go to step 4
        # For general exit, let's assume we just update the view
        elif self.app_state.active_translator is None:
             # Just refresh current step
             self.step_controller.show_step(self.progress_header.current_step)
    
    def _start_translation(self):
        """Start the translation process by asking for title confirmation first."""
        if not self.app_state.api_validated:
            self.toast.warning("Please connect API first")
            return
        
        if not self.app_state.current_file or self.app_state.selected_track_id is None:
            self.toast.warning("Please select a video and subtitle")
            return
            
        # Extract title automatically
        extracted_title = extract_anime_title(self.app_state.current_file)
        
        # Show review dialog
        dialog = ctk.CTkInputDialog(
            text="Review Anime Title (Used for translation context):", 
            title="Anime Title Review"
        )
        
        # Inject the default value directly (CTkInputDialog doesn't perfectly support this, 
        # but we can edit the entry inside after initialization)
        dialog.after(100, lambda: [dialog._entry.delete(0, 'end'), dialog._entry.insert(0, extracted_title)])
        
        # We need to use `after` to make sure it runs without blocking to death, but CTkInputDialog is modal natively.
        # So we just wait for input
        reviewed_title = dialog.get_input()
        
        if reviewed_title is None:
            # User cancelled the dialog
            self.toast.info("Translation cancelled")
            return
            
        self.app_state.current_anime_title = reviewed_title.strip()
        
        self.app_state.is_processing = True
        self.app_state.pending_estimates.clear() # Cancel background work
        self._enter_processing_mode()
        
        # Initialize orchestrator via session
        self.translation_session.init_orchestrator(
             on_progress=self.translation_controller.on_progress,
             on_complete=self.translation_controller.on_orchestrator_complete,
             on_error=self.translation_controller.on_error
        )
        
        source_lang = self.source_lang_row.get_value()
        target_lang = self.target_lang_row.get_value()
        model_used = self.app_state.selected_model or "gemini-1.5-flash"
        
        self.translation_session.start(
             self.app_state.current_file,
             self.app_state.selected_track_id,
             source_lang,
             target_lang,
             model_used,
             self.app_state.current_anime_title,
             self.app_state.external_subtitle_path
        )
    
    # Removed _on_translation_progress, _on_orchestrator_complete from here
    # Managed by translation_controller
    
    def _pause_translation(self):
        """Pause translation."""
        if self.app_state.is_paused:
            # Resume
            self._do_resume()
        else:
            # Pause
            if self.translation_session.pause():
                self.processing_view.set_paused(True)
                self.footer.set_processing_mode(True, is_paused=True)
                self.status_label.configure(text="Paused - progress saved")
    
    def _resume_translation(self):
        """Resume from saved state."""
        if not self.app_state.api_validated:
            self._pending_resume = True
            self.resume_btn.configure(state="disabled", text="Connecting...")
            self._validate_api()
            return

        self._do_resume()
    
    def _do_resume(self):
        """Actually resume translation."""
        self._pending_resume = False
        self.app_state.is_paused = False
        self.app_state.should_cancel = False
        self.app_state.is_processing = True
        
        self.processing_view.set_paused(False)
        self.footer.set_processing_mode(True, is_paused=False)
        self.resume_btn.pack_forget()
        
        self._enter_processing_mode()
        
        # Initialize orchestrator via session
        self.translation_session.init_orchestrator(
             on_progress=self.translation_controller.on_progress,
             on_complete=self.translation_controller.on_orchestrator_complete,
             on_error=self.translation_controller.on_error
        )
        
        self.translation_session.resume()
             
        source_lang = self.source_lang_row.get_value()
        target_lang = self.target_lang_row.get_value()
        model_used = self.app_state.selected_model or "gemini-1.5-flash"
        anime_title = getattr(self.app_state, 'current_anime_title', None)
        
        # Call start again to resume background thread
        self.translation_session.start(
            self.app_state.current_file,
            self.app_state.selected_track_id,
            source_lang,
            target_lang,
            model_used,
            anime_title,
            self.app_state.external_subtitle_path
        )
    
    def _cancel_translation(self):
        """Cancel translation."""
        self.translation_session.cancel()
        self._exit_processing_mode()
        self.toast.info("Translation cancelled")
