"""
Step 2: Configuration View for Sub-auto.
Handles subtitle track selection, language settings, and model configuration.
"""

import customtkinter as ctk
from typing import List, Callable, Optional, Any
from ..styles import (
    COLORS, FONTS, SPACING, RADIUS, 
    get_label_style, get_button_style
)
from ..components import CollapsibleFrame, TrackListItem, SettingsRow

class ConfigurationView(ctk.CTkFrame):
    """View for Step 2: Configuration (Tracks + Options)."""
    
    def __init__(
        self, 
        master, 
        on_model_change: Callable[[str], None],
        on_validate_api: Callable[[], None],
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.grid_columnconfigure(0, weight=1)

        self.header_card = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_medium"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=COLORS["border"]
        )
        self.header_card.pack(fill="x", pady=(0, SPACING["md"]))

        self.header_label = ctk.CTkLabel(
            self.header_card,
            text="Configure translation",
            font=(FONTS["family"], FONTS["heading_size"] + 4, "bold"),
            text_color=COLORS["text_primary"]
        )
        self.header_label.pack(anchor="w", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["xs"]))

        self.header_subtitle = ctk.CTkLabel(
            self.header_card,
            text="Pick the subtitle track, confirm languages, then connect your model.",
            font=(FONTS["family"], FONTS["body_size"]),
            text_color=COLORS["text_secondary"]
        )
        self.header_subtitle.pack(anchor="w", padx=SPACING["lg"], pady=(0, SPACING["lg"]))
        
        # === subtitle tracks section ===
        self.tracks_section = CollapsibleFrame(self, title="Subtitle Tracks")
        self.tracks_section.pack(fill="x", pady=(0, SPACING["md"]))

        self.tracks_hint = ctk.CTkLabel(
            self.tracks_section.header_frame,
            text="Choose one embedded subtitle stream",
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["text_muted"]
        )
        self.tracks_hint.grid(row=0, column=3, sticky="e", padx=(SPACING["sm"], 0))
        
        content = self.tracks_section.content_frame
        
        self.tracks_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.tracks_frame.pack(fill="x")
        self.tracks_frame.grid_columnconfigure(0, weight=1)
        
        self.no_tracks_label = ctk.CTkLabel(
            self.tracks_frame,
            text="Select an MKV file to see subtitle tracks",
            **get_label_style("muted")
        )
        self.no_tracks_label.grid(row=0, column=0, pady=SPACING["lg"])
        
        self.track_items: List[TrackListItem] = []
        
        # === Translation Options Section ===
        self.options_section = CollapsibleFrame(self, title="Translation Settings")
        self.options_section.pack(fill="x", pady=(0, SPACING["md"]))

        self.options_hint = ctk.CTkLabel(
            self.options_section.header_frame,
            text="Review context before starting",
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["text_muted"]
        )
        self.options_hint.grid(row=0, column=3, sticky="e", padx=(SPACING["sm"], 0))
        
        opts_content = self.options_section.content_frame
        opts_content.grid_columnconfigure((0, 1), weight=1)
        
        # Source language
        self.source_lang_row = SettingsRow(
            opts_content,
            label="From",
            input_type="dropdown",
            options=["English", "Japanese", "Korean", "Chinese", "Arabic", "Auto-detect"],
            default_value="English"
        )
        self.source_lang_row.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]), pady=SPACING["xs"])
        
        # Target language
        self.target_lang_row = SettingsRow(
            opts_content,
            label="To",
            input_type="dropdown",
            options=["Indonesian"],
            default_value="Indonesian"
        )
        self.target_lang_row.grid(row=0, column=1, sticky="ew", padx=(SPACING["sm"], 0), pady=SPACING["xs"])
        
        # Model selection row
        self.model_frame = ctk.CTkFrame(
            opts_content,
            fg_color=COLORS["bg_dark"],
            corner_radius=RADIUS["md"],
            border_width=1,
            border_color=COLORS["border"]
        )
        self.model_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SPACING["md"], 0))
        self.model_frame.grid_columnconfigure(2, weight=1)
        
        model_label = ctk.CTkLabel(
            self.model_frame,
            text="Model:",
            **get_label_style("body")
        )
        model_label.grid(row=0, column=0, padx=SPACING["md"], pady=SPACING["md"])
        
        self.model_dropdown = ctk.CTkOptionMenu(
            self.model_frame,
            values=["Not connected"],
            command=on_model_change,
            fg_color=COLORS["bg_light"],
            button_color=COLORS["bg_medium"],
            button_hover_color=COLORS["border"],
            dropdown_fg_color=COLORS["bg_dark"],
            dropdown_hover_color=COLORS["bg_light"],
            corner_radius=RADIUS["md"],
            width=200,
            state="disabled"
        )
        self.model_dropdown.grid(row=0, column=1, padx=SPACING["sm"], pady=SPACING["md"])
        
        # Status indicator
        status_frame = ctk.CTkFrame(self.model_frame, fg_color="transparent")
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
        
        # Connect button
        self.validate_btn = ctk.CTkButton(
            self.model_frame,
            text="Connect",
            width=80,
            command=on_validate_api,
            **get_button_style("secondary")
        )
        self.validate_btn.grid(row=0, column=3, padx=SPACING["md"], pady=SPACING["md"])

    def update_tracks(self, tracks: List[Any], selected_id: Optional[int], on_track_select: Callable[[int, bool], None]):
        """Update the list of subtitle tracks."""
        # Clear existing
        for item in self.track_items:
            item.destroy()
        self.track_items.clear()
        
        if not tracks:
            self.no_tracks_label.grid(row=0, column=0, pady=SPACING["lg"])
            return
            
        self.no_tracks_label.grid_forget()
        
        for i, track in enumerate(tracks):
            item = TrackListItem(
                self.tracks_frame,
                track_id=track.track_id,
                language=track.language,
                track_name=track.track_name,
                codec=track.codec,
                is_default=track.default_track,
                on_select=on_track_select
            )
            item.grid(row=i, column=0, sticky="ew", pady=SPACING["xs"])
            if track.track_id == selected_id:
                item.set_selected(True)
            self.track_items.append(item)

    def set_model_status(self, text: str, color: str = None):
        """Update model status text and color."""
        self.model_status.configure(text=text)
        if color:
            self.model_status.configure(text_color=color)

    def set_model_options(self, options: List[str], current: Optional[str] = None):
        """Update model dropdown values."""
        if options:
            self.model_dropdown.configure(values=options, state="normal")
            if current and current in options:
                self.model_dropdown.set(current)
        else:
            self.model_dropdown.configure(state="disabled")
            self.model_dropdown.set("Not connected")

    def set_cost_estimate(self, text: str):
        """Update cost estimate label."""
        self.cost_estimate_label.configure(text=text)
