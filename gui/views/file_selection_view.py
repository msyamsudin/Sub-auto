"""
Step 1: File Selection View for Sub-auto.
Handles video file selection via drag-and-drop or browsing.
"""

import customtkinter as ctk
from typing import Callable, Optional
from ..styles import COLORS, SPACING, RADIUS, get_label_style
from ..components import FileDropZone

class FileSelectionView(ctk.CTkFrame):
    """View for Step 1: File Selection."""
    
    def __init__(
        self, 
        master, 
        on_file_selected: Callable[[str], None],
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_file_selected = on_file_selected
        
        self.grid_columnconfigure(0, weight=1)
        
        self.hero = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_medium"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=COLORS["border"]
        )
        self.hero.pack(fill="x", pady=(0, SPACING["lg"]))
        self.hero.grid_columnconfigure(0, weight=1)

        self.kicker = ctk.CTkLabel(
            self.hero,
            text="STEP 1",
            font=("Segoe UI", 10, "bold"),
            text_color=COLORS["accent_hover"]
        )
        self.kicker.grid(row=0, column=0, sticky="w", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["xs"]))

        self.header = ctk.CTkLabel(
            self.hero,
            text="Select your source video",
            font=("Segoe UI", 22, "bold"),
            text_color=COLORS["text_primary"]
        )
        self.header.grid(row=1, column=0, sticky="w", padx=SPACING["lg"])

        self.subtitle = ctk.CTkLabel(
            self.hero,
            text="Start with a single MKV file. We'll detect subtitle tracks and guide the next steps automatically.",
            font=("Segoe UI", 12),
            text_color=COLORS["text_secondary"]
        )
        self.subtitle.grid(row=2, column=0, sticky="w", padx=SPACING["lg"], pady=(SPACING["xs"], SPACING["lg"]))
        
        # File Drop Zone
        self.file_drop = FileDropZone(
            self,
            on_file_selected=self.on_file_selected,
            height=220
        )
        self.file_drop.pack(fill="x", pady=(0, SPACING["xl"]))
        
        # Instructions
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.pack(fill="x")

        hints = [
            "Best with softsubs or embedded subtitle tracks",
            "Large files are fine, scanning only reads track metadata first",
            "Supported format: .mkv (Matroska Video)",
        ]

        for hint in hints:
            ctk.CTkLabel(
                self.info_frame,
                text=f"• {hint}",
                **get_label_style("muted")
            ).pack(anchor="w", pady=(0, SPACING["xs"]))

    def set_file_description(self, description: str):
        """Update description if needed (though stepper handles this usually)."""
        pass
