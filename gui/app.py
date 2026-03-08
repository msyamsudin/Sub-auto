"""
Main Application Window for Sub-auto
Subtitle extraction, translation, and replacement tool.
Single-page wizard layout with progressive disclosure.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, List
import threading
import os
import time
import sys
import ctypes

from .constants import APP_TITLE, APP_VERSION, WINDOW_SIZE, MIN_SIZE, LANGUAGE_MAPPING
from .window_utils import setup_window_style

from .styles import (
    COLORS, FONTS, SPACING, RADIUS,
    configure_theme, get_button_style, get_frame_style, get_label_style, get_input_style
)
from .components import (
    FileDropZone, TrackListItem, ProgressPanel, SettingsRow, StatusBadge, APIKeyPanel, SummaryWindow,
    LogPanel, CollapsibleFrame, CustomTitleBar, SubtitleEditor, VerticalStepper, HorizontalStepper
)
from .settings_dialog import SettingsDialog
from .toast import ToastManager
from .processing_view import ProcessingView
from .history_view import HistoryView
from .views.file_selection_view import FileSelectionView
from .views.configuration_view import ConfigurationView
from .views.footer_view import FooterView
from .views.review_view import ReviewView

from core.config_manager import get_config, ConfigManager
from core.mkv_handler import MKVHandler, SubtitleTrack
from core.subtitle_parser import SubtitleParser
from core.translator import Translator, get_api_manager, TokenUsage
from core.state_manager import get_state_manager, StateManager
from core.history_manager import get_history_manager, HistoryEntry
from core.logger import get_logger, Logger
from core.utils import extract_anime_title
from core.finalization_service import FinalizationService

from core.version import __version__
from .state.app_state import AppState
from .services.subtitle_track_service import SubtitleTrackService
from .services.translation_session import TranslationSession
from .controllers.api_controller import APIController
from .controllers.translation_controller import TranslationController
from .controllers.step_controller import StepController
from .controllers.view_manager import ViewManager

class SubAutoApp(ctk.CTk):
    """Main application window for Sub-auto."""
    
    APP_TITLE = APP_TITLE
    APP_VERSION = APP_VERSION
    WINDOW_SIZE = WINDOW_SIZE
    MIN_SIZE = MIN_SIZE
    
    def __init__(self):
        super().__init__()
        
        # Configure theme
        configure_theme()
        
        # Window setup - remove default title bar
        self.overrideredirect(True)
        
        # Center window
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - self.WINDOW_SIZE[0]) // 2
        y = (screen_height - self.WINDOW_SIZE[1]) // 2
        self.geometry(f"{self.WINDOW_SIZE[0]}x{self.WINDOW_SIZE[1]}+{x}+{y}")
        
        self.minsize(*self.MIN_SIZE)
        
        # Set window background
        self.configure(fg_color=COLORS["bg_dark"])
        
        # Enable window shadow and taskbar icon on Windows
        self.after(10, self._setup_window_style)
        
        # State
        self.app_state = AppState()
        self.config = get_config()
        self.settings_view: Optional[SettingsDialog] = None
        self.history_view: Optional[HistoryView] = None
        self.mkv_handler: Optional[MKVHandler] = None
        
        self.app_state_manager = get_state_manager()
        self.history_manager = get_history_manager()
        self.logger = get_logger()
        
        self._pending_resume = False # Keep as internal UI state for now or move to app_state?
        # Moving most to app_state
        self.app_state.remove_old_subs = True
        
        # Initialize MKV handler and services
        
        # Language mapping from ISO 639-2 (MKVToolnix) to human names
        self.LANGUAGE_MAPPING = LANGUAGE_MAPPING
        
        # Initialize MKV handler and services
        self._init_mkv_handler()
        self.finalization_service = FinalizationService(self.mkv_handler)
        self.subtitle_service = SubtitleTrackService(self.mkv_handler, self.app_state)
        self.subtitle_service.set_language_mapping(self.LANGUAGE_MAPPING)
        
        self.translation_session = TranslationSession(self.mkv_handler, self.app_state)
        self.api_controller = APIController(self.app_state, self.config, None, None) 
        self.translation_controller = TranslationController(self.app_state, None, None, self.after)
        
        self.view_manager = ViewManager(self, self.app_state)
        self.view_manager.set_callbacks(
            on_open=self._on_overlay_opened,
            on_close=self._on_overlay_closed
        )
        
        # Build UI
        self._setup_ui()
        
        # Initialize toast manager
        self.toast = ToastManager(self)
        self.api_controller.toast = self.toast
        self.translation_controller.toast = self.toast
        self.translation_controller.set_callbacks(
            on_complete=self._exit_processing_mode,
            on_show_review=self._show_review_editor,
            on_show_summary=self._on_translation_summary_ready
        )
        
        # Load saved API key
        self._load_saved_api_key()
        
        # Check for resumable state (delayed to avoid blocking)
        self.after(500, self._check_resumable_state)

        # Handle close event
        # Note: WM_DELETE_WINDOW doesn't work with overrideredirect
        # Close is handled by CustomTitleBar
    
    def _init_mkv_handler(self):
        """Initialize MKV handler."""
        try:
            self.mkv_handler = MKVHandler()
        except Exception as e:
            self.logger.warning(f"Failed to initialize MKV handler: {e}")
    
    def _setup_window_style(self):
        """Setup Windows-specific window styling."""
        setup_window_style(self)

    def _setup_ui(self):
        """Setup the main UI - Top Nav + Content layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Custom Title Bar
        self.title_bar = CustomTitleBar(self, title=self.APP_TITLE, version=self.APP_VERSION, on_settings=self._open_settings, on_history=self._open_history, show_settings=True, show_history=True)
        self.title_bar.grid(row=0, column=0, sticky="ew")
        
        # Stepper
        self.stepper = HorizontalStepper(self.title_bar.get_center_frame(), steps=["Select File", "Configuration", "Translation", "Review"], current_step=1, on_step_change=self._on_step_change)
        self.stepper.pack(side="left", expand=True, fill="y", padx=SPACING["md"])
        
        # Main container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=1, column=0, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.content_area = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_area.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["md"])
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)

        # Processing View
        self.processing_view = ProcessingView(self.content_area, logger_instance=self.logger, on_pause=self._pause_translation, on_cancel=self._cancel_translation)
        self.translation_controller.processing_view = self.processing_view
        
        # Initialize Step Fragments
        view1 = self._create_step1_fragment()
        view2 = self._create_step2_fragment()
        view4 = self._create_step4_fragment()
        
        # Note: Step 3 is the processing_view itself
        self.step_frames = [view1, view2, self.processing_view, view4]
        
        # Step Controller
        self.step_controller = StepController(self.app_state, self.stepper, self.step_frames)
        self.step_controller.set_callback(self._on_handle_step_change_ui)

        # Footer
        self._create_footer()
        
        # Link API Controller
        self.api_controller.set_ui_elements(self.model_dropdown, self.model_status, self.validate_btn, self.title_bar, self.after)
        
        # Show first step
        self.step_controller.show_step(1)
        
    def _on_handle_step_change_ui(self, step_index: int):
        self._update_step_states()
        self._update_action_buttons()

    def _create_step1_fragment(self):
        view = FileSelectionView(self.content_area, on_file_selected=self._on_file_selected)
        self.file_drop = view.file_drop
        return view

    def _create_step2_fragment(self):
        view = ConfigurationView(self.content_area, on_model_change=self._on_model_change, on_validate_api=self._validate_api)
        self.tracks_frame = view.tracks_frame
        self.no_tracks_label = view.no_tracks_label
        self.source_lang_row = view.source_lang_row
        self.target_lang_row = view.target_lang_row
        self.model_dropdown = view.model_dropdown
        self.model_status = view.model_status
        self.cost_estimate_label = view.cost_estimate_label
        self.validate_btn = view.validate_btn
        self.track_items = view.track_items
        return view

    def _create_step4_fragment(self):
        return ReviewView(self.content_area, on_approve=self._on_review_approved, on_discard=self._on_review_discarded)

    def _on_step_change(self, step_index: int):
        self.step_controller.handle_step_change(step_index)
    
    def _create_footer(self):
        """Create footer with action buttons (FULL WIDTH)."""
        self.footer = FooterView(
            self,
            on_start=self._start_translation,
            on_reset=self._reset_app,
            on_resume=self._resume_translation,
            on_show_summary=self._show_last_summary
        )
        self.footer.grid(row=2, column=0, sticky="ew", padx=SPACING["md"], pady=(0, SPACING["md"]))
        
        # Link references for backward compatibility
        self.start_btn = self.footer.start_btn
        self.resume_btn = self.footer.resume_btn
        self.status_label = self.footer.status_label
        self.reset_btn = self.footer.reset_btn
        self.show_summary_btn = self.footer.summary_btn
        
        # Initial state
        self.start_btn.configure(state="disabled")
    
    def _update_step_states(self):
        """Update UI states based on current progress."""
        self.api_controller.sync_api_state()
        manager = get_api_manager()
        if hasattr(self, 'step_controller'):
            self.step_controller.update_stepper_logic(manager)
        self._update_action_buttons()
        self._update_token_estimate()
    
    # Removed legacy _sync_api_state and _update_stepper_logic

    def _update_action_buttons(self):
        """Enable/disable action buttons in footer."""
        has_file = self.app_state.current_file is not None
        has_track = self.app_state.selected_track_id is not None
        api_ready = self.app_state.api_validated
        
        can_start = has_file and has_track and api_ready and not self.app_state.is_processing
        if hasattr(self, 'start_btn'):
            self.start_btn.configure(state="normal" if can_start else "disabled")
        
        # Update cost estimate
        self._update_token_estimate()
    
    def _update_token_estimate(self):
        """Calculate and display estimated tokens for OpenRouter translations."""
        # Only show for OpenRouter/Groq with file, track, and API ready
        if (self.config.provider not in ["openrouter", "groq"] or 
            not self.app_state.current_file or 
            self.app_state.selected_track_id is None or
            not self.app_state.api_validated or
            self.app_state.is_processing): # Don't estimate while already processing
            if hasattr(self, 'cost_estimate_label'):
                self.cost_estimate_label.configure(text="")
            return
        
        try:
            from core.translator import get_api_manager
            api_manager = get_api_manager()
            model_info = api_manager.get_selected_model_info()
            
            if not model_info:
                if hasattr(self, 'cost_estimate_label'):
                    self.cost_estimate_label.configure(text="")
                return
            
            # Use the estimation service
            from core.estimation_service import EstimationService
            
            if not hasattr(self, 'estimation_service'):
                self.estimation_service = EstimationService(self.mkv_handler)
                
            def on_result(total_chars, line_count):
                self.after(0, lambda: self._display_token_estimate(model_info, total_chars, line_count))
                
            def on_error(e):
                self.after(0, lambda: self.cost_estimate_label.configure(text=""))
                
            started = self.estimation_service.estimate_tokens_async(
                self.app_state.current_file,
                self.app_state.selected_track_id,
                on_result,
                on_error
            )
            
            if started and hasattr(self, 'cost_estimate_label'):
                 self.cost_estimate_label.configure(text="💰 Calculating...")
            
        except Exception as e:
            self.logger.warning(f"Failed to estimate list: {e}")
            if hasattr(self, 'cost_estimate_label'):
                self.cost_estimate_label.configure(text="")
    
    def _display_token_estimate(self, model_info, total_chars: int, line_count: int):
        """Display the token estimate based on cached subtitle data."""
        if not hasattr(self, 'estimation_service'):
            from core.estimation_service import EstimationService
            self.estimation_service = EstimationService(self.mkv_handler)
            
        total_estimated_tokens = self.estimation_service.calculate_tokens(total_chars, line_count)
        
        # Format token count
        if total_estimated_tokens >= 1000:
            token_text = f"{total_estimated_tokens / 1000:.1f}K"
        else:
            token_text = f"{total_estimated_tokens}"
        
        # Display only tokens, NO cost
        display_text = f"💰 ~{token_text} tokens"
        
        if hasattr(self, 'cost_estimate_label'):
            self.cost_estimate_label.configure(text=display_text)
    def _open_settings(self):
        """Open settings view."""
        self.view_manager.open_settings(self.config, self._on_settings_save, SettingsDialog)
        
    def _on_overlay_opened(self, view_type: str):
        """Callback when an overlay is opened."""
        if hasattr(self, 'footer'):
            self.footer.grid_remove()
        
        if view_type == "settings" and self.view_manager.settings_view:
            self.view_manager.settings_view.remove_subs_var.set(self.app_state.remove_old_subs)

    def _on_overlay_closed(self, view_type: str):
        """Callback when an overlay is closed."""
        if hasattr(self, 'footer'):
            self.footer.grid()

    def _open_history(self):
        """Open history view."""
        self.view_manager.open_history(HistoryView)
    
    def _on_settings_save(self, settings: dict):
        """Handle settings save."""
        self.remove_old_subs = settings.get("remove_old_subs", True)
        self._init_mkv_handler()  # Reinitialize with new path
        
        # Sync API validation state
        manager = get_api_manager()
        self.app_state.api_validated = manager.is_configured
        self.app_state.selected_model = manager.selected_model
        
        # If AI settings changed, handle validation sync
        if settings.get("ai_settings_changed", False):
            if not manager.is_configured:
                # Check if we should auto-connect
                if self.config.provider == "ollama" or \
                   (self.config.provider == "openrouter" and self.config.openrouter_api_key) or \
                   (self.config.provider == "groq" and self.config.groq_api_key):
                    # Show connecting status first
                    self.app_state.is_validating = True
                    self.title_bar.set_api_status(False, connecting=True)
                    self._validate_api()
                else:
                    self.toast.info("AI settings updated. Please reconnect.")
            else:
                self.toast.success("Settings updated")
        else:
            self.toast.success("Settings saved")
            
        # Always refresh UI states to ensure title bar and step info are in sync
        self._update_step_states()
    
    def _on_file_selected(self, file_path: str):
        """Handle file selection."""
        self.app_state.current_file = file_path
        self._load_subtitle_tracks()
        self._update_step_states()
        
        # Auto-advance to Step 2
        self._on_step_change(2)

    
    def _load_subtitle_tracks(self):
        """Load subtitle tracks from the selected MKV file."""
        if not self.app_state.current_file or not self.mkv_handler:
            return
            
        try:
            filtered_tracks = self.subtitle_service.load_tracks(self.app_state.current_file)
            
            # Update View
            view = self.step_frames[1]
            view.update_tracks(
                tracks=filtered_tracks,
                selected_id=None,
                on_track_select=self._on_track_select
            )
            
            if not filtered_tracks:
                 view.no_tracks_label.configure(text="No supported subtitle tracks found", text_color=COLORS["warning"])
                 view.no_tracks_label.grid()
                 return
            
            # Auto-select first track
            if self.track_items:
                self.track_items[0].select()
                
        except Exception as e:
            view = self.step_frames[1]
            view.set_model_status(f"Error: {str(e)}", COLORS["error"])
            view.no_tracks_label.configure(
                text=f"Error: {str(e)}",
                text_color=COLORS["error"]
            )
            view.no_tracks_label.grid()
            self.toast.error(f"Failed to load tracks: {str(e)}")
    
    def _on_track_select(self, track_id: int, is_selected: bool):
        """Handle track selection."""
        new_track_id = self.subtitle_service.handle_track_selection(track_id, is_selected, self.track_items)
        if new_track_id is None and not is_selected:
             pass # Track was deselected
            
        # Update source language based on track info
        if self.app_state.selected_track_id is not None:
            lang_name = self.subtitle_service.get_track_language_name(self.app_state.selected_track_id)
            if lang_name:
                # Ensure the option exists in the dropdown
                current_options = self.source_lang_row.input.cget("values")
                if lang_name not in current_options:
                    new_options = list(current_options)
                    # Insert before "Auto-detect" if it exists, otherwise append
                    if "Auto-detect" in new_options:
                        new_options.insert(new_options.index("Auto-detect"), lang_name)
                    else:
                        new_options.append(lang_name)
                    self.source_lang_row.input.configure(values=new_options)
                
                self.source_lang_row.set_value(lang_name)
                self.logger.info(f"🌐 Auto-selected source language: {lang_name} (from track {self.app_state.selected_track_id})")

        self._update_step_states()
    
    def _on_model_change(self, model: str):
        """Handle model selection change."""
        self.app_state.selected_model = model
        self._update_step_states()
    
    def _validate_api(self):
        """Validate AI provider connection."""
        self.api_controller.validate_api()
    
    # Removed legacy _do_validate, _on_validate_result, _on_validate_error
    
    def _load_saved_api_key(self):
        """Load saved configuration and auto-validate."""
        if self.config.provider == "openrouter" and self.config.openrouter_api_key:
            self.after(1000, self._validate_api)
        elif self.config.provider == "ollama":
            self.after(1000, self._validate_api)
        elif self.config.provider == "groq" and self.config.groq_api_key:
            self.after(1000, self._validate_api)
    
    def _enter_processing_mode(self):
        """Switch to processing mode (Step 3)."""
        self.app_state.is_processing = True
        self.title_bar.title_label.configure(text=f"{self.APP_TITLE} - Processing")
        
        # Switch to Step 3
        # Use set_step to update UI selection
        self.stepper.set_step(3)
        self._update_step_states() # Update completion status
        self.step_controller.show_step(3)
        
        # Set file info in processing view
        if self.app_state.current_file:
            filename = Path(self.app_state.current_file).name
            track_info = ""
            for track in self.app_state.subtitle_tracks:
                if track.track_id == self.app_state.selected_track_id:
                    track_info = f"Track {track.track_id} - {track.language.upper()}"
                    break
            
            self.processing_view.set_file_info(filename, track_info)
    
    def _exit_processing_mode(self):
        """Return to normal mode or advance to review."""
        self.app_state.is_processing = False
        self.title_bar.title_label.configure(text=self.APP_TITLE)
        
        # If cancelled, go back to configuration (Step 2)
        if self.app_state.should_cancel:
             self._on_step_change(2)
        # If completed (logic handled in _on_translation_complete), we might stay or go to step 4
        # For general exit, let's assume we just update the view
        elif self.app_state.active_translator is None:
             # Just refresh current step
             self.step_controller.show_step(self.stepper.current_step)
    
    def _start_translation(self):
        """Start the translation process by asking for title confirmation first."""
        if not self.app_state.api_validated:
            self.toast.warning("Please connect API first")
            return
        
        if not self.app_state.current_file or self.app_state.selected_track_id is None:
            self.toast.warning("Please select a file and track")
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
             self.app_state.current_anime_title
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
            anime_title
        )
    
    def _cancel_translation(self):
        """Cancel translation."""
        self.translation_session.cancel()
        self._exit_processing_mode()
        self.toast.info("Translation cancelled")
    
    def _on_translation_complete(self, summary: dict):
        """Handle validation after merge complete."""
        self.translation_controller.finalize_translation(summary, self.config.provider)
    
    def _on_translation_summary_ready(self, summary_data: dict):
        """Callback from translation controller when summary is ready for UI."""
        self.stepper.set_step(5)
        self.summary_view = SummaryWindow(
            self,
            **summary_data,
            on_open_folder=lambda: os.startfile(Path(summary_data["output_path"]).parent) if summary_data.get("output_path") else None,
            on_close=self._close_summary
        )
        self.summary_view.grid(row=1, column=0, rowspan=2, sticky="nsew")
        self.summary_view.lift()
        
        if self.app_state_manager:
            self.app_state_manager.clear()
            
        self.after(2000, self._exit_processing_mode)
    
    def _close_summary(self):
        """Close summary view and reset app for next file."""
        if hasattr(self, 'summary_view') and self.summary_view:
            self.summary_view.destroy()
            self.summary_view = None
            
        self._reset_app()

    def _on_translation_error(self, error: str):
        # This is now handled by controller, but kept as placeholder if needed
        pass
    
    def _show_review_editor(self, payload: dict):
        """Show the subtitle review editor."""
        self.app_state.is_processing = False
        self._exit_processing_mode()
        self.app_state.merge_payload = payload
        
        # Update view
        view = self.step_frames[3]
        view.show_payload(payload)
        
        # Update Stepper
        self.step_controller.show_step(4)
        self.toast.info("Translation complete! Please review the subtitles.")
    
    def _on_review_approved(self, content: str):
        """Handle review approval - save edited content and merge."""
        try:
            # Save edited content back to file
            with open(self.app_state.merge_payload["translated_sub_path"], 'wt', encoding='utf-8') as f:
                f.write(content)
            
            # Finalize merge via service
            self.toast.info("Finalizing merge into video...")
            summary = self.finalization_service.finalize_merge(
                self.app_state.merge_payload, 
                remove_old_subs=self.app_state.remove_old_subs
            )
            self._on_translation_complete(summary)
            
        except Exception as e:
            self.toast.error(f"Merge failed: {str(e)}")
            self.logger.error(f"Finalize merge error: {e}")
            
    def _on_review_discarded(self):
        """Handle review discard - clean up and reset."""
        self.finalization_service.cleanup_temp_files(self.app_state.merge_payload) 
        if self.app_state_manager:
            self.app_state_manager.clear()
        self.app_state.merge_payload = None
        self._on_step_change(2) # Back to config
        self.toast.info("Translation discarded")
    
    
    def _check_resumable_state(self):
        """Check for resumable state."""
        state = self.app_state_manager.load()
        if not state:
            return
        
        if not os.path.exists(state.source_file):
            self.app_state_manager.clear()
            return
        
        # Ask user
        if messagebox.askyesno(
            "Resume Translation?",
            f"Found incomplete translation:\n{Path(state.source_file).name}\n\n"
            f"Progress: {state.progress_percent:.1f}%\n"
            "Resume?"
        ):
            self.app_state.current_file = state.source_file
            self.file_drop.set_file(state.source_file)
            self._load_subtitle_tracks()
            
            if state.track_id:
                self.after(500, lambda: self._select_track_by_id(state.track_id))
            
            self.source_lang_row.set_value(state.source_lang)
            self.target_lang_row.set_value(state.target_lang)
            self.app_state.selected_model = state.model_name
            
            # Show resume button
            self.start_btn.pack_forget()
            self.resume_btn.pack(side="left")
            self.status_label.configure(text="Ready to resume")
        else:
            self.app_state_manager.clear()
    
    def _select_track_by_id(self, track_id: int):
        """Select track by ID."""
        for item in self.track_items:
            if item.track_id == track_id:
                item.select()
                self.app_state.selected_track_id = track_id
                self._update_step_states()
                break
    
    def _reset_app(self):
        """Reset app to initial state."""
        self.app_state.current_file = None
        self.file_drop.reset()
        
        for item in self.track_items:
            item.destroy()
        self.track_items.clear()
        self.app_state.selected_track_id = None
        self.no_tracks_label.grid()
        
        self.app_state.is_processing = False
        self.app_state.is_paused = False
        self.app_state.should_cancel = False
        # Clear payload to ensure Step 3/4 reset
        if hasattr(self.app_state, 'merge_payload'):
            self.app_state.merge_payload = None
        
        self._on_step_change(1) # Go back to step 1
        self._update_step_states()
        self.status_label.configure(text="")
        
        self.resume_btn.pack_forget()
        self.start_btn.pack(side="left")
    
    def _show_last_summary(self):
        """Re-open the last summary window."""
        if self.app_state.last_summary_data:
            from pathlib import Path
            output_path = Path(self.app_state.last_summary_data["output_path"])
            
            if hasattr(self, 'summary_view') and self.summary_view:
                self.summary_view.destroy()
            
            self.summary_view = SummaryWindow(
                self,
                **self.app_state.last_summary_data,
                on_open_folder=lambda: os.startfile(output_path.parent),
                on_close=self._close_summary
            )
            self.summary_view.grid(row=1, column=0, rowspan=2, sticky="nsew")
            self.summary_view.lift()

    def _on_close(self):
        """Handle window close."""
        if self.app_state.is_processing and not self.app_state.is_paused:
            if not messagebox.askokcancel("Quit", "Translation in progress. Quit?"):
                return
        
        self.app_state.should_cancel = True
        self.quit()
        self.destroy()
        sys.exit(0)

def run_app():
    """Run the Sub-auto application."""
    app = SubAutoApp()
    app.mainloop()
