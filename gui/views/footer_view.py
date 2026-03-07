"""
Footer actions component for Sub-auto.
Contains buttons for Start, Reset, Resume, and Status display.
"""

import customtkinter as ctk
from typing import Callable, Optional
from ..styles import (
    COLORS, FONTS, SPACING, 
    get_button_style, get_label_style
)

class FooterView(ctk.CTkFrame):
    """Footer view with action buttons."""
    
    def __init__(
        self, 
        master, 
        on_start: Callable[[], None],
        on_reset: Callable[[], None],
        on_resume: Callable[[], None],
        on_show_summary: Callable[[], None],
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", height=60, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        
        # Separator
        self.separator = ctk.CTkFrame(self, height=2, fg_color=COLORS["border"])
        self.separator.pack(fill="x", pady=(0, SPACING["sm"]))
        
        # Content frame
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="x", expand=True)
        self.content.grid_columnconfigure(0, weight=1)
        
        # Left side - status
        self.status_label = ctk.CTkLabel(
            self.content,
            text="",
            **get_label_style("muted")
        )
        self.status_label.grid(row=0, column=0, sticky="w")
        
        # Right side - buttons
        self.buttons_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.buttons_frame.grid(row=0, column=1, sticky="e")
        
        self.reset_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Reset",
            width=80,
            command=on_reset,
            **get_button_style("secondary")
        )
        self.reset_btn.pack(side="left", padx=(0, SPACING["lg"]))
        
        self.summary_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Show Summary",
            width=120,
            command=on_show_summary,
            **get_button_style("secondary")
        )
        self.summary_btn.pack(side="left", padx=(0, SPACING["lg"]))
        self.summary_btn.pack_forget()

        self.start_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Start Translation",
            width=150,
            font=(FONTS["family"], FONTS["subheading_size"], "bold"),
            command=on_start,
            **get_button_style("info")
        )
        self.start_btn.pack(side="left")
        
        self.resume_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Resume",
            width=120,
            command=on_resume,
            **get_button_style("success")
        )
        # resume_btn is initially hidden
        
    def set_status(self, text: str, color: Optional[str] = None):
        """Update status label."""
        self.status_label.configure(text=text)
        if color:
            self.status_label.configure(text_color=color)

    def set_start_state(self, enabled: bool, text: str = "Start Translation"):
        """Update start button state."""
        self.start_btn.configure(
            state="normal" if enabled else "disabled",
            text=text
        )

    def show_resume(self, show: bool):
        """Toggle resume button visibility."""
        if show:
            self.resume_btn.pack(side="left", padx=(0, SPACING["lg"]))
            self.start_btn.pack_forget()
        else:
            self.resume_btn.pack_forget()
            self.start_btn.pack(side="left")

    def show_summary(self, show: bool):
        """Toggle summary button visibility."""
        if show:
            self.summary_btn.pack(side="left", padx=(0, SPACING["lg"]), before=self.start_btn)
        else:
            self.summary_btn.pack_forget()
