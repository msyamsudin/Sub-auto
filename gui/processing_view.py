"""
Processing View Component for Sub-auto
Compact view shown during translation processing.
"""

import customtkinter as ctk
from typing import Optional, Callable
from pathlib import Path

from .components import LogPanel
from .styles import COLORS, FONTS, SPACING, RADIUS, get_button_style, get_label_style

class ProcessingView(ctk.CTkFrame):
    """
    Compact processing view shown during translation.
    Shows progress, stats, and control buttons.
    """
    
    def __init__(
        self,
        master,
        logger_instance,
        on_pause: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.logger = logger_instance
        self.on_pause = on_pause
        self.on_cancel = on_cancel
        self.is_paused = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup processing view UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Allow log to expand if needed
        
        # Main card
        self.card = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=COLORS["step_active"]
        )
        self.card.grid(row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=SPACING["lg"])
        self.card.grid_columnconfigure(0, weight=1)
        
        # Header with file info
        header = ctk.CTkFrame(self.card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["md"]))
        header.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            header,
            text="🔄 Translating...",
            font=(FONTS["family"], FONTS["heading_size"], "bold"),
            text_color=COLORS["step_active"]
        )
        self.status_label.grid(row=0, column=0, sticky="w")
        
        # File info
        file_frame = ctk.CTkFrame(self.card, fg_color=COLORS["bg_medium"], corner_radius=RADIUS["md"])
        file_frame.grid(row=1, column=0, sticky="ew", padx=SPACING["lg"], pady=SPACING["sm"])
        file_frame.grid_columnconfigure(0, weight=1)
        
        self.file_label = ctk.CTkLabel(
            file_frame,
            text="",
            font=(FONTS["family"], FONTS["subheading_size"], "bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        self.file_label.grid(row=0, column=0, sticky="w", padx=SPACING["md"], pady=(SPACING["sm"], 0))
        
        self.track_label = ctk.CTkLabel(
            file_frame,
            text="",
            font=(FONTS["family"], FONTS["body_size"]),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        self.track_label.grid(row=1, column=0, sticky="w", padx=SPACING["md"], pady=(0, SPACING["sm"]))
        
        # Progress section
        progress_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        progress_frame.grid(row=2, column=0, sticky="ew", padx=SPACING["lg"], pady=SPACING["md"])
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            mode="determinate",
            progress_color=COLORS["step_active"],
            fg_color=COLORS["bg_dark"],
            corner_radius=8,
            height=16
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, SPACING["sm"]))
        self.progress_bar.set(0)
        
        # Progress text
        progress_text_frame = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_text_frame.grid(row=1, column=0, sticky="ew")
        progress_text_frame.grid_columnconfigure(1, weight=1)
        
        self.percent_label = ctk.CTkLabel(
            progress_text_frame,
            text="0%",
            font=(FONTS["family"], FONTS["heading_size"], "bold"),
            text_color=COLORS["text_primary"]
        )
        self.percent_label.grid(row=0, column=0, sticky="w")
        
        self.lines_label = ctk.CTkLabel(
            progress_text_frame,
            text="0 / 0 lines",
            font=(FONTS["family"], FONTS["body_size"]),
            text_color=COLORS["text_secondary"]
        )
        self.lines_label.grid(row=0, column=1, sticky="w", padx=SPACING["md"])
        
        # Token stats
        stats_frame = ctk.CTkFrame(self.card, fg_color=COLORS["bg_medium"], corner_radius=RADIUS["md"])
        stats_frame.grid(row=3, column=0, sticky="ew", padx=SPACING["lg"], pady=SPACING["sm"])
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Create stats and store references
        self.prompt_value_label = self._create_stat(stats_frame, 0, "Prompt", "0")
        self.completion_value_label = self._create_stat(stats_frame, 1, "Completion", "0")
        self.total_value_label = self._create_stat(stats_frame, 2, "Total", "0")
        
        # Control buttons
        buttons_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        buttons_frame.grid(row=4, column=0, sticky="e", padx=SPACING["lg"], pady=SPACING["lg"])
        
        self.pause_btn = ctk.CTkButton(
            buttons_frame,
            text="Pause",
            width=100,
            command=self._on_pause_click,
            **get_button_style("secondary")
        )
        self.pause_btn.pack(side="left", padx=(0, SPACING["md"]))
        
        self.cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            width=100,
            command=self.on_cancel,
            **get_button_style("danger")
        )
        self.cancel_btn.pack(side="left")
        
        # Log Panel
        self.log_panel = LogPanel(self, self.logger)
        self.log_panel.grid(row=1, column=0, sticky="nsew", padx=SPACING["lg"], pady=(0, SPACING["lg"]))
    
    def _create_stat(self, parent, col: int, label: str, value: str):
        """Create a stat display and return the value label."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=col, padx=SPACING["md"], pady=SPACING["md"])
        
        value_lbl = ctk.CTkLabel(
            frame,
            text=value,
            font=(FONTS["family"], FONTS["subheading_size"], "bold"),
            text_color=COLORS["primary_light"]
        )
        value_lbl.pack()
        
        label_lbl = ctk.CTkLabel(
            frame,
            text=label,
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["text_muted"]
        )
        label_lbl.pack()
        
        return value_lbl  # Return reference to value label
    
    def _on_pause_click(self):
        """Handle pause button click."""
        if self.on_pause:
            self.on_pause()
    
    def set_file_info(self, filename: str, track_info: str):
        """Set file and track info."""
        self.file_label.configure(text=f"📄 {filename}")
        self.track_label.configure(text=track_info)
    
    def set_progress(self, percent: float, current: int, total: int):
        """Update progress display."""
        self.progress_bar.set(percent / 100)
        self.percent_label.configure(text=f"{percent:.0f}%")
        self.lines_label.configure(text=f"{current:,} / {total:,} lines")
        # Force UI refresh to ensure progress updates are visible immediately
        self.update_idletasks()
    
    def set_token_stats(self, prompt: int, completion: int, total: int):
        """Update token statistics."""
        self.prompt_value_label.configure(text=f"{prompt:,}")
        self.completion_value_label.configure(text=f"{completion:,}")
        self.total_value_label.configure(text=f"{total:,}")
        # Force UI refresh to ensure token stats are visible immediately
        self.update_idletasks()
    
    def set_paused(self, paused: bool):
        """Set paused state."""
        self.is_paused = paused
        if paused:
            self.status_label.configure(text="⏸️ Paused", text_color=COLORS["warning"])
            self.pause_btn.configure(text="Resume")
            self.progress_bar.configure(progress_color=COLORS["warning"])
            self.card.configure(border_color=COLORS["warning"])
        else:
            self.status_label.configure(text="🔄 Translating...", text_color=COLORS["step_active"])
            self.pause_btn.configure(text="Pause")
            self.progress_bar.configure(progress_color=COLORS["step_active"])
            self.card.configure(border_color=COLORS["step_active"])
    
    def set_completed(self):
        """Set completed state."""
        self.status_label.configure(text="✅ Complete!", text_color=COLORS["success"])
        self.progress_bar.configure(progress_color=COLORS["success"])
        self.card.configure(border_color=COLORS["success"])
        self.pause_btn.pack_forget()
        self.cancel_btn.configure(text="Close", fg_color=COLORS["success"])
    
    def set_error(self, message: str):
        """Set error state."""
        self.status_label.configure(text=f"❌ Error: {message}", text_color=COLORS["error"])
        self.progress_bar.configure(progress_color=COLORS["error"])
        self.card.configure(border_color=COLORS["error"])
        self.pause_btn.pack_forget()

    def set_status(self, message: str, color: Optional[str] = None):
        """Set a custom status message."""
        if not color:
            color = COLORS["step_active"]
        self.status_label.configure(text=message, text_color=color)
        self.update_idletasks()
