"""
Main Application Window for Sub-auto
Subtitle extraction, translation, and replacement tool.
Single-page wizard layout with progressive disclosure.

Composed from focused mixins (see the sibling modules in this package) so the
file stays small while ``SubAutoApp`` keeps its full public surface.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from tkinter import messagebox

import customtkinter as ctk

from ..constants import APP_TITLE, APP_VERSION, WINDOW_SIZE, MIN_SIZE, LANGUAGE_MAPPING
from ..styles import COLORS, configure_theme
from ..settings import SettingsDialog
from ..history_view import HistoryView
from ..toast import ToastManager

from core.config_manager import get_config
from core.mkv_handler import MKVHandler
from core.state_manager import get_state_manager
from core.history_manager import get_history_manager
from core.logger import get_logger
from core.finalization_service import FinalizationService
from core.prompt_manager import PromptManager

from ..state.app_state import AppState
from ..services.subtitle_track_service import SubtitleTrackService
from ..services.translation_session import TranslationSession
from ..controllers.api_controller import APIController
from ..controllers.translation_controller import TranslationController
from ..controllers.view_manager import ViewManager

from .ui_setup import UISetupMixin
from .state_ui import StateUIMixin
from .overlays import OverlayMixin
from .file_selection import FileSelectionMixin
from .translation_flow import TranslationFlowMixin
from .finalization import FinalizationMixin


class SubAutoApp(
    UISetupMixin,
    StateUIMixin,
    OverlayMixin,
    FileSelectionMixin,
    TranslationFlowMixin,
    FinalizationMixin,
    ctk.CTk
):
    """Main application window for Sub-auto."""

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
        self.prompt_manager = PromptManager()
        self.settings_view: Optional[SettingsDialog] = None
        self.history_view: Optional[HistoryView] = None
        self.mkv_handler: Optional[MKVHandler] = None
        
        self.app_state_manager = get_state_manager()
        self.history_manager = get_history_manager()
        self.logger = get_logger()
        
        self._pending_resume = False # Keep as internal UI state for now or move to app_state?
        # Moving most to app_state
        self.app_state.remove_old_subs = True
        
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
            self.app_state.external_subtitle_path = state.external_subtitle_path
            self.file_drop.set_file(state.source_file)
            self._load_subtitle_tracks()
            
            if state.external_subtitle_path and os.path.exists(state.external_subtitle_path):
                self.app_state.selected_track_id = -1
                self.step_frames[1].show_external_subtitle_option(
                    True, Path(state.external_subtitle_path).name
                )
                self._update_step_states()
            elif state.track_id is not None:
                self.after(500, lambda: self._select_track_by_id(state.track_id))
            
            self.source_lang_row.set_value(state.source_lang)
            self.target_lang_row.set_value(state.target_lang)
            self.app_state.selected_model = state.model_name
            
            # Show resume button
            if hasattr(self, 'start_btn'):
                self.start_btn.pack_forget()
            self.resume_btn.pack(side="left")
            self.status_label.configure(text="Ready to resume")
        else:
            self.app_state_manager.clear()
    
    def _reset_app(self):
        """Reset app to initial state."""
        self.app_state.current_file = None
        self.file_drop.reset()
        
        for item in self.track_items:
            item.destroy()
        self.track_items.clear()
        self.app_state.selected_track_id = None
        self.app_state.external_subtitle_path = None
        self.step_frames[1].show_external_subtitle_option(False)
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
        if hasattr(self, 'start_btn'):
            self.start_btn.pack(side="right")
    
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
