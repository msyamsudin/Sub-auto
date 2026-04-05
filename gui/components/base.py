import customtkinter as ctk
from typing import Optional, Callable, List
from .styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_button_style, get_input_style, get_frame_style, get_label_style
)

class TrackListItem(ctk.CTkFrame):
    """A single subtitle track item with checkbox."""
    
    def __init__(
        self,
        master,
        track_id: int,
        track_name: str,
        language: str,
        codec: str,
        is_default: bool = False,
        on_select: Optional[Callable[[int, bool], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color=COLORS["bg_dark"], corner_radius=RADIUS["md"], **kwargs)
        
        self.track_id = track_id
        self.on_select = on_select
        self.is_selected = ctk.BooleanVar(value=False)
        
        self._setup_ui(track_name, language, codec, is_default)
    
    def _setup_ui(self, track_name: str, language: str, codec: str, is_default: bool):
        """Setup the track item UI."""
        self.grid_columnconfigure(1, weight=1)
        
        # Checkbox
        self.checkbox = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.is_selected,
            command=self._on_checkbox_change,
            width=24,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["text_muted"] # Improved border contrast
        )
        self.checkbox.grid(row=0, column=0, padx=SPACING["sm"], pady=SPACING["sm"])
        
        # Track info container
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="w", pady=SPACING["sm"])
        
        # Track ID and name
        title_text = f"Track {self.track_id}"
        if track_name:
            title_text += f" - {track_name}"
        
        self.title_label = ctk.CTkLabel(
            info_frame,
            text=title_text,
            **get_label_style("body")
        )
        self.title_label.pack(anchor="w")
        
        # Language and codec
        meta_text = f"{language.upper()} • {codec}"
        if is_default:
            meta_text += " • Default"
        
        self.meta_label = ctk.CTkLabel(
            info_frame,
            text=meta_text,
            **get_label_style("muted")
        )
        self.meta_label.pack(anchor="w")
    
    def _on_checkbox_change(self):
        """Handle checkbox state change."""
        if self.on_select:
            self.on_select(self.track_id, self.is_selected.get())
    
    def select(self):
        """Select this track."""
        self.is_selected.set(True)
        self._on_checkbox_change()
    
    def deselect(self):
        """Deselect this track."""
        self.is_selected.set(False)
        self._on_checkbox_change()


class StatusBadge(ctk.CTkFrame):
    """A small status badge/pill."""
    
    def __init__(
        self,
        master,
        text: str,
        variant: str = "info",  # "info", "success", "warning", "error"
        **kwargs
    ):
        color_map = {
            "info": (COLORS["info"], COLORS["bg_dark"]),
            "success": (COLORS["success"], COLORS["success_bg"]),
            "warning": (COLORS["warning"], COLORS["warning_bg"]),
            "error": (COLORS["error"], COLORS["error_bg"]),
        }
        
        text_color, bg_color = color_map.get(variant, color_map["info"])
        
        super().__init__(
            master,
            fg_color=bg_color,
            corner_radius=RADIUS["sm"],
            **kwargs
        )
        
        self.label = ctk.CTkLabel(
            self,
            text=text,
            text_color=text_color,
            font=(FONTS["family"], FONTS["small_size"], "bold"),
            padx=SPACING["sm"],
            pady=2
        )
        self.label.pack()
    
    def set_text(self, text: str):
        """Update badge text."""
        self.label.configure(text=text)
    
    def set_variant(self, variant: str):
        """Update badge variant."""
        color_map = {
            "info": (COLORS["info"], COLORS["bg_dark"]),
            "success": (COLORS["success"], COLORS["success_bg"]),
            "warning": (COLORS["warning"], COLORS["warning_bg"]),
            "error": (COLORS["error"], COLORS["error_bg"]),
        }
        text_color, bg_color = color_map.get(variant, color_map["info"])
        self.configure(fg_color=bg_color)
        self.label.configure(text_color=text_color)


class SettingsRow(ctk.CTkFrame):
    """A single settings row with label and input."""
    
    def __init__(
        self,
        master,
        label: str,
        input_type: str = "entry",  # "entry", "dropdown", "browse"
        default_value: str = "",
        options: List[str] = None,
        placeholder: str = "",
        browse_title: str = "Select",
        browse_type: str = "directory",  # "directory" or "file"
        on_change: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.on_change = on_change
        self.input_type = input_type
        self.browse_title = browse_title
        self.browse_type = browse_type
        
        self._setup_ui(label, input_type, default_value, options, placeholder)
    
    def _setup_ui(
        self,
        label: str,
        input_type: str,
        default_value: str,
        options: List[str],
        placeholder: str
    ):
        """Setup the settings row UI."""
        self.grid_columnconfigure(1, weight=1)
        
        # Label
        self.label = ctk.CTkLabel(
            self,
            text=label,
            width=150,
            anchor="w",
            **get_label_style("body")
        )
        self.label.grid(row=0, column=0, sticky="w", padx=(0, SPACING["md"]))
        
        # Input based on type
        if input_type == "entry":
            self.input = ctk.CTkEntry(
                self,
                placeholder_text=placeholder,
                **get_input_style()
            )
            self.input.grid(row=0, column=1, sticky="ew")
            if default_value:
                self.input.insert(0, default_value)
            self.input.bind("<FocusOut>", lambda e: self._on_value_change())
            
        elif input_type == "dropdown":
            self.input = ctk.CTkOptionMenu(
                self,
                values=options or [],
                command=lambda v: self._on_value_change(),
                fg_color=COLORS["bg_dark"],
                button_color=COLORS["bg_light"],
                button_hover_color=COLORS["border"],
                dropdown_fg_color=COLORS["bg_dark"],
                dropdown_hover_color=COLORS["bg_light"],
                corner_radius=RADIUS["md"]
            )
            self.input.grid(row=0, column=1, sticky="ew")
            if default_value and default_value in (options or []):
                self.input.set(default_value)
                
        elif input_type == "browse":
            # Container for entry + button
            from tkinter import filedialog
            browse_frame = ctk.CTkFrame(self, fg_color="transparent")
            browse_frame.grid(row=0, column=1, sticky="ew")
            browse_frame.grid_columnconfigure(0, weight=1)
            
            self.input = ctk.CTkEntry(
                browse_frame,
                placeholder_text=placeholder,
                **get_input_style()
            )
            self.input.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))
            if default_value:
                self.input.insert(0, default_value)
            
            self.browse_btn = ctk.CTkButton(
                browse_frame,
                text="Browse",
                width=80,
                command=self._on_browse,
                **get_button_style("secondary")
            )
            self.browse_btn.grid(row=0, column=1)
    
    def _on_browse(self):
        """Handle browse button click."""
        from tkinter import filedialog
        if self.browse_type == "directory":
            path = filedialog.askdirectory(title=self.browse_title)
        else:
            path = filedialog.askopenfilename(title=self.browse_title)
        
        if path:
            self.set_value(path)
            self._on_value_change()
    
    def _on_value_change(self):
        """Handle value change."""
        if self.on_change:
            self.on_change(self.get_value())
    
    def get_value(self) -> str:
        """Get the current value."""
        if self.input_type == "dropdown":
            return self.input.get()
        else:
            return self.input.get()
    
    def set_value(self, value: str):
        """Set the value."""
        if self.input_type == "dropdown":
            self.input.set(value)
        else:
            self.input.delete(0, "end")
            self.input.insert(0, value)
