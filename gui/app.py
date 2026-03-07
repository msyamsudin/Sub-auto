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

class SubAutoApp(ctk.CTk):
    """Main application window for Sub-auto."""
    
    APP_TITLE = "sub-auto"
    APP_VERSION = f"v{__version__}"
    WINDOW_SIZE = (1200, 800)  # Increased from (780, 520) to match editor size
    MIN_SIZE = (1200, 800)      # Increased from (700, 480)
    
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
        self.config = get_config()
        self.settings_view: Optional[SettingsDialog] = None
        self.history_view: Optional[HistoryView] = None
        self.mkv_handler: Optional[MKVHandler] = None
        self.current_file: Optional[str] = None
        self.subtitle_tracks: List[SubtitleTrack] = []
        self.selected_track_id: Optional[int] = None
        self.is_processing = False
        self.is_paused = False
        self.should_cancel = False
        self.api_validated = False
        self.selected_model: Optional[str] = None
        self.last_summary_data = None
        self.state_manager = get_state_manager()
        self.history_manager = get_history_manager()
        self.logger = get_logger()
        self.remove_old_subs = True
        self._pending_resume = False
        self.active_translator: Optional[Translator] = None
        self.is_validating = False
        self._pending_estimates = set()
        self._subtitle_cache = {}
        
        # Language mapping from ISO 639-2 (MKVToolnix) to human names
        self.LANGUAGE_MAPPING = {
            "eng": "English",
            "ara": "Arabic",
            "jpn": "Japanese",
            "kor": "Korean",
            "chi": "Chinese",
            "zho": "Chinese",
            "ind": "Indonesian",
            "may": "Indonesian",
            "msa": "Indonesian",
            "und": "English",
        }
        
        # Initialize MKV handler and services
        self._init_mkv_handler()
        self.finalization_service = FinalizationService(self.mkv_handler)
        
        # Build UI
        self._setup_ui()
        
        # Initialize toast manager
        self.toast = ToastManager(self)
        
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
        try:
            # Get window handle
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            
            # Enable shadow effect
            DWMWA_NCRENDERING_POLICY = 2
            DWMNCRP_ENABLED = 2
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_NCRENDERING_POLICY,
                ctypes.byref(ctypes.c_int(DWMNCRP_ENABLED)),
                ctypes.sizeof(ctypes.c_int)
            )

            # Enable rounded corners (Windows 11)
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
                ctypes.sizeof(ctypes.c_int)
            )
            
            # Show in taskbar - set window as tool window then back to normal
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style & ~WS_EX_TOOLWINDOW | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            
            # Force window to refresh
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
            ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
        except Exception as e:
            self.logger.warning(f"Failed to setup window style: {e}")
    
    def _setup_ui(self):
        """Setup the main UI - Top Nav + Content layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Content area expands
        
        # Custom Title Bar (replaces Windows default)
        self.title_bar = CustomTitleBar(
            self,
            title=self.APP_TITLE,
            version=self.APP_VERSION,
            on_settings=self._open_settings,
            on_history=self._open_history,
            show_settings=True,
            show_history=True,
            is_dialog=False
        )
        self.title_bar.grid(row=0, column=0, sticky="ew")
        
        # Inject Horizontal Stepper into Title Bar
        self.stepper = HorizontalStepper(
            self.title_bar.get_center_frame(),
            steps=["Select File", "Configuration", "Translation", "Review"],
            current_step=1,
            on_step_change=self._on_step_change
        )
        self.stepper.pack(side="left", expand=True, fill="y", padx=SPACING["md"])
        
        # Main container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=1, column=0, sticky="nsew")
        
        self.main_container.grid_columnconfigure(0, weight=1) # Content Area spans full width
        self.main_container.grid_rowconfigure(0, weight=1)
        
        # === Content Area ===
        self.content_area = ctk.CTkFrame(self.main_container, fg_color="transparent")
        # Removed sidebar column, so content is column 0
        self.content_area.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["md"])
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)
        
        # Processing view (hidden initially, overlay)
        self.processing_view = ProcessingView(
            self.content_area,
            logger_instance=self.logger,
            on_pause=self._pause_translation,
            on_cancel=self._cancel_translation
        )
        
        # Initialize Step Frames
        self.step_frames = {}
        self._create_step_frames()
        
        # Show initial step
        self._show_step(1)
        
        # Create persistent footer
        self._create_footer()
        
    def _create_step_frames(self):
        """Initialize frames for each step."""
        # Step 1: File Selection
        self.step_frames[1] = self._create_step1_frame()
        
        # Step 2: Configuration
        self.step_frames[2] = self._create_step2_frame()
        
        # Step 4: Review
        self.step_frames[4] = self._create_step4_frame()
        
        pass 

    def _show_step(self, step_idx: int):
        """Switch to specific step view."""
        # Hide current contents
        for widget in self.content_area.winfo_children():
            widget.pack_forget()
            widget.grid_forget()
            
        # Update Stepper UI
        self.stepper.set_step(step_idx)
        
        # Show new content
        if step_idx == 3:
             # Processing Step
             if self.is_processing:
                 self.processing_view.pack(fill="both", expand=True)
             else:
                 # Show 'Ready to Start' or similar if not processing
                 # For now, let's just show Step 2 content but with focus on Start button?
                 # Or maybe Step 3 IS the execution phase.
                 pass
        elif step_idx in self.step_frames:
            self.step_frames[step_idx].pack(fill="both", expand=True)
            
    def _on_step_change(self, step_idx: int):
        """Handle stepper click."""
        # Validation logic before switching
        if step_idx > 1 and not self.current_file:
            self.toast.warning("Please select a file first")
            return
            
        if step_idx > 2 and self.selected_track_id is None:
             self.toast.warning("Please select a subtitle track first")
             return
             
        self._show_step(step_idx)
    
    def _create_step1_frame(self):
        """Create Frame for Step 1: File Selection."""
        view = FileSelectionView(
            self.content_area,
            on_file_selected=self._on_file_selected
        )
        self.file_drop = view.file_drop
        return view

    def _create_step2_frame(self):
        """Create Frame for Step 2: Configuration (Tracks + Options)."""
        view = ConfigurationView(
            self.content_area,
            on_model_change=self._on_model_change,
            on_validate_api=self._validate_api
        )
        
        # Link references for backward compatibility with app.py methods
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

    def _create_step4_frame(self):
        """Create Frame for Step 4: Review."""
        view = ReviewView(
            self.content_area,
            on_approve=self._on_review_approved,
            on_discard=self._on_review_discarded
        )
        return view
    
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
        manager = get_api_manager()
        self._sync_api_state(manager)
        self._update_stepper_logic(manager)
        self._update_action_buttons()
        self._update_token_estimate()
    
    def _sync_api_state(self, manager):
        """Sync API connection state and model selection."""
        # Sync with global ModelManager state (e.g. if validated in settings)
        if manager.is_configured:
            self.api_validated = True
            self.selected_model = manager.selected_model

        if self.api_validated:
            display_names = manager.get_model_display_names()
            if display_names:
                self.model_dropdown.configure(values=display_names, state="normal")
                info = manager.get_selected_model_info()
                if info:
                    self.model_dropdown.set(info.short_name)
            
            self.model_status.configure(text="✓ Connected", text_color=COLORS["success"])
            if hasattr(self, "validate_btn"):
                self.validate_btn.grid_forget()
        else:
            self.model_dropdown.configure(state="disabled")
            if not self.is_validating:
                self.model_status.configure(text="⚠ Not connected", text_color=COLORS["text_muted"])
                self.model_dropdown.set("Not connected")

        # Update title bar API status
        if not self.is_validating:
            display_model = self.selected_model
            info = manager.get_selected_model_info()
            if info:
                display_model = info.short_name
            self.title_bar.set_api_status(self.api_validated, display_model or "")

    def _update_stepper_logic(self, manager):
        """Update stepper descriptions and completion marks."""
        has_file = self.current_file is not None
        has_track = self.selected_track_id is not None
        api_ready = self.api_validated
        completed_indices = []

        # Step 1: File Selection
        if has_file:
            completed_indices.append(1)
            path = Path(self.current_file)
            size = path.stat().st_size / (1024 * 1024 * 1024)  # GB
            self.stepper.update_step_description(1, f"{path.name} ({size:.2f} GB)")
        else:
            self.stepper.clear_step_description(1)

        # Step 2: Configuration
        if has_file and has_track:
            track_info = "Track Selected"
            for track in self.subtitle_tracks:
                if track.track_id == self.selected_track_id:
                    track_info = f"Track {track.track_id} - {track.language.upper()}"
                    break
            
            status_text = track_info
            if api_ready:
                status_text += f"\nModel: {self.selected_model or 'Default'}"
                completed_indices.append(2)
            self.stepper.update_step_description(2, status_text)
        else:
            self.stepper.clear_step_description(2)

        # Step 3: Translation (Processing)
        in_review = hasattr(self, 'merge_payload') and self.merge_payload is not None
        if self.is_processing or in_review:
             completed_indices.append(3)
        
        # Sync with stepper
        self.stepper.set_completed_steps(completed_indices)

    def _update_action_buttons(self):
        """Enable/disable action buttons in footer."""
        has_file = self.current_file is not None
        has_track = self.selected_track_id is not None
        api_ready = self.api_validated
        
        can_start = has_file and has_track and api_ready and not self.is_processing
        if hasattr(self, 'start_btn'):
            self.start_btn.configure(state="normal" if can_start else "disabled")
        
        # Update cost estimate
        self._update_token_estimate()
    
    def _update_token_estimate(self):
        """Calculate and display estimated tokens for OpenRouter translations."""
        # Only show for OpenRouter/Groq with file, track, and API ready
        if (self.config.provider not in ["openrouter", "groq"] or 
            not self.current_file or 
            self.selected_track_id is None or
            not self.api_validated or
            self.is_processing): # Don't estimate while already processing
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
                self.current_file,
                self.selected_track_id,
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
        if self.settings_view:
            return
 
        # Create settings view
        self.settings_view = SettingsDialog(
            self,
            self.config,
            on_save=self._on_settings_save,
            on_close=self._close_settings
        )
        
        # Determine current content to hide/overlay
        # Cover the main container
        self.settings_view.grid(row=1, column=0, rowspan=2, sticky="nsew") # Span footer row too
        self.settings_view.lift()  # Ensure it's on top
        
        # Hide Footer
        if hasattr(self, 'footer_frame'):
            self.footer_frame.grid_remove()
        
        # Set initial values
        self.settings_view.remove_subs_var.set(self.remove_old_subs)

    def _close_settings(self):
        """Close settings view."""
        if self.settings_view:
            self.settings_view.destroy()
            self.settings_view = None
            
        # Restore Footer
        if hasattr(self, 'footer_frame'):
            self.footer_frame.grid()

    def _open_history(self):
        """Open history view."""
        if self.history_view:
            return

        # Create history view
        self.history_view = HistoryView(
            self,
            on_close=self._close_history
        )
        
        # Cover the main container
        self.history_view.grid(row=1, column=0, rowspan=2, sticky="nsew")
        self.history_view.lift()
        
        # Hide Footer
        if hasattr(self, 'footer_frame'):
            self.footer_frame.grid_remove()

    def _close_history(self):
        """Close history view."""
        if self.history_view:
            self.history_view.destroy()
            self.history_view = None
            
        # Restore Footer
        if hasattr(self, 'footer_frame'):
            self.footer_frame.grid()
    
    def _on_settings_save(self, settings: dict):
        """Handle settings save."""
        self.remove_old_subs = settings.get("remove_old_subs", True)
        self._init_mkv_handler()  # Reinitialize with new path
        
        # Sync API validation state
        manager = get_api_manager()
        self.api_validated = manager.is_configured
        self.selected_model = manager.selected_model
        
        # If AI settings changed, handle validation sync
        if settings.get("ai_settings_changed", False):
            if not manager.is_configured:
                # Check if we should auto-connect
                if self.config.provider == "ollama" or \
                   (self.config.provider == "openrouter" and self.config.openrouter_api_key) or \
                   (self.config.provider == "groq" and self.config.groq_api_key):
                    # Show connecting status first
                    self.is_validating = True
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
        self.current_file = file_path
        self._load_subtitle_tracks()
        self._update_step_states()
        
        # Auto-advance to Step 2
        self._on_step_change(2)

    
    def _load_subtitle_tracks(self):
        """Load subtitle tracks from the selected MKV file."""
        if not self.current_file or not self.mkv_handler:
            return
        
        self.selected_track_id = None
        
        try:
            self.subtitle_tracks = self.mkv_handler.get_subtitle_tracks(self.current_file)
            
            # Filter tracks (optional, but good to keep logic here)
            filtered_tracks = [t for t in self.subtitle_tracks if t.file_extension in ['.srt', '.ass']]
            
            # Update View
            view = self.step_frames[2]
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
            view = self.step_frames[2]
            view.set_model_status(f"Error: {str(e)}", COLORS["error"])
            view.no_tracks_label.configure(
                text=f"Error: {str(e)}",
                text_color=COLORS["error"]
            )
            view.no_tracks_label.grid()
            self.toast.error(f"Failed to load tracks: {str(e)}")
    
    def _on_track_select(self, track_id: int, is_selected: bool):
        """Handle track selection."""
        if is_selected:
            if self.selected_track_id == track_id:
                return
            
            # Deselect others (this will trigger callbacks, hence the guard above is important)
            for item in self.track_items:
                if item.track_id != track_id:
                    item.deselect()
            
            self.selected_track_id = track_id
        else:
            if self.selected_track_id != track_id:
                return
            self.selected_track_id = None
            
        # Update source language based on track info
        if self.selected_track_id is not None:
            track = next((t for t in self.subtitle_tracks if t.track_id == self.selected_track_id), None)
            if track and track.language:
                lang_code = track.language.lower()
                lang_name = self.LANGUAGE_MAPPING.get(lang_code)
                
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
                    self.logger.info(f"🌐 Auto-selected source language: {lang_name} (from track {self.selected_track_id})")

        self._update_step_states()
    
    def _on_model_change(self, model: str):
        """Handle model selection change."""
        self.selected_model = model
        self._update_step_states()
    
    def _validate_api(self):
        """Validate AI provider connection."""
        self.validate_btn.configure(state="disabled", text="...")
        self.model_status.configure(text="Connecting & fetching models...", text_color=COLORS["text_secondary"])
        self.model_dropdown.configure(state="disabled")
        self.title_bar.set_api_status(False, connecting=True)
        self.is_validating = True
        
        # Validate in background
        thread = threading.Thread(target=self._do_validate, daemon=True)
        thread.start()
    
    def _do_validate(self):
        """Perform validation in background."""
        try:
            # Get fresh manager
            manager = get_api_manager()
            result = manager.validate_connection()
            self.after(0, lambda: self._on_validate_result(result))
        except Exception as e:
            self.after(0, lambda e=e: self._on_validate_error(str(e)))
    
    def _on_validate_result(self, result):
        """Handle validation result."""
        self.is_validating = False
        self.validate_btn.configure(state="normal", text="Connect")
        
        if result.is_valid:
            self.api_validated = True
            models = [m.short_name for m in result.available_models]
            
            # Populate model dropdown
            if models:
                self.model_dropdown.configure(values=models, state="normal")
                
                # Try to select configured model if available
                configured_model = None
                if self.config.provider == "ollama":
                    configured_model = self.config.ollama_model
                elif self.config.provider == "openrouter":
                    configured_model = self.config.openrouter_model
                elif self.config.provider == "groq":
                    configured_model = self.config.groq_model
                
                if configured_model and configured_model in models:
                     self.selected_model = configured_model
                     self.model_dropdown.set(configured_model)
                else:
                    # Default selection logic
                    for model in models:
                        if "flash" in model.lower():
                            self.selected_model = model
                            self.model_dropdown.set(model)
                            break
                    else:
                        self.selected_model = models[0]
                        self.model_dropdown.set(models[0])
            
            self.model_status.configure(
                text="✓ Connected",
                text_color=COLORS["success"]
            )
            # Remove redundant button
            self.validate_btn.grid_forget()
            self.toast.success("API connected successfully")
        else:
            self.api_validated = False
            self.model_dropdown.configure(state="disabled")
            self.model_status.configure(text=result.message, text_color=COLORS["error"])
            # Show retry button
            self.validate_btn.configure(text="Retry")
            self.validate_btn.grid(row=0, column=3, padx=SPACING["md"], pady=SPACING["sm"])
            self.toast.error(result.message)
        
        self._update_step_states()
        
        # Check for pending resume
        if getattr(self, '_pending_resume', False) and self.api_validated:
            self._pending_resume = False
            self._do_resume()
    
    def _on_validate_error(self, error: str):
        """Handle validation error."""
        self.is_validating = False
        self.api_validated = False
        self.validate_btn.configure(state="normal", text="Connect")
        self.model_dropdown.configure(state="disabled")
        self.model_status.configure(text="Connection failed", text_color=COLORS["error"])
        self.toast.error(f"Validation failed: {error}")
        self._update_step_states()
    
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
        self.is_processing = True
        self.title_bar.title_label.configure(text=f"{self.APP_TITLE} - Processing")
        
        # Switch to Step 3
        # Use set_step to update UI selection
        self.stepper.set_step(3)
        self._update_step_states() # Update completion status
        self._show_step(3)
        
        # Set file info in processing view
        if self.current_file:
            filename = Path(self.current_file).name
            track_info = ""
            for track in self.subtitle_tracks:
                if track.track_id == self.selected_track_id:
                    track_info = f"Track {track.track_id} - {track.language.upper()}"
                    break
            
            self.processing_view.set_file_info(filename, track_info)
    
    def _exit_processing_mode(self):
        """Return to normal mode or advance to review."""
        self.is_processing = False
        self.title_bar.title_label.configure(text=self.APP_TITLE)
        
        # If cancelled, go back to configuration (Step 2)
        if self.should_cancel:
             self._on_step_change(2)
        # If completed (logic handled in _on_translation_complete), we might stay or go to step 4
        # For general exit, let's assume we just update the view
        elif self.active_translator is None:
             # Just refresh current step
             self._show_step(self.stepper.current_step)
    
    def _start_translation(self):
        """Start the translation process by asking for title confirmation first."""
        if not self.api_validated:
            self.toast.warning("Please connect API first")
            return
        
        if not self.current_file or self.selected_track_id is None:
            self.toast.warning("Please select a file and track")
            return
            
        # Extract title automatically
        extracted_title = extract_anime_title(self.current_file)
        
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
            
        self.current_anime_title = reviewed_title.strip()
        
        self.is_processing = True
        self._pending_estimates.clear() # Cancel background work
        self._enter_processing_mode()
        
        # Intialize orchestrator
        if not hasattr(self, 'orchestrator'):
             from core.translation_orchestrator import TranslationOrchestrator
             self.orchestrator = TranslationOrchestrator(self.mkv_handler)
             
        self.orchestrator.set_callbacks(
             on_progress=self._on_translation_progress,
             on_complete=self._on_translation_orchestrator_complete,
             on_error=self._on_translation_error
        )
        
        source_lang = self.source_lang_row.get_value()
        target_lang = self.target_lang_row.get_value()
        model_used = self.selected_model or "gemini-1.5-flash"
        
        self.orchestrator.start_translation(
             self.current_file,
             self.selected_track_id,
             source_lang,
             target_lang,
             model_used,
             self.current_anime_title
        )
    
    def _on_translation_progress(self, current: int, total: int, status: str, token_usage: TokenUsage):
         """Handle translation progress callback."""
         status_color = None
         if status:
             if "Retrying" in status:
                  status_color = COLORS["warning"]
             elif "Finalizing" in status:
                  status_color = COLORS["success"]
         
         # Update processing view directly
         self.after(0, lambda: self.processing_view.update_progress_summary(
             current=current,
             total=total,
             status=status,
             status_color=status_color,
             tokens=token_usage
         ))
         
    def _on_translation_orchestrator_complete(self, payload: dict):
         """Handles completion from orchestrator before review."""
         self.after(0, lambda: self._show_review_editor(payload))
    
    def _pause_translation(self):
        """Pause translation."""
        if self.is_paused:
            # Resume
            self._do_resume()
        else:
            # Pause
            self.is_paused = True
            self.should_cancel = True
            if hasattr(self, 'orchestrator'):
                 self.orchestrator.pause()
            
            self.processing_view.set_paused(True)
            self.status_label.configure(text="Paused - progress saved")
    
    def _resume_translation(self):
        """Resume from saved state."""
        if not self.api_validated:
            self._pending_resume = True
            self.resume_btn.configure(state="disabled", text="Connecting...")
            self._validate_api()
            return

        self._do_resume()
    
    def _do_resume(self):
        """Actually resume translation."""
        self._pending_resume = False
        self.is_paused = False
        self.should_cancel = False
        self.is_processing = True
        
        self.processing_view.set_paused(False)
        self.resume_btn.pack_forget()
        
        self._enter_processing_mode()
        
        if hasattr(self, 'orchestrator'):
             self.orchestrator.resume()
             
             source_lang = self.source_lang_row.get_value()
             target_lang = self.target_lang_row.get_value()
             model_used = self.selected_model or "gemini-1.5-flash"
             anime_title = getattr(self, 'current_anime_title', None)
             
             # Call start again to resume background thread
             self.orchestrator.start_translation(
                 self.current_file,
                 self.selected_track_id,
                 source_lang,
                 target_lang,
                 model_used,
                 anime_title
             )
    
    def _cancel_translation(self):
        """Cancel translation."""
        self.should_cancel = True
        self.is_processing = False
        if hasattr(self, 'orchestrator'):
             self.orchestrator.cancel()
        
        self._exit_processing_mode()
        self.toast.info("Translation cancelled")
    
    def _on_translation_complete(self, summary: dict):
        """Handle validation after merge complete."""
        self.is_processing = False
        self.processing_view.set_completed()
        
        tokens = summary.get("tokens")
        if tokens:
             self.toast.success(f"Translation complete! {tokens.total_tokens:,} tokens used")
        else:
             self.toast.success("Translation complete!")
        
        # Mark all steps complete
        self.stepper.set_step(5)
        self.last_summary_data = {
            "output_path": summary.get("output_path", ""),
            "lines_translated": summary.get("lines_translated", 0),
            "model_used": summary.get("model_used", ""),
            "duration_seconds": summary.get("duration_seconds", 0),
            "removed_old_subs": summary.get("removed_old_subs", False),
            "prompt_tokens": tokens.prompt_tokens if tokens else 0,
            "completion_tokens": tokens.completion_tokens if tokens else 0,
            "total_tokens": tokens.total_tokens if tokens else 0,
            "estimated_cost": summary.get("estimated_cost", 0),
            "provider": self.config.provider
        }

        # Show summary
        self.summary_view = SummaryWindow(
            self,
            **self.last_summary_data,
            on_open_folder=lambda: os.startfile(Path(summary["output_path"]).parent) if summary.get("output_path") else None,
            on_close=self._close_summary
        )
        self.summary_view.grid(row=1, column=0, rowspan=2, sticky="nsew")
        self.summary_view.lift()
        
        if self.state_manager:
            self.state_manager.clear()
            
        self.after(2000, self._exit_processing_mode)
    
    def _close_summary(self):
        """Close summary view and reset app for next file."""
        if hasattr(self, 'summary_view') and self.summary_view:
            self.summary_view.destroy()
            self.summary_view = None
            
        self._reset_app()
    
    def _on_translation_error(self, error: str):
        """Handle translation error."""
        self.is_processing = False
        self.processing_view.set_error(error[:50])
        self.toast.error(f"Translation failed: {error}")
        
        self.after(3000, self._exit_processing_mode)
    
    def _show_review_editor(self, payload: dict):
        """Show the subtitle review editor."""
        self.is_processing = False
        self._exit_processing_mode()
        self.merge_payload = payload
        
        # Update view
        view = self.step_frames[4]
        view.show_payload(payload)
        
        # Update Stepper
        self._show_step(4)
        self.toast.info("Translation complete! Please review the subtitles.")
    
    def _on_review_approved(self, content: str):
        """Handle review approval - save edited content and merge."""
        try:
            # Save edited content back to file
            with open(self.merge_payload["translated_sub_path"], 'wt', encoding='utf-8') as f:
                f.write(content)
            
            # Finalize merge via service
            self.toast.info("Finalizing merge into video...")
            summary = self.finalization_service.finalize_merge(
                self.merge_payload, 
                remove_old_subs=self.remove_old_subs
            )
            self._on_translation_complete(summary)
            
        except Exception as e:
            self.toast.error(f"Merge failed: {str(e)}")
            self.logger.error(f"Finalize merge error: {e}")
            
    def _on_review_discarded(self):
        """Handle review discard - clean up and reset."""
        self.finalization_service.cleanup_temp_files(self.merge_payload) 
        if self.state_manager:
            self.state_manager.clear()
        self.merge_payload = None
        self._on_step_change(2) # Back to config
        self.toast.info("Translation discarded")
    
    
    def _check_resumable_state(self):
        """Check for resumable state."""
        state = self.state_manager.load()
        if not state:
            return
        
        if not os.path.exists(state.source_file):
            self.state_manager.clear()
            return
        
        # Ask user
        if messagebox.askyesno(
            "Resume Translation?",
            f"Found incomplete translation:\n{Path(state.source_file).name}\n\n"
            f"Progress: {state.progress_percent:.1f}%\n"
            "Resume?"
        ):
            self.current_file = state.source_file
            self.file_drop.set_file(state.source_file)
            self._load_subtitle_tracks()
            
            if state.track_id:
                self.after(500, lambda: self._select_track_by_id(state.track_id))
            
            self.source_lang_row.set_value(state.source_lang)
            self.target_lang_row.set_value(state.target_lang)
            self.selected_model = state.model_name
            
            # Show resume button
            self.start_btn.pack_forget()
            self.resume_btn.pack(side="left")
            self.status_label.configure(text="Ready to resume")
        else:
            self.state_manager.clear()
    
    def _select_track_by_id(self, track_id: int):
        """Select track by ID."""
        for item in self.track_items:
            if item.track_id == track_id:
                item.select()
                self.selected_track_id = track_id
                self._update_step_states()
                break
    
    def _reset_app(self):
        """Reset app to initial state."""
        self.current_file = None
        self.file_drop.reset()
        
        for item in self.track_items:
            item.destroy()
        self.track_items.clear()
        self.selected_track_id = None
        self.no_tracks_label.grid()
        
        self.is_processing = False
        self.is_paused = False
        self.should_cancel = False
        # Clear payload to ensure Step 3/4 reset
        if hasattr(self, 'merge_payload'):
            self.merge_payload = None
        
        self._on_step_change(1) # Go back to step 1
        self._update_step_states()
        self.status_label.configure(text="")
        
        self.resume_btn.pack_forget()
        self.start_btn.pack(side="left")
    
    def _show_last_summary(self):
        """Re-open the last summary window."""
        if self.last_summary_data:
            from pathlib import Path
            output_path = Path(self.last_summary_data["output_path"])
            
            if hasattr(self, 'summary_view') and self.summary_view:
                self.summary_view.destroy()
            
            self.summary_view = SummaryWindow(
                self,
                **self.last_summary_data,
                on_open_folder=lambda: os.startfile(output_path.parent),
                on_close=self._close_summary
            )
            self.summary_view.grid(row=1, column=0, rowspan=2, sticky="nsew")
            self.summary_view.lift()

    def _on_close(self):
        """Handle window close."""
        if self.is_processing and not self.is_paused:
            if not messagebox.askokcancel("Quit", "Translation in progress. Quit?"):
                return
        
        self.should_cancel = True
        self.quit()
        self.destroy()
        sys.exit(0)

def run_app():
    """Run the Sub-auto application."""
    app = SubAutoApp()
    app.mainloop()
