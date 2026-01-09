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
    LogPanel, CollapsibleFrame, CustomTitleBar, SubtitleEditor
)
from .step_card import StepCard
from .settings_dialog import SettingsDialog
from .toast import ToastManager
from .processing_view import ProcessingView

from core.config_manager import get_config, ConfigManager
from core.mkv_handler import MKVHandler, SubtitleTrack
from core.subtitle_parser import SubtitleParser
from core.translator import Translator, get_api_manager, TokenUsage, validate_and_save_api_key
from core.state_manager import get_state_manager, StateManager
from core.logger import get_logger, Logger


class SubAutoApp(ctk.CTk):
    """Main application window for Sub-auto."""
    
    APP_TITLE = "Sub-auto"
    APP_VERSION = "1.2.0"
    WINDOW_SIZE = (700, 520)
    MIN_SIZE = (650, 480)
    
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
        self.logger = get_logger()
        self.remove_old_subs = True
        self._pending_resume = False
        self.active_translator: Optional[Translator] = None
        
        # Initialize MKV handler
        self._init_mkv_handler()
        
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
        """Setup the main UI - single page layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Content area expands
        self.grid_rowconfigure(1, weight=1)  # Content area expands
        
        # Custom Title Bar (replaces Windows default)
        self.title_bar = CustomTitleBar(
            self,
            title=self.APP_TITLE,
            version=self.APP_VERSION,
            on_settings=self._open_settings,
            show_settings=True,
            is_dialog=False
        )
        self.title_bar.grid(row=0, column=0, sticky="ew")
        
        # Main content - scrollable
        self.content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=SPACING["sm"], pady=(0, SPACING["sm"]))
        self.content.grid_columnconfigure(0, weight=1)
        
        # Normal view container
        self.normal_view = ctk.CTkFrame(self.content, fg_color="transparent")
        self.normal_view.pack(fill="both", expand=True)
        self.normal_view.grid_columnconfigure(0, weight=1)
        
        # Processing view (hidden initially)
        self.processing_view = ProcessingView(
            self.content,
            logger_instance=self.logger,
            on_pause=self._pause_translation,
            on_cancel=self._cancel_translation
        )
        
        # Step 1: File Selection
        self._create_step1()
        
        # Step 2: Track Selection
        self._create_step2()
        
        # Step 3: Translation Options
        self._create_step3()
        
        # Footer with action buttons
        self._create_footer()
        
        # Initial step states
        self._update_step_states()
    
    def _create_step1(self):
        """Create Step 1: File Selection."""
        self.step1 = StepCard(
            self.normal_view,
            step_number=1,
            title="Select Video File",
            state="active"
        )
        self.step1.pack(fill="x", pady=(0, SPACING["sm"]))
        
        content = self.step1.get_content_frame()
        
        # File drop zone
        self.file_drop = FileDropZone(
            content,
            on_file_selected=self._on_file_selected,
            height=100
        )
        self.file_drop.pack(fill="x")
    
    def _create_step2(self):
        """Create Step 2: Track Selection."""
        self.step2 = StepCard(
            self.normal_view,
            step_number=2,
            title="Select Subtitle Track",
            state="inactive"
        )
        self.step2.pack(fill="x", pady=(0, SPACING["sm"]))
        
        content = self.step2.get_content_frame()
        
        # Tracks container
        self.tracks_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.tracks_frame.pack(fill="x")
        self.tracks_frame.grid_columnconfigure(0, weight=1)
        
        # Placeholder text
        self.no_tracks_label = ctk.CTkLabel(
            self.tracks_frame,
            text="Select an MKV file to see subtitle tracks",
            **get_label_style("muted")
        )
        self.no_tracks_label.grid(row=0, column=0, pady=SPACING["lg"])
        
        self.track_items: List[TrackListItem] = []
    
    def _create_step3(self):
        """Create Step 3: Translation Options."""
        self.step3 = StepCard(
            self.normal_view,
            step_number=3,
            title="Translation Options",
            state="inactive"
        )
        self.step3.pack(fill="x", pady=(0, SPACING["sm"]))
        
        content = self.step3.get_content_frame()
        
        # Options grid
        options_frame = ctk.CTkFrame(content, fg_color="transparent")
        options_frame.pack(fill="x")
        options_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Source language
        self.source_lang_row = SettingsRow(
            options_frame,
            label="From",
            input_type="dropdown",
            options=["English", "Japanese", "Korean", "Chinese", "Auto-detect"],
            default_value="English"
        )
        self.source_lang_row.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]), pady=SPACING["xs"])
        self.source_lang_row.label.configure(width=50)
        
        # Target language
        self.target_lang_row = SettingsRow(
            options_frame,
            label="To",
            input_type="dropdown",
            options=["Indonesian"],
            default_value="Indonesian"
        )
        self.target_lang_row.grid(row=0, column=1, sticky="ew", padx=(SPACING["sm"], 0), pady=SPACING["xs"])
        self.target_lang_row.label.configure(width=50)
        
        # Model selection row
        model_frame = ctk.CTkFrame(options_frame, fg_color=COLORS["bg_medium"], corner_radius=RADIUS["md"])
        model_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SPACING["sm"], 0))
        model_frame.grid_columnconfigure(2, weight=1)
        
        model_label = ctk.CTkLabel(
            model_frame,
            text="Model:",
            **get_label_style("body")
        )
        model_label.grid(row=0, column=0, padx=SPACING["md"], pady=SPACING["sm"])
        
        # Model dropdown (hidden initially)
        self.model_dropdown = ctk.CTkOptionMenu(
            model_frame,
            values=["Not connected"],
            command=self._on_model_change,
            fg_color=COLORS["bg_light"],
            button_color=COLORS["bg_medium"],
            button_hover_color=COLORS["border"],
            dropdown_fg_color=COLORS["bg_dark"],
            dropdown_hover_color=COLORS["bg_light"],
            corner_radius=RADIUS["md"],
            width=180,
            state="disabled"
        )
        self.model_dropdown.grid(row=0, column=1, padx=SPACING["sm"], pady=SPACING["sm"])
        
        # Status indicator with token estimate below
        status_frame = ctk.CTkFrame(model_frame, fg_color="transparent")
        status_frame.grid(row=0, column=2, sticky="w", padx=SPACING["sm"])
        
        self.model_status = ctk.CTkLabel(
            status_frame,
            text="⚠ Not connected",
            text_color=COLORS["text_muted"],
            font=(FONTS["family"], FONTS["small_size"])
        )
        self.model_status.pack(side="left")

        # Cost estimate label (inline)
        self.cost_estimate_label = ctk.CTkLabel(
            status_frame,
            text="",
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["success"]
        )
        self.cost_estimate_label.pack(side="left", padx=(SPACING["sm"], 0))
        
        # Connect button (only show if not auto-connected)
        self.validate_btn = ctk.CTkButton(
            model_frame,
            text="Connect",
            width=80,
            command=self._validate_api,
            **get_button_style("secondary")
        )
        # Initially hidden if we auto-connect, shown on error
        # self.validate_btn.grid(row=0, column=3, padx=SPACING["md"], pady=SPACING["sm"])
    
    def _create_footer(self):
        """Create footer with action buttons."""
        # Add separator line
        separator = ctk.CTkFrame(self.normal_view, height=2, fg_color=COLORS["bg_medium"])
        separator.pack(fill="x", pady=(SPACING["md"], SPACING["sm"]))
        
        footer = ctk.CTkFrame(self.normal_view, fg_color="transparent")
        footer.pack(fill="x", pady=SPACING["sm"])
        footer.grid_columnconfigure(0, weight=1)
        
        # Left side - status
        self.status_label = ctk.CTkLabel(
            footer,
            text="",
            **get_label_style("muted")
        )
        self.status_label.grid(row=0, column=0, sticky="w")
        
        # Right side - buttons
        buttons = ctk.CTkFrame(footer, fg_color="transparent")
        buttons.grid(row=0, column=1, sticky="e")
        
        self.reset_btn = ctk.CTkButton(
            buttons,
            text="Reset",
            width=80,
            command=self._reset_app,
            **get_button_style("secondary")
        )
        self.reset_btn.pack(side="left", padx=(0, SPACING["lg"]))
        
        self.show_summary_btn = ctk.CTkButton(
            buttons,
            text="Show Summary",
            width=120,
            command=self._show_last_summary,
            **get_button_style("secondary")
        )
        self.show_summary_btn.pack(side="left", padx=(0, SPACING["lg"]))
        self.show_summary_btn.pack_forget()

        self.start_btn = ctk.CTkButton(
            buttons,
            text="Start Translation",
            width=150,
            font=(FONTS["family"], FONTS["subheading_size"], "bold"),
            command=self._start_translation,
            **get_button_style("info")
        )
        self.start_btn.pack(side="left")
        
        # Resume button (hidden by default)
        self.resume_btn = ctk.CTkButton(
            buttons,
            text="Resume",
            width=120,
            command=self._resume_translation,
            **get_button_style("success")
        )
        
        # Initial button state
        self.start_btn.configure(state="disabled")
    
    def _update_step_states(self):
        """Update step card states based on current progress."""
        has_file = self.current_file is not None
        has_track = self.selected_track_id is not None
        api_ready = self.api_validated
        
        # Step 1: Always active, completed when file selected
        if has_file:
            self.step1.set_state("completed")
            path = Path(self.current_file)
            size = path.stat().st_size / (1024 * 1024 * 1024)  # GB
            self.step1.set_subtitle(f"{path.name} ({size:.2f} GB)")
        else:
            self.step1.set_state("active")
            self.step1.clear_subtitle()
        
        # Step 2: Active after file, completed when track selected
        if has_file:
            if has_track:
                self.step2.set_state("completed")
                # Find track info for subtitle
                for track in self.subtitle_tracks:
                    if track.track_id == self.selected_track_id:
                        self.step2.set_subtitle(f"Track {track.track_id} - {track.language.upper()}")
                        break
            else:
                self.step2.set_state("active")
                self.step2.clear_subtitle()
        else:
            self.step2.set_state("inactive")
        
        # Step 3: Active after track selected
        if has_file and has_track:
            if api_ready:
                self.step3.set_state("completed")
                self.step3.set_subtitle(f"{self.selected_model}")
            else:
                self.step3.set_state("active")
                self.step3.clear_subtitle()
        else:
            self.step3.set_state("inactive")
        
        # Update start button
        can_start = has_file and has_track and api_ready
        self.start_btn.configure(state="normal" if can_start else "disabled")
        
        # Update title bar API status
        self.title_bar.set_api_status(api_ready, self.selected_model or "")
        
        # Update cost estimate
        self._update_token_estimate()
    
    def _update_token_estimate(self):
        """Calculate and display estimated tokens for OpenRouter translations."""
        # Only show for OpenRouter/Groq with file, track, and API ready
        if (self.config.provider not in ["openrouter", "groq"] or 
            not self.current_file or 
            self.selected_track_id is None or
            not self.api_validated):
            self.cost_estimate_label.configure(text="")
            return
        
        try:
            from core.translator import get_api_manager
            api_manager = get_api_manager()
            model_info = api_manager.get_selected_model_info()
            
            if not model_info:
                self.cost_estimate_label.configure(text="")
                return
            
            # Check cache - avoid re-extracting subtitle
            cache_key = f"{self.current_file}:{self.selected_track_id}"
            if not hasattr(self, '_subtitle_cache'):
                self._subtitle_cache = {}
            
            if cache_key in self._subtitle_cache:
                total_chars, line_count = self._subtitle_cache[cache_key]
            else:
                # Show loading indicator
                self.cost_estimate_label.configure(text="💰 Calculating...")
                
                # Run extraction in background
                def do_estimate():
                    try:
                        extracted_path = self.mkv_handler.extract_subtitle(
                            self.current_file,
                            self.selected_track_id
                        )
                        
                        parser = SubtitleParser()
                        lines = parser.load(extracted_path)
                        
                        # Clean up extracted file
                        try:
                            Path(extracted_path).unlink()
                        except Exception:
                            pass
                        
                        total_chars = sum(len(line.text) for line in lines)
                        line_count = len(lines)
                        
                        # Cache the result
                        self._subtitle_cache[cache_key] = (total_chars, line_count)
                        
                        # Update on main thread
                        self.after(0, lambda: self._display_token_estimate(model_info, total_chars, line_count))
                    except Exception as e:
                        self.after(0, lambda: self.cost_estimate_label.configure(text=""))
                
                import threading
                thread = threading.Thread(target=do_estimate, daemon=True)
                thread.start()
                return
            
            # Calculate and display from cache
            self._display_token_estimate(model_info, total_chars, line_count)
            
        except Exception as e:
            self.logger.warning(f"Failed to estimate list: {e}")
            self.cost_estimate_label.configure(text="")
    
    def _display_token_estimate(self, model_info, total_chars: int, line_count: int):
        """Display the token estimate based on cached subtitle data."""
        # Estimate tokens (rough: 4 chars per token)
        estimated_prompt_tokens = (total_chars // 4) + (line_count * 50)  # Text + prompt overhead
        estimated_completion_tokens = total_chars // 4  # Similar output size
        total_estimated_tokens = estimated_prompt_tokens + estimated_completion_tokens
        
        # Format token count
        if total_estimated_tokens >= 1000:
            token_text = f"{total_estimated_tokens / 1000:.1f}K"
        else:
            token_text = f"{total_estimated_tokens}"
        
        # Display only tokens, NO cost
        display_text = f"💰 ~{token_text} tokens"
        
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
        # We want to cover everything below the main title bar (row 1 and 2)
        self.settings_view.grid(row=1, column=0, rowspan=2, sticky="nsew")
        self.settings_view.lift()  # Ensure it's on top
        
        # Set initial values
        self.settings_view.remove_subs_var.set(self.remove_old_subs)

    def _close_settings(self):
        """Close settings view."""
        if self.settings_view:
            self.settings_view.destroy()
            self.settings_view = None
    
    def _on_settings_save(self, settings: dict):
        """Handle settings save."""
        self.remove_old_subs = settings.get("remove_old_subs", True)
        self._init_mkv_handler()  # Reinitialize with new path
        
        # If API key changed, re-validate
        if settings.get("ai_settings_changed", False):
            self.api_validated = False
            self._update_step_states()
            
            # Auto-connect if OLLAMA or OpenRouter with key
            if self.config.provider == "ollama" or \
               (self.config.provider == "openrouter" and self.config.openrouter_api_key) or \
               (self.config.provider == "groq" and self.config.groq_api_key):
                self._validate_api()
            else:
                self.toast.info("AI settings updated. Please reconnect.")
        else:
            self.toast.success("Settings saved")
    
    def _on_file_selected(self, file_path: str):
        """Handle file selection."""
        self.current_file = file_path
        self._load_subtitle_tracks()
        self._update_step_states()
    
    def _load_subtitle_tracks(self):
        """Load subtitle tracks from the selected MKV file."""
        if not self.current_file or not self.mkv_handler:
            return
        
        # Clear existing tracks
        for item in self.track_items:
            item.destroy()
        self.track_items.clear()
        self.selected_track_id = None
        
        try:
            self.subtitle_tracks = self.mkv_handler.get_subtitle_tracks(self.current_file)
            
            if not self.subtitle_tracks:
                self.no_tracks_label.configure(
                    text="No subtitle tracks found",
                    text_color=COLORS["warning"]
                )
                self.no_tracks_label.grid()
                return
            
            # Hide placeholder
            self.no_tracks_label.grid_remove()
            
            # Create track items
            for i, track in enumerate(self.subtitle_tracks):
                if track.file_extension not in ['.srt', '.ass']:
                    continue
                
                item = TrackListItem(
                    self.tracks_frame,
                    track_id=track.track_id,
                    track_name=track.track_name,
                    language=track.language,
                    codec=track.codec,
                    is_default=track.default_track,
                    on_select=self._on_track_select
                )
                item.grid(row=i, column=0, sticky="ew", pady=SPACING["xs"])
                self.track_items.append(item)
            
            # Auto-select first track
            if self.track_items:
                self.track_items[0].select()
                self.selected_track_id = self.subtitle_tracks[0].track_id
                self._update_step_states()
                
                # Auto-collapse step 1 to save space
                self.step1.collapse()
                self.after(50, self._reset_scroll)
                
        except Exception as e:
            self.no_tracks_label.configure(
                text=f"Error: {str(e)}",
                text_color=COLORS["error"]
            )
            self.no_tracks_label.grid()
            self.toast.error(f"Failed to load tracks: {str(e)}")
    
    def _on_track_select(self, track_id: int, is_selected: bool):
        """Handle track selection."""
        if is_selected:
            for item in self.track_items:
                if item.track_id != track_id:
                    item.deselect()
            self.selected_track_id = track_id
            
            # Auto-collapse Step 2 when there are multiple tracks (>2) to save space
            if len(self.track_items) > 2:
                self.step2.collapse()
                # Workaround: Reset scroll to prevent content disappearance when collapsing from bottom
                self.after(50, self._reset_scroll)
        else:
            if self.selected_track_id == track_id:
                self.selected_track_id = None
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
        self.validate_btn.configure(state="normal", text="Connect")
        self.model_dropdown.configure(state="disabled")
        self.model_status.configure(text="Connection failed", text_color=COLORS["error"])
        self.toast.error(f"Validation failed: {error}")
    
    def _load_saved_api_key(self):
        """Load saved configuration and auto-validate."""
        if self.config.provider == "openrouter" and self.config.openrouter_api_key:
            self.after(1000, self._validate_api)
        elif self.config.provider == "ollama":
            self.after(1000, self._validate_api)
        elif self.config.provider == "groq" and self.config.groq_api_key:
            self.after(1000, self._validate_api)
    
    def _enter_processing_mode(self):
        """Switch to compact processing mode."""
        # Hide normal view
        self.normal_view.pack_forget()
        
        # Show processing view
        self.processing_view.pack(fill="both", expand=True)
        
        # Set file info
        if self.current_file:
            filename = Path(self.current_file).name
            track_info = ""
            for track in self.subtitle_tracks:
                if track.track_id == self.selected_track_id:
                    track_info = f"Track {track.track_id} ({track.language.upper()}) → Indonesian"
                    break
            self.processing_view.set_file_info(filename, track_info)
        
        # Hide footer buttons, show in processing view
        self.start_btn.pack_forget()
        self.reset_btn.pack_forget()
        self.resume_btn.pack_forget()
        self.show_summary_btn.pack_forget()
    
    def _exit_processing_mode(self):
        """Return to normal mode."""
        self.processing_view.pack_forget()
        self.normal_view.pack(fill="both", expand=True)
        
        # Restore footer buttons
        self.reset_btn.pack(side="left", padx=(0, SPACING["md"]))
        
        if self.last_summary_data:
             self.show_summary_btn.pack(side="left", padx=(0, SPACING["md"]))
             
        self.start_btn.pack(side="left")
        self.start_btn.configure(state="normal")
    
    def _start_translation(self):
        """Start the translation process."""
        if not self.api_validated:
            self.toast.warning("Please connect API first")
            return
        
        if not self.current_file or self.selected_track_id is None:
            self.toast.warning("Please select a file and track")
            return
        
        self.is_processing = True
        self._enter_processing_mode()
        
        # Start in background
        thread = threading.Thread(target=self._run_translation, daemon=True)
        thread.start()
    
    def _run_translation(self):
        """Run the translation process in background."""
        start_time = time.time()
        lines_count = 0
        model_used = self.selected_model or "gemini-1.5-flash"
        
        try:
            # Check for resume state
            resume_state = None
            if self.state_manager.has_resumable_state(self.current_file):
                state = self.state_manager.load()
                if state and state.track_id == self.selected_track_id:
                    resume_state = state
            
            # Extract subtitle
            extracted_path = self.mkv_handler.extract_subtitle(
                self.current_file,
                self.selected_track_id
            )
            
            # Parse subtitle
            parser = SubtitleParser()
            lines = parser.load(extracted_path)
            total_lines = len(lines)
            lines_count = total_lines
            
            # Initialize translator
            api_manager = get_api_manager()
            translator = Translator(model_manager=api_manager)
            self.active_translator = translator  # Store reference
            success, msg = translator.initialize()
            
            if not success:
                raise RuntimeError(f"Failed to initialize: {msg}")
            
            source_lang = self.source_lang_row.get_value()
            target_lang = self.target_lang_row.get_value()
            
            def progress_callback(current, total, status, token_usage: TokenUsage):
                if self.should_cancel or self.is_paused:
                    return
                
                percent = (current / total) * 100
                self.after(0, lambda: self.processing_view.set_progress(percent, current, total))
                
                # Update status message if provided
                if status:
                    # Choose color based on status content
                    color = None
                    if "Retrying" in status:
                        color = COLORS["warning"]
                    elif "Finalizing" in status:
                        color = COLORS["success"]
                    
                    self.after(0, lambda: self.processing_view.set_status(status, color))
                
                self.after(0, lambda: self.processing_view.set_token_stats(
                    token_usage.prompt_tokens,
                    token_usage.completion_tokens,
                    token_usage.total_tokens
                ))
            
            # Create state if not resuming
            if not resume_state:
                self.state_manager.create_state(
                    source_file=self.current_file,
                    track_id=self.selected_track_id,
                    total_lines=total_lines,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    model_name=model_used
                )
            
            def state_callback(current, total, status, token_usage):
                progress_callback(current, total, status, token_usage)
                if self.should_cancel:
                    raise KeyboardInterrupt("Cancelled")
            
            translations, errors, final_tokens = translator.translate_all(
                lines=lines,
                source_lang=source_lang,
                target_lang=target_lang,
                batch_size=self.config.batch_size,
                progress_callback=state_callback,
                state_manager=self.state_manager
            )
            
            # Apply translations
            parser.apply_translations(translations)
            
            # Save translated subtitle
            input_path = Path(self.current_file)
            output_dir = self.config.default_output_dir or str(input_path.parent)
            
            # Sanitize model name for filename
            sanitized_model = model_used.replace("/", "_").replace(":", "_").replace("\\", "_")
            
            translated_sub_path = Path(output_dir) / f"{input_path.stem}_{sanitized_model}_translated.srt"
            parser.save(str(translated_sub_path))
            
            # PAUSE HERE - Show review editor instead of immediately merging
            # Prepare payload for merge step
            merge_payload = {
                "current_file": self.current_file,
                "translated_sub_path": str(translated_sub_path),
                "output_dir": output_dir,
                "input_path": input_path,
                "sanitized_model": sanitized_model,
                "model_used": model_used,
                "extracted_path": extracted_path,
                "lines_count": lines_count,
                "start_time": start_time,
                "final_tokens": final_tokens,
                "api_manager": api_manager
            }
            
            # Show review editor on main thread
            self.after(0, lambda: self._show_review_editor(merge_payload))
            
        except Exception as e:
            if self.is_paused or self.should_cancel:
                return
            self.after(0, lambda e=e: self._on_translation_error(str(e)))
        finally:
            self.active_translator = None
    
    def _pause_translation(self):
        """Pause translation."""
        if self.is_paused:
            # Resume
            if self.active_translator:
                self.active_translator.is_paused = False
            self._do_resume()
        else:
            # Pause
            self.is_paused = True
            self.should_cancel = True
            if self.active_translator:
                self.active_translator.is_paused = True
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
        
        thread = threading.Thread(target=self._run_translation, daemon=True)
        thread.start()
    
    def _cancel_translation(self):
        """Cancel translation."""
        self.should_cancel = True
        self.is_processing = False
        if self.active_translator:
            self.active_translator.should_stop = True
            self.active_translator = None
        self._exit_processing_mode()
        self.toast.info("Translation cancelled")
    
    def _on_translation_complete(self, summary: dict):
        """Handle translation completion."""
        self.is_processing = False
        self.processing_view.set_completed()
        
        tokens = summary["tokens"]
        self.toast.success(f"Translation complete! {tokens.total_tokens:,} tokens used")
        
        # Store summary data for re-opening
        self.last_summary_data = {
            "output_path": summary["output_path"],
            "lines_translated": summary["lines_translated"],
            "model_used": summary["model_used"],
            "duration_seconds": summary["duration_seconds"],
            "removed_old_subs": summary["removed_old_subs"],
            "prompt_tokens": tokens.prompt_tokens,
            "completion_tokens": tokens.completion_tokens,
            "total_tokens": tokens.total_tokens,
            "estimated_cost": summary.get("estimated_cost"),
            "provider": self.config.provider
        }
        
        # Show the "Show Summary" button
        # Button will be packed in _exit_processing_mode

        # Show summary
        self.summary_view = SummaryWindow(
            self,
            **self.last_summary_data,
            on_open_folder=lambda: os.startfile(Path(summary["output_path"]).parent),
            on_close=self._close_summary
        )
        self.summary_view.grid(row=1, column=0, rowspan=2, sticky="nsew")
        self.summary_view.lift()
        
        # Reset state
        # self.token_accumulator = TokenUsage() # This is not used here, token_accumulator is managed by Translator
        if self.state_manager:
            self.state_manager.clear() # Use clear() instead of clear_state()
            
        # Exit processing mode after delay
        self.after(2000, self._exit_processing_mode)
    
    def _close_summary(self):
        """Close summary view."""
        if hasattr(self, 'summary_view') and self.summary_view:
            self.summary_view.destroy()
            self.summary_view = None
    
    def _on_translation_error(self, error: str):
        """Handle translation error."""
        self.is_processing = False
        self.processing_view.set_error(error[:50])
        self.toast.error(f"Translation failed: {error}")
        
        # Exit processing mode after delay
        self.after(3000, self._exit_processing_mode)
    
    def _show_review_editor(self, payload: dict):
        """Show the subtitle review editor."""
        self.is_processing = False
        self._exit_processing_mode()
        
        # Store payload for later use
        self.merge_payload = payload
        
        # Create and show editor as a toplevel window
        if hasattr(self, 'editor_view') and self.editor_view:
            try:
                self.editor_view.destroy()
            except:
                pass
        
        self.editor_view = SubtitleEditor(
            self,
            subtitle_path=payload["translated_sub_path"],
            on_approve=self._on_review_approved,
            on_discard=self._on_review_discarded
        )
        # No need to grid() - it's a toplevel window now
        
        self.toast.info("Translation complete! Please review the subtitles.")
    
    def _on_review_approved(self, content: str):
        """Handle review approval - save edited content and merge."""
        try:
            # Save edited content back to file
            with open(self.merge_payload["translated_sub_path"], 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Editor window closes itself
            
            # Proceed with merge
            self.toast.info("Merging subtitle into video...")
            self._finalize_merge(self.merge_payload)
            
        except Exception as e:
            self.toast.error(f"Failed to save changes: {str(e)}")
            self.logger.error(f"Review approval error: {e}")
    
    def _on_review_discarded(self):
        """Handle review discard - clean up and reset."""
        try:
            # Clean up translated subtitle file
            translated_sub_path = Path(self.merge_payload["translated_sub_path"])
            if translated_sub_path.exists():
                translated_sub_path.unlink()
            
            # Clean up extracted subtitle file
            extracted_path = self.merge_payload.get("extracted_path")
            if extracted_path and Path(extracted_path).exists():
                Path(extracted_path).unlink()
            
            # Editor window closes itself
            
            # Clear state
            self.state_manager.clear()
            self.merge_payload = None
            
            self.toast.info("Translation discarded")
            
        except Exception as e:
            self.logger.warning(f"Cleanup error during discard: {e}")
    
    def _finalize_merge(self, payload: dict):
        """Finalize the merge process after review approval."""
        try:
            # Merge into MKV
            input_path = payload["input_path"]
            output_dir = payload["output_dir"]
            sanitized_model = payload["sanitized_model"]
            model_used = payload["model_used"]
            
            output_mkv_path = Path(output_dir) / f"{input_path.stem}_{sanitized_model}_translated.mkv"
            
            self.mkv_handler.replace_subtitle(
                mkv_path=payload["current_file"],
                subtitle_path=payload["translated_sub_path"],
                output_path=str(output_mkv_path),
                language="ind",
                track_name=f"Indonesian ({model_used})",
                remove_existing_subs=self.remove_old_subs
            )
            
            # Clean up temporary files
            try:
                # Remove extracted subtitle file
                extracted_path = payload.get("extracted_path")
                if extracted_path and Path(extracted_path).exists():
                    Path(extracted_path).unlink()
                    self.logger.info(f"Cleaned up: {extracted_path}")
                
                # Remove translated subtitle file
                translated_sub_path = Path(payload["translated_sub_path"])
                if translated_sub_path.exists():
                    translated_sub_path.unlink()
                    self.logger.info(f"Cleaned up: {translated_sub_path}")
            except Exception as cleanup_error:
                self.logger.warning(f"Failed to clean up temp files: {cleanup_error}")
            
            # Done
            duration = time.time() - payload["start_time"]
            self.state_manager.clear()
            
            # Calculate cost estimation if using OpenRouter
            estimated_cost = None
            if self.config.provider == "openrouter":
                api_manager = payload["api_manager"]
                model_info = api_manager.get_selected_model_info()
                if model_info:
                    final_tokens = payload["final_tokens"]
                    estimated_cost = model_info.calculate_cost(
                        final_tokens.prompt_tokens,
                        final_tokens.completion_tokens
                    )
            
            summary = {
                "output_path": str(output_mkv_path),
                "lines_translated": payload["lines_count"],
                "model_used": model_used,
                "duration_seconds": duration,
                "removed_old_subs": self.remove_old_subs,
                "tokens": payload["final_tokens"],
                "estimated_cost": estimated_cost
            }
            
            self._on_translation_complete(summary)
            
        except Exception as e:
            self.toast.error(f"Merge failed: {str(e)}")
            self.logger.error(f"Merge error: {e}")
    
    
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


    
    def _reset_scroll(self):
        """Reset scroll position to top."""
        try:
            self.content._parent_canvas.yview_moveto(0.0)
        except Exception:
            pass

def run_app():
    """Run the Sub-auto application."""
    app = SubAutoApp()
    app.mainloop()
