"""
StepCard Component for Sub-auto
A card component that represents a step in a wizard-like flow.
"""

import customtkinter as ctk
from typing import Optional, Callable

from .styles import COLORS, FONTS, SPACING, RADIUS, get_label_style


class StepCard(ctk.CTkFrame):
    """
    A card component for wizard-style steps.
    
    States:
    - inactive: Dimmed, non-interactive
    - active: Current step, highlighted
    - completed: Done, shows checkmark
    - error: Has error, shows error indicator
    """
    
    def __init__(
        self,
        master,
        step_number: int,
        title: str,
        state: str = "inactive",  # inactive, active, completed, error
        on_click: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        
        self.step_number = step_number
        self.title = title
        self._state = state
        self.on_click = on_click
        self.content_frame: Optional[ctk.CTkFrame] = None
        
        self._setup_ui()
        self._apply_state()
    
    def _setup_ui(self):
        """Setup the step card UI."""
        self.configure(
            fg_color=COLORS["bg_card"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=COLORS["border"]
        )
        
        self.grid_columnconfigure(0, weight=1)
        
        # Header row
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=SPACING["md"], pady=SPACING["md"])
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        # Step number badge
        self.badge_frame = ctk.CTkFrame(
            self.header_frame,
            width=32,
            height=32,
            corner_radius=16,
            fg_color=COLORS["step_inactive"]
        )
        self.badge_frame.grid(row=0, column=0, padx=(0, SPACING["md"]))
        self.badge_frame.grid_propagate(False)
        
        self.badge_label = ctk.CTkLabel(
            self.badge_frame,
            text=str(self.step_number),
            font=(FONTS["family"], FONTS["body_size"], "bold"),
            text_color=COLORS["text_primary"]
        )
        self.badge_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text=self.title,
            font=(FONTS["family"], FONTS["subheading_size"], "bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        self.title_label.grid(row=0, column=1, sticky="w")
        
        # Status indicator
        self.status_label = ctk.CTkLabel(
            self.header_frame,
            text="",
            font=(FONTS["family"], FONTS["body_size"]),
            text_color=COLORS["text_muted"]
        )
        self.status_label.grid(row=0, column=2, padx=SPACING["sm"])
        
        # Content area (collapsible)
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="ew", padx=SPACING["md"], pady=(0, SPACING["md"]))
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Bind click to header
        self.header_frame.bind("<Button-1>", lambda e: self._on_header_click())
        self.badge_frame.bind("<Button-1>", lambda e: self._on_header_click())
        self.title_label.bind("<Button-1>", lambda e: self._on_header_click())
    
    def _on_header_click(self):
        """Handle header click."""
        if self._state != "inactive" and self.on_click:
            self.on_click()
    
    def _apply_state(self):
        """Apply visual styling based on current state."""
        if self._state == "inactive":
            self.configure(border_color=COLORS["border"])
            self.badge_frame.configure(fg_color=COLORS["step_inactive"])
            self.badge_label.configure(text=str(self.step_number))
            self.title_label.configure(text_color=COLORS["text_muted"])
            self.status_label.configure(text="")
            self.content_frame.grid_remove()
            # Dim all content
            self._set_children_state("disabled")
            
        elif self._state == "active":
            self.configure(border_color=COLORS["step_active"])
            self.badge_frame.configure(fg_color=COLORS["step_active"])
            self.badge_label.configure(text=str(self.step_number))
            self.title_label.configure(text_color=COLORS["text_primary"])
            self.status_label.configure(text="●", text_color=COLORS["step_active"])
            self.content_frame.grid()
            self._set_children_state("normal")
            
        elif self._state == "completed":
            self.configure(border_color=COLORS["step_completed"])
            self.badge_frame.configure(fg_color=COLORS["step_completed"])
            self.badge_label.configure(text="✓")
            self.title_label.configure(text_color=COLORS["text_primary"])
            self.status_label.configure(text="")
            self.content_frame.grid()
            self._set_children_state("normal")
            
        elif self._state == "error":
            self.configure(border_color=COLORS["error"])
            self.badge_frame.configure(fg_color=COLORS["error"])
            self.badge_label.configure(text="!")
            self.title_label.configure(text_color=COLORS["text_primary"])
            self.status_label.configure(text="Error", text_color=COLORS["error"])
            self.content_frame.grid()
            self._set_children_state("normal")
    
    def _set_children_state(self, state: str):
        """Set state of interactive children."""
        for child in self.content_frame.winfo_children():
            try:
                if hasattr(child, 'configure'):
                    child.configure(state=state)
            except:
                pass
    
    def set_state(self, state: str):
        """Set the step state."""
        if state in ("inactive", "active", "completed", "error"):
            self._state = state
            self._apply_state()
    
    def get_state(self) -> str:
        """Get current state."""
        return self._state
    
    def get_content_frame(self) -> ctk.CTkFrame:
        """Get the content frame to add widgets to."""
        return self.content_frame
    
    def set_subtitle(self, text: str):
        """Set optional subtitle/summary text below content."""
        # Create or update subtitle label
        if not hasattr(self, 'subtitle_label'):
            self.subtitle_label = ctk.CTkLabel(
                self.header_frame,
                text=text,
                font=(FONTS["family"], FONTS["small_size"]),
                text_color=COLORS["text_muted"],
                anchor="w"
            )
            self.subtitle_label.grid(row=1, column=1, columnspan=2, sticky="w", pady=(2, 0))
        else:
            self.subtitle_label.configure(text=text)
    
    def clear_subtitle(self):
        """Remove subtitle."""
        if hasattr(self, 'subtitle_label'):
            self.subtitle_label.destroy()
            delattr(self, 'subtitle_label')


class CompactHeader(ctk.CTkFrame):
    """
    Compact header with app title and settings button.
    """
    
    def __init__(
        self,
        master,
        title: str = "Sub-auto",
        version: str = "1.2.0",
        on_settings: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(master, fg_color=COLORS["bg_medium"], corner_radius=0, **kwargs)
        
        self.on_settings = on_settings
        self._setup_ui(title, version)
    
    def _setup_ui(self, title: str, version: str):
        """Setup header UI."""
        self.configure(height=50)
        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)
        
        # App icon and title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=SPACING["lg"], pady=SPACING["sm"])
        
        icon = ctk.CTkLabel(
            title_frame,
            text="🎬",
            font=(FONTS["family"], 18)
        )
        icon.pack(side="left", padx=(0, SPACING["sm"]))
        
        title_label = ctk.CTkLabel(
            title_frame,
            text=f"{title}",
            font=(FONTS["family"], FONTS["heading_size"], "bold"),
            text_color=COLORS["text_primary"]
        )
        title_label.pack(side="left")
        
        version_label = ctk.CTkLabel(
            title_frame,
            text=f"v{version}",
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["text_muted"]
        )
        version_label.pack(side="left", padx=(SPACING["sm"], 0))
        
        # Settings button
        from .styles import get_button_style
        settings_btn = ctk.CTkButton(
            self,
            text="⚙️",
            width=40,
            command=self.on_settings,
            **get_button_style("ghost")
        )
        settings_btn.grid(row=0, column=2, padx=SPACING["lg"])
        
        # API status indicator
        self.api_status = ctk.CTkLabel(
            self,
            text="",
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["text_muted"]
        )
        self.api_status.grid(row=0, column=1, sticky="e", padx=SPACING["md"])
    
    def set_api_status(self, is_valid: bool, model_name: str = ""):
        """Update API status display."""
        if is_valid:
            text = f"✓ {model_name}" if model_name else "✓ API Ready"
            self.api_status.configure(text=text, text_color=COLORS["success"])
        else:
            self.api_status.configure(text="⚠ API Not Configured", text_color=COLORS["warning"])
