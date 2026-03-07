"""
Review View for Sub-auto
Handles Step 4 (Review) of the translation wizard.
"""

import customtkinter as ctk
from typing import Callable, Optional, Dict, Any

from ..styles import COLORS, SPACING, get_label_style, get_button_style
from ..components import SubtitleReviewPanel, SubtitleEditor

class ReviewView(ctk.CTkFrame):
    """View for reviewing and approving translated subtitles."""
    
    def __init__(
        self, 
        master: any, 
        on_approve: Callable[[str], None],
        on_discard: Callable[[], None]
    ):
        super().__init__(master, fg_color="transparent")
        self.on_approve = on_approve
        self.on_discard = on_discard
        self.use_new_review = True
        self.payload: Optional[Dict[str, Any]] = None
        self.editor_view: Optional[any] = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._setup_ui()

    def _setup_ui(self):
        """Setup the view layout."""
        # Header with Title and Toggle
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, SPACING["sm"]))
        
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Review Subtitles", 
            **get_label_style("heading")
        )
        self.title_label.pack(side="left")
        
        self.toggle_btn = ctk.CTkButton(
            self.header_frame, 
            text="Switch to Classic",
            command=self._toggle_editor,
            width=120,
            height=24,
            **get_button_style("ghost")
        )
        self.toggle_btn.pack(side="right")
        
        # Container for the actual editor
        self.editor_container = ctk.CTkFrame(self, fg_color="transparent")
        self.editor_container.grid(row=1, column=0, sticky="nsew")

    def show_payload(self, payload: Dict[str, Any]):
        """Load and display a translation payload for review."""
        self.payload = payload
        self._refresh_editor()

    def _toggle_editor(self):
        """Switch between Modern and Classic editor."""
        self.use_new_review = not self.use_new_review
        self.toggle_btn.configure(
            text=f"Switch to {'Classic' if self.use_new_review else 'Modern'}"
        )
        self._refresh_editor()

    def _refresh_editor(self):
        """Re-create the editor widget based on current mode."""
        if not self.payload:
            return
            
        # Clean up existing
        if self.editor_view:
            self.editor_view.destroy()
            
        subtitle_path = self.payload["translated_sub_path"]
        
        if self.use_new_review:
            self.editor_view = SubtitleReviewPanel(
                self.editor_container,
                subtitle_path=subtitle_path,
                on_approve=self.on_approve,
                on_discard=self.on_discard
            )
        else:
            self.editor_view = SubtitleEditor(
                self.editor_container,
                subtitle_path=subtitle_path,
                on_approve=self.on_approve,
                on_discard=self.on_discard
            )
            
        self.editor_view.pack(fill="both", expand=True)
