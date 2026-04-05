import customtkinter as ctk
from pathlib import Path
from typing import Optional, Callable, List
from .styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_button_style, get_frame_style, get_label_style
)

class FileDropZone(ctk.CTkFrame):
    """
    A drag-and-drop zone for file selection.
    Note: True drag-and-drop requires tkinterdnd2 which may not be available.
    This implements click-to-browse as the primary method.
    """
    
    def __init__(
        self,
        master,
        file_types: List[tuple] = [("MKV files", "*.mkv")],
        on_file_selected: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(master, **get_frame_style("card"), **kwargs)
        
        self.file_types = file_types
        self.on_file_selected = on_file_selected
        self.selected_file: Optional[str] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the drop zone UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._setup_empty_ui()
        
    def _setup_empty_ui(self):
        """Setup the empty state UI (Large drop zone)."""
        # Clear existing
        for widget in self.winfo_children():
            widget.destroy()
            
        # Inner container with dashed border effect
        self.inner_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_dark"],
            corner_radius=RADIUS["lg"]
        )
        self.inner_frame.grid(
            row=0, column=0,
            sticky="nsew",
            padx=SPACING["md"],
            pady=SPACING["md"]
        )
        self.inner_frame.grid_columnconfigure(0, weight=1)
        self.inner_frame.grid_rowconfigure(0, weight=1)
        self.inner_frame.configure(border_width=1, border_color=COLORS["border_light"])

        self.hero_badge = ctk.CTkLabel(
            self.inner_frame,
            text="Quick Start",
            font=(FONTS["family"], FONTS["small_size"], "bold"),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent_bg"],
            corner_radius=RADIUS["xl"],
            padx=SPACING["sm"],
            pady=2
        )
        self.hero_badge.grid(row=0, column=0, sticky="nw", padx=SPACING["lg"], pady=SPACING["lg"])
        
        # Content container
        self.content = ctk.CTkFrame(self.inner_frame, fg_color="transparent")
        self.content.grid(row=0, column=0, pady=SPACING["xl"])
        
        # Icon/emoji
        self.icon_label = ctk.CTkLabel(
            self.content,
            text="📁",
            font=(FONTS["family"], 36),
            text_color=COLORS["accent_hover"]
        )
        self.icon_label.pack(pady=(0, SPACING["xs"]))
        
        # Main text
        self.main_label = ctk.CTkLabel(
            self.content,
            text="Drop your MKV file to begin",
            font=(FONTS["family"], FONTS["heading_size"] + 2, "bold"),
            text_color=COLORS["text_primary"]
        )
        self.main_label.pack()

        # Sub text
        self.sub_label = ctk.CTkLabel(
            self.content,
            text="Click anywhere here or drag and drop a video file",
            **get_label_style("muted")
        )
        self.sub_label.pack(pady=(SPACING["xs"], 0))

        self.helper_label = ctk.CTkLabel(
            self.content,
            text="Sub-auto will scan subtitle tracks and prepare translation settings for you.",
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["text_secondary"]
        )
        self.helper_label.pack(pady=(SPACING["sm"], 0))
        
        # Make clickable
        self._bind_click_recursive(self)

    def _setup_compact_ui(self, path: Path):
        """Setup the compact state UI (Selected file row)."""
        # Clear existing
        for widget in self.winfo_children():
            widget.destroy()
            
        # Container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=0, column=0, sticky="ew", padx=SPACING["md"], pady=SPACING["sm"])
        container.grid_columnconfigure(1, weight=1)
        
        # Thumbnail placeholder / Icon
        icon_frame = ctk.CTkFrame(
            container, 
            width=44, height=44, 
            fg_color=COLORS["accent_bg"],
            corner_radius=RADIUS["md"]
        )
        icon_frame.grid(row=0, column=0, sticky="w", padx=(0, SPACING["md"]))
        icon_frame.grid_propagate(False)
        
        icon = ctk.CTkLabel(
            icon_frame,
            text="🎬",
            font=(FONTS["family"], 20),
        )
        icon.place(relx=0.5, rely=0.5, anchor="center")
        
        # File Info
        info_frame = ctk.CTkFrame(container, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="ew")
        
        name_lbl = ctk.CTkLabel(
            info_frame,
            text=path.name,
            font=(FONTS["family"], FONTS["body_size"], "bold"),
            text_color=COLORS["text_primary"]
        )
        name_lbl.pack(anchor="w")
        
        size_bytes = path.stat().st_size
        size_str = self._format_size(size_bytes)
        size_lbl = ctk.CTkLabel(
            info_frame,
            text=f"{size_str} • {path.parent}",
            **get_label_style("muted")
        )
        size_lbl.pack(anchor="w")
        
        # Change Button
        change_btn = ctk.CTkButton(
            container,
            text="Change",
            width=60,
            height=24,
            command=self._on_click,
            **get_button_style("secondary")
        )
        change_btn.grid(row=0, column=2, padx=(SPACING["md"], 0))

    def _bind_click_recursive(self, widget):
        if isinstance(widget, (ctk.CTkLabel, ctk.CTkFrame)):
             widget.bind("<Button-1>", lambda e: self._on_click())
             widget.configure(cursor="hand2")
             
        for child in widget.winfo_children():
            self._bind_click_recursive(child)
    
    def _bind_click(self, widget):
        """Bind click event to a widget."""
        widget.bind("<Button-1>", lambda e: self._on_click())
        widget.configure(cursor="hand2")
    
    def _on_click(self):
        """Handle click event - open file dialog."""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select MKV File",
            filetypes=self.file_types
        )
        
        if file_path:
            self.set_file(file_path)
    
    def set_file(self, file_path: str):
        """Set the selected file and update UI."""
        self.selected_file = file_path
        path = Path(file_path)
        
        # Switch to compact UI
        self._setup_compact_ui(path)
        
        # Callback
        if self.on_file_selected:
            self.on_file_selected(file_path)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size to human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def reset(self):
        """Reset the drop zone to initial state."""
        self.selected_file = None
        self._setup_empty_ui()
