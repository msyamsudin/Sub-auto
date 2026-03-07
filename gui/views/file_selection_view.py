"""
Step 1: File Selection View for Sub-auto.
Handles video file selection via drag-and-drop or browsing.
"""

import customtkinter as ctk
from typing import Callable, Optional
from ..styles import SPACING, get_label_style
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
        
        # Header
        self.header = ctk.CTkLabel(
            self, 
            text="Select Video File", 
            **get_label_style("heading")
        )
        self.header.pack(anchor="w", pady=(0, SPACING["lg"]))
        
        # File Drop Zone
        self.file_drop = FileDropZone(
            self,
            on_file_selected=self.on_file_selected,
            height=200
        )
        self.file_drop.pack(fill="x", pady=(0, SPACING["xl"]))
        
        # Instructions
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.pack(fill="x")
        
        ctk.CTkLabel(
            self.info_frame,
            text="💡 Supported formats: .mkv (Matroska Video)",
            **get_label_style("muted")
        ).pack(anchor="w")

    def set_file_description(self, description: str):
        """Update description if needed (though stepper handles this usually)."""
        pass
