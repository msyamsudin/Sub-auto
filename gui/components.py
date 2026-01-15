"""
Reusable GUI Components for Sub-auto
Custom widgets and UI elements.
"""

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from typing import Optional, Callable, List
import os
import time
import ctypes

from .styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_button_style, get_input_style, get_frame_style, get_label_style
)


class CustomTitleBar(ctk.CTkFrame):
    """
    Custom title bar to replace Windows default.
    Provides window controls (minimize, maximize, close) and drag functionality.
    """
    
    def __init__(
        self,
        master,
        title: str = "Sub-auto",
        version: str = "",
        on_settings: Optional[Callable] = None,
        show_settings: bool = True,
        is_dialog: bool = False,
        draggable: bool = True,
        show_minimize: bool = True,
        show_close: bool = True,
        **kwargs
    ):
        super().__init__(master, fg_color=COLORS["bg_medium"], corner_radius=0, **kwargs)
        
        self.master = master
        self.title_text = title
        self.version = version
        self.on_settings = on_settings
        self.show_settings = show_settings
        self.is_dialog = is_dialog
        self.draggable = draggable
        self.show_minimize = show_minimize
        self.show_close = show_close
        
        # Drag state
        self._drag_x = 0
        self._drag_y = 0
        self._is_maximized = False
        self._normal_geometry = None
        
        self._setup_ui()
        if self.draggable:
            self._bind_drag_events()
    
    def _setup_ui(self):
        """Setup title bar UI."""
        # Use smaller height for dialogs
        bar_height = 22 if self.is_dialog else 30
        btn_height = 20 if self.is_dialog else 30
        btn_width = 30 if self.is_dialog else 40
        
        title_font_size = 9 if self.is_dialog else FONTS["body_size"] - 2
        
        self.configure(height=bar_height)
        self.pack_propagate(False)
        self.grid_columnconfigure(1, weight=1)
        
        # Left side - App icon and title
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="w", padx=SPACING["md"], pady=SPACING["sm"])
        
        # Title
        self.title_label = ctk.CTkLabel(
            left_frame,
            text=f"{self.title_text} {self.version}".strip(),
            font=(FONTS["family"], FONTS["heading_size"], "bold"),
            text_color=COLORS["text_primary"]
        )
        self.title_label.pack(side="left")
        
        # Center spacer (draggable area)
        self.drag_area = ctk.CTkFrame(self, fg_color="transparent")
        self.drag_area.grid(row=0, column=1, sticky="ew")
        
        # API Status indicator (for main window only)
        if not self.is_dialog:
            self.api_status = ctk.CTkLabel(
                self.drag_area,
                text="",
                font=(FONTS["family"], FONTS["small_size"]),
                text_color=COLORS["text_muted"]
            )
            self.api_status.pack(side="right", padx=SPACING["md"])
        
        # Right side - Window controls
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.grid(row=0, column=2, sticky="e")
        
        # Settings button (optional)
        if self.show_settings and self.on_settings:
            self.settings_btn = ctk.CTkButton(
                controls_frame,
                text="☰",
                width=btn_width,
                height=btn_height,
                corner_radius=0,
                fg_color="transparent",
                hover_color=COLORS["bg_light"],
                text_color=COLORS["text_secondary"],
                command=self.on_settings
            )
            self.settings_btn.pack(side="left")
        
        # Minimize button
        if self.show_minimize:
            self.min_btn = ctk.CTkButton(
                controls_frame,
                text="—",
                width=btn_width,
                height=btn_height,
                corner_radius=0,
                fg_color="transparent",
                hover_color=COLORS["bg_light"],
                text_color=COLORS["text_secondary"],
                command=self._minimize_window
            )
            self.min_btn.pack(side="left")
        
        # Maximize button (not shown for dialogs)
        if not self.is_dialog and not self.is_dialog: # Redundant check kept for minimal diff, but logic is fine
            self.max_btn = ctk.CTkButton(
                controls_frame,
                text="□",
                width=btn_width,
                height=btn_height,
                corner_radius=0,
                fg_color="transparent",
                hover_color=COLORS["bg_light"],
                text_color=COLORS["text_secondary"],
                command=self._toggle_maximize
            )
            self.max_btn.pack(side="left")
        
        # Close button
        if self.show_close:
            self.close_btn = ctk.CTkButton(
                controls_frame,
                text="✕",
                width=btn_width,
                height=btn_height,
                corner_radius=0,
                fg_color="transparent",
                hover_color=COLORS["error"],
                text_color=COLORS["text_secondary"],
                command=self._close_window
            )
            self.close_btn.pack(side="left")
        
        # Bind drag to icon, title, and labels
        for widget in left_frame.winfo_children():
            self._bind_widget_drag(widget)
    
    def _bind_drag_events(self):
        """Bind drag events to title bar."""
        self.bind("<Button-1>", self._on_drag_start)
        self.bind("<B1-Motion>", self._on_drag_motion)
        self.bind("<Double-Button-1>", self._on_double_click)
        
        self.drag_area.bind("<Button-1>", self._on_drag_start)
        self.drag_area.bind("<B1-Motion>", self._on_drag_motion)
        self.drag_area.bind("<Double-Button-1>", self._on_double_click)
    
    def _bind_widget_drag(self, widget):
        """Bind drag events to a widget."""
        widget.bind("<Button-1>", self._on_drag_start)
        widget.bind("<B1-Motion>", self._on_drag_motion)
        widget.bind("<Double-Button-1>", self._on_double_click)
    
    def _on_drag_start(self, event):
        """Handle drag start."""
        self._drag_x = event.x_root - self.master.winfo_x()
        self._drag_y = event.y_root - self.master.winfo_y()
    
    def _on_drag_motion(self, event):
        """Handle drag motion."""
        # If maximized, restore before moving
        if self._is_maximized:
            self._restore_window()
            # Adjust drag offset for restored window
            self._drag_x = self.master.winfo_width() // 2
            self._drag_y = 18
        
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.master.geometry(f"+{x}+{y}")
    
    def _on_double_click(self, event):
        """Handle double click to toggle maximize."""
        if not self.is_dialog:
            self._toggle_maximize()
    
    def _minimize_window(self):
        """Minimize window."""
        try:
            # Minimize using Windows API to avoid TclError with overrideredirect
            hwnd = ctypes.windll.user32.GetParent(self.master.winfo_id())
            ctypes.windll.user32.ShowWindow(hwnd, 6) # SW_MINIMIZE
        except Exception:
            try:
                self.master.iconify()
            except Exception:
                pass
    
    def _toggle_maximize(self):
        """Toggle between maximized and normal state."""
        if self._is_maximized:
            self._restore_window()
        else:
            self._maximize_window()
    
    def _maximize_window(self):
        """Maximize window."""
        if not self._is_maximized:
            # Store current geometry
            self._normal_geometry = self.master.geometry()
            
            # Get screen size
            screen_width = self.master.winfo_screenwidth()
            screen_height = self.master.winfo_screenheight()
            
            # Account for taskbar (approximately 40px)
            self.master.geometry(f"{screen_width}x{screen_height - 40}+0+0")
            self._is_maximized = True
            
            if hasattr(self, 'max_btn'):
                self.max_btn.configure(text="❐")
    
    def _restore_window(self):
        """Restore window to normal size."""
        if self._is_maximized and self._normal_geometry:
            self.master.geometry(self._normal_geometry)
            self._is_maximized = False
            
            if hasattr(self, 'max_btn'):
                self.max_btn.configure(text="□")
    
    def _close_window(self):
        """Close window."""
        # Check if master has custom close handler
        if hasattr(self.master, '_on_close'):
            self.master._on_close()
        else:
            self.master.destroy()
    
    def set_api_status(self, is_valid: bool, model_name: str = "", connecting: bool = False):
        """Update API status display."""
        if not hasattr(self, 'api_status'):
            return
            
        if connecting:
            self.api_status.configure(text="⟳ Fetching models...", text_color=COLORS["text_secondary"])
        elif is_valid:
            text = f"✓ {model_name}" if model_name else "✓ API Ready"
            self.api_status.configure(text=text, text_color=COLORS["success"])
        else:
            self.api_status.configure(text="⚠ API Not Configured", text_color=COLORS["warning"])
            
    def get_center_frame(self):
        """Get the center frame for adding widgets."""
        return self.drag_area


class CollapsibleFrame(ctk.CTkFrame):
    """
    A frame that can be collapsed/expanded with a header click.
    """
    def __init__(self, master, title, expanded=True, **kwargs):
        super().__init__(master, **get_frame_style("card"), **kwargs)
        self.expanded = expanded
        self.title = title
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # Content row

        # Header Frame
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=SPACING["md"], pady=(SPACING["sm"], 0))
        self.header_frame.columnconfigure(2, weight=1) # Spacer

        # Toggle Button (Arrow)
        self.toggle_btn = ctk.CTkButton(
            self.header_frame,
            text="▼" if expanded else "▶",
            width=24,
            height=24,
            fg_color="transparent",
            hover_color=COLORS["bg_medium"],
            text_color=COLORS["text_secondary"],
            command=self.toggle,
            font=(FONTS["family"], 16)
        )
        self.toggle_btn.grid(row=0, column=0, sticky="w")
        
        # Title Label
        self.title_lbl = ctk.CTkLabel(
            self.header_frame, 
            text=title,
            **get_label_style("subheading")
        )
        self.title_lbl.grid(row=0, column=1, sticky="w", padx=SPACING["sm"])

        # Content Frame
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        if expanded:
            self.content_frame.grid(row=1, column=0, sticky="nsew", padx=SPACING["md"], pady=SPACING["md"])
            
        # Bind click on header to toggle
        self.title_lbl.bind("<Button-1>", lambda e: self.toggle())
        self.header_frame.bind("<Button-1>", lambda e: self.toggle())

    def toggle(self):
        if self.expanded:
            self.content_frame.grid_forget()
            self.toggle_btn.configure(text="▶")
            self.expanded = False
        else:
            self.content_frame.grid(row=1, column=0, sticky="nsew", padx=SPACING["md"], pady=SPACING["md"])
            self.toggle_btn.configure(text="▼")
            self.expanded = True
            
    def add_widget_to_header(self, widget, **grid_kwargs):
        """Add a widget (like a badge) to the header (right side)."""
        widget.grid(row=0, column=3+len(self.header_frame.grid_slaves(row=0)), **grid_kwargs)
        widget.lift()


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
        
        # Content container
        self.content = ctk.CTkFrame(self.inner_frame, fg_color="transparent")
        self.content.grid(row=0, column=0, pady=SPACING["lg"]) # Reduced padding
        
        # Icon/emoji
        self.icon_label = ctk.CTkLabel(
            self.content,
            text="📁",
            font=(FONTS["family"], 32), # Smaller icon
            text_color=COLORS["text_muted"]
        )
        self.icon_label.pack(pady=(0, SPACING["xs"]))
        
        # Main text
        self.main_label = ctk.CTkLabel(
            self.content,
            text="Click to select MKV file",
            **get_label_style("body") # Smaller font
        )
        self.main_label.pack()
        
        # Sub text
        self.sub_label = ctk.CTkLabel(
            self.content,
            text="or drag & drop",
            **get_label_style("muted")
        )
        self.sub_label.pack(pady=(SPACING["xs"], 0))
        
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
            width=40, height=40, 
            fg_color=COLORS["bg_dark"],
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
            **get_label_style("body")
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
    
    def deselect(self):
        """Deselect this track."""
        self.is_selected.set(False)


class SegmentedProgressBar(ctk.CTkFrame):
    """
    A segmented progress bar using Canvas for performance.
    Features:
    - Zero-lag resizing (Canvas based)
    - Dynamic segment count
    - Pulse animation on leading edge
    """
    def __init__(
        self,
        master,
        segment_width: int = 10,
        height: int = 16,
        spacing: int = 3,
        active_color: str = COLORS["error"],
        inactive_color: str = COLORS["bg_dark"],
        pulse_color: str = "#FF8A80", # Lighter red for pulse
        corner_radius: int = 2,
        **kwargs
    ):
        super().__init__(master, height=height, fg_color="transparent", **kwargs)
        
        self.height = height
        self.segment_width = segment_width
        self.spacing = spacing
        self.active_color = active_color
        self.inactive_color = inactive_color
        self.pulse_color = pulse_color
        self.corner_radius = corner_radius
        
        # State
        self.progress = 0.0
        self._current_width = 1
        self._segments_count = 0
        self._active_count = 0
        self._pulse_direction = 1 # 1 for fade in, -1 for fade out
        self._pulse_alpha = 0.0   # 0.0 to 1.0 interpolation factor
        self._anim_running = False
        
        # Canvas Setup
        # Resolve transparent to actual color (Canvas doesn't support 'transparent')
        bg_color = self._apply_appearance_mode(self._fg_color)
        if bg_color == "transparent":
            bg_color = self._apply_appearance_mode(COLORS["bg_medium"])
            
        self.canvas = ctk.CTkCanvas(
            self,
            height=height,
            bg=bg_color,
            highlightthickness=0,
            borderwidth=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        # Bind events
        self.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Configure>", self._on_resize)

    def _apply_appearance_mode(self, color):
        """Handle ctk color tuples/single values."""
        if isinstance(color, (tuple, list)):
            return color[1] if ctk.get_appearance_mode() == "Dark" else color[0]
        return color

    def _on_resize(self, event):
        """Handle resize."""
        if event.width <= 1 or event.width == self._current_width:
            return
            
        self._current_width = event.width
        self._draw()

    def _draw(self, no_color_updates=False, **kwargs):
        """Draw segments."""
        if self._current_width <= 0:
            return
            
        # If called by parent init, canvas might not be ready or we want to skip
        if not hasattr(self, 'canvas'):
            return

        self.canvas.delete("all")
        
        # Calculate count
        total_unit = self.segment_width + self.spacing
        self._segments_count = max(1, int((self._current_width + self.spacing) // total_unit))
        
        # Draw all inactive first
        for i in range(self._segments_count):
            x = i * total_unit
            self._draw_round_rect(
                x, 0, x + self.segment_width, self.height, 
                radius=self.corner_radius, 
                fill=self.inactive_color,
                tag=f"seg_{i}"
            )
            
        # Redraw active state
        self._update_colors()

    def _draw_round_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Draw a rounded rectangle using polygon."""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1, x2, y1 + radius,
            x2, y2 - radius,
            x2, y2, x2 - radius, y2,
            x1 + radius, y2,
            x1, y2, x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def set(self, value: float):
        """Set progress (0.0 - 1.0)."""
        self.progress = max(0.0, min(1.0, value))
        self._update_colors()
        
        # Start/Stop pulse
        if self.progress > 0 and self.progress < 1:
            if not self._anim_running:
                self._anim_running = True
                self._animate_pulse()
        else:
            self._anim_running = False # Stop on 0 or complete

    def _update_colors(self):
        """Update segment colors."""
        target_active = int(self.progress * self._segments_count)
        
        # Optimization: only update changed segments? 
        # For now, simplistic approach is fine for 50 items.
        
        for i in range(self._segments_count):
            tag = f"seg_{i}"
            color = self.active_color if i < target_active else self.inactive_color
            self.canvas.itemconfig(tag, fill=color)
            
        self._active_count = target_active

    def _animate_pulse(self):
        """Pulse the last active segment."""
        if not self._anim_running or self._active_count <= 0:
            return

        # Target segment: the last one that is active (leading edge)
        # Index is active_count - 1
        target_idx = self._active_count - 1
        tag = f"seg_{target_idx}"
        
        # Logic: Interpolate between active_color and pulse_color
        # We'll just toggle for simplicity first, or better, oscillate
         
        # Oscillate alpha
        self._pulse_alpha += 0.1 * self._pulse_direction
        if self._pulse_alpha >= 1.0:
            self._pulse_alpha = 1.0
            self._pulse_direction = -1
        elif self._pulse_alpha <= 0.0:
            self._pulse_alpha = 0.0
            self._pulse_direction = 1
            
        # Interpolate Color
        current_color = self._interpolate_color(self.active_color, self.pulse_color, self._pulse_alpha)
        self.canvas.itemconfig(tag, fill=current_color)
        
        # Schedule next frame (30ms ~ 33fps)
        self.after(30, self._animate_pulse)

    def _interpolate_color(self, c1, c2, t):
        """Interpolate between two hex colors."""
        # Clean hex
        c1 = c1.lstrip('#')
        c2 = c2.lstrip('#')
        
        # RGB
        r1, g1, b1 = tuple(int(c1[i:i+2], 16) for i in (0, 2, 4))
        r2, g2, b2 = tuple(int(c2[i:i+2], 16) for i in (0, 2, 4))
        
        # Lerp
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        
        return f"#{r:02x}{g:02x}{b:02x}"
        
    def configure(self, **kwargs):
        if "progress_color" in kwargs:
            self.active_color = kwargs.pop("progress_color")
            self._update_colors()
        if "fg_color" in kwargs:
            self.inactive_color = kwargs.pop("fg_color")
            # Update canvas background too if transparent logic needed?
            # For now just update rectangles
            self._update_colors()
        super().configure(**kwargs)



class ProgressPanel(ctk.CTkFrame):
    """Progress panel with progress bar and status text."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **get_frame_style("card"), **kwargs)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the progress panel UI."""
        self.grid_columnconfigure(0, weight=1)
        
        # Status text
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready",
            **get_label_style("body")
        )
        self.status_label.grid(
            row=0, column=0,
            sticky="w",
            padx=SPACING["md"],
            pady=(SPACING["md"], SPACING["xs"])
        )
        
        # Progress bar
        self.progress_bar = SegmentedProgressBar(
            self,
            active_color=COLORS["error"],
            segment_width=12,
            spacing=4
        )
        self.progress_bar.grid(
            row=1, column=0,
            sticky="ew",
            padx=SPACING["md"],
            pady=SPACING["xs"]
        )
        self.progress_bar.set(0)
        
        # Detail text
        self.detail_label = ctk.CTkLabel(
            self,
            text="",
            **get_label_style("muted")
        )
        self.detail_label.grid(
            row=2, column=0,
            sticky="w",
            padx=SPACING["md"],
            pady=(SPACING["xs"], SPACING["md"])
        )
    
    def set_progress(self, value: float, status: str = "", detail: str = ""):
        """
        Update progress.
        
        Args:
            value: Progress value between 0 and 1
            status: Main status text
            detail: Detail text (optional)
        """
        self.progress_bar.set(value)
        
        if status:
            self.status_label.configure(text=status)
        
        self.detail_label.configure(text=detail)
    
    def set_status(self, status: str):
        """Update just the status text."""
        self.status_label.configure(text=status)
    
    def set_indeterminate(self, status: str = "Processing..."):
        """Set progress bar to indeterminate mode."""
        # SegmentedProgressBar doesn't support built-in indeterminate
        # self.progress_bar.configure(mode="indeterminate")
        # self.progress_bar.start()
        self.status_label.configure(text=status)
    
    def stop_indeterminate(self):
        """Stop indeterminate mode."""
        # self.progress_bar.stop()
        # self.progress_bar.configure(mode="determinate")
        pass
    
    def reset(self):
        """Reset progress panel."""
        # self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.status_label.configure(text="Ready")
        self.detail_label.configure(text="")
    
    def set_success(self, message: str = "Complete!"):
        """Show success state."""
        self.progress_bar.set(1)
    def set_success(self, message: str = "Complete!"):
        """Show success state."""
        self.progress_bar.set(1)
        self.progress_bar.configure(progress_color=COLORS["success"])
        self.status_label.configure(text=message, text_color=COLORS["success"])
    
    def set_error(self, message: str = "Error occurred"):
        """Show error state."""
    def set_error(self, message: str = "Error occurred"):
        """Show error state."""
        self.progress_bar.configure(progress_color=COLORS["error"])
        self.status_label.configure(text=message, text_color=COLORS["error"])


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


class APIKeyPanel(ctk.CTkFrame):
    """
    Panel for API key management with validation, model selection, and status display.
    """
    
    def __init__(
        self,
        master,
        on_validated: Optional[Callable[[bool, List[str]], None]] = None,
        on_model_changed: Optional[Callable[[str], None]] = None,
        show_header: bool = True,
        **kwargs
    ):
        super().__init__(master, **get_frame_style("card" if show_header else "transparent"), **kwargs)
        
        self.on_validated = on_validated
        self.on_model_changed = on_model_changed
        self.show_header = show_header
        self.is_validated = False
        self.available_models: List[str] = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the API key panel UI."""
        self.grid_columnconfigure(0, weight=1)
        
        row_idx = 0
        
        # Header (Optional)
        if self.show_header:
            header_frame = ctk.CTkFrame(self, fg_color="transparent")
            header_frame.grid(row=row_idx, column=0, sticky="ew", padx=SPACING["md"], pady=(SPACING["md"], SPACING["sm"]))
            header_frame.grid_columnconfigure(1, weight=1)
            
            header_label = ctk.CTkLabel(
                header_frame,
                text="🔑 API Configuration",
                **get_label_style("subheading")
            )
            header_label.grid(row=0, column=0, sticky="w")
            
            # Status badge
            self.status_badge = StatusBadge(header_frame, text="Not Configured", variant="warning")
            self.status_badge.grid(row=0, column=2, sticky="e")
            
            row_idx += 1
        else:
            # Create status badge but don't show it (can be reparented/queried later)
            self.status_badge = StatusBadge(self, text="Not Configured", variant="warning")
        
        # API Key input row
        api_frame = ctk.CTkFrame(self, fg_color="transparent")
        api_frame.grid(row=row_idx, column=0, sticky="ew", padx=SPACING["md"] if self.show_header else 0, pady=SPACING["xs"])
        api_frame.grid_columnconfigure(1, weight=1)
        
        api_label = ctk.CTkLabel(
            api_frame,
            text="OpenRouter Key:",
            width=120,
            anchor="w",
            **get_label_style("body")
        )
        api_label.grid(row=0, column=0, sticky="w", padx=(0, SPACING["sm"]))
        
        self.api_key_entry = ctk.CTkEntry(
            api_frame,
            placeholder_text="sk-or-...",
            show="•",
            **get_input_style()
        )
        self.api_key_entry.grid(row=0, column=1, sticky="ew", padx=(0, SPACING["sm"]))
        
        # Show/Hide button
        self.show_key = False
        self.toggle_btn = ctk.CTkButton(
            api_frame,
            text="👁",
            width=35,
            command=self._toggle_key_visibility,
            **get_button_style("ghost")
        )
        self.toggle_btn.grid(row=0, column=2, padx=(0, SPACING["sm"]))
        
        # Validate button
        self.validate_btn = ctk.CTkButton(
            api_frame,
            text="Validate",
            width=80,
            command=self._validate_api_key,
            **get_button_style("primary")
        )
        self.validate_btn.grid(row=0, column=3)
        row_idx += 1
        
        # Model selector row (initially hidden)
        self.model_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        model_label = ctk.CTkLabel(
            self.model_frame,
            text="Model:",
            width=120,
            anchor="w",
            **get_label_style("body")
        )
        model_label.grid(row=0, column=0, sticky="w", padx=(0, SPACING["sm"]))
        
        self.model_dropdown = ctk.CTkOptionMenu(
            self.model_frame,
            values=["Select model..."],
            command=self._on_model_selected,
            width=300,
            fg_color=COLORS["bg_dark"],
            button_color=COLORS["bg_light"],
            button_hover_color=COLORS["border"],
            dropdown_fg_color=COLORS["bg_dark"],
            dropdown_hover_color=COLORS["bg_light"],
            corner_radius=RADIUS["md"]
        )
        self.model_dropdown.grid(row=0, column=1, sticky="w")
        
        # Model info label
        self.model_info_label = ctk.CTkLabel(
            self.model_frame,
            text="",
            **get_label_style("muted")
        )
        self.model_info_label.grid(row=0, column=2, sticky="w", padx=SPACING["md"])
        
        # Status message
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            **get_label_style("muted")
        )
        self.status_label.grid(row=row_idx, column=0, sticky="w", padx=SPACING["md"] if self.show_header else 0, pady=(SPACING["xs"], SPACING["md"]))
        
        # Token usage display (initially hidden)
        self.token_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=RADIUS["md"])
        
        token_header = ctk.CTkLabel(
            self.token_frame,
            text="📊 Token Usage",
            **get_label_style("body")
        )
        token_header.grid(row=0, column=0, sticky="w", padx=SPACING["sm"], pady=(SPACING["sm"], SPACING["xs"]))
        
        self.token_label = ctk.CTkLabel(
            self.token_frame,
            text="Prompt: 0 | Completion: 0 | Total: 0",
            **get_label_style("mono")
        )
        self.token_label.grid(row=1, column=0, sticky="w", padx=SPACING["sm"], pady=(0, SPACING["sm"]))
    
    def _toggle_key_visibility(self):
        """Toggle API key visibility."""
        self.show_key = not self.show_key
        if self.show_key:
            self.api_key_entry.configure(show="")
            self.toggle_btn.configure(text="🔒")
        else:
            self.api_key_entry.configure(show="•")
            self.toggle_btn.configure(text="👁")
    
    def _validate_api_key(self):
        """Validate the API key."""
        api_key = self.api_key_entry.get().strip()
        
        if not api_key:
            self._set_status("Please enter an API key", "error")
            return
        
        # Show loading state
        self.validate_btn.configure(state="disabled", text="...")
        self._set_status("Validating API key...", "info")
        
        # Run validation in background
        import threading
        thread = threading.Thread(
            target=self._do_validation,
            args=(api_key,),
            daemon=True
        )
        thread.start()
    
    def _do_validation(self, api_key: str):
        """Perform API validation (runs in background thread)."""
        try:
            from core.translator import validate_and_save_api_key
            result = validate_and_save_api_key(api_key)
            
            # Update UI on main thread
            self.after(0, lambda: self._handle_validation_result(result))
        except Exception as e:
            self.after(0, lambda e=e: self._handle_validation_error(str(e)))
    
    def _handle_validation_result(self, result):
        """Handle validation result on main thread."""
        from core.translator import APIValidationResult
        
        self.validate_btn.configure(state="normal", text="Validate")
        
        if result.is_valid:
            self.is_validated = True
            self.available_models = [m.short_name for m in result.available_models]
            
            # Update UI
            self.status_badge.set_text("✓ Validated")
            self.status_badge.set_variant("success")
            self._set_status(result.message, "success")
            
            # Show model selector
            # Show model selector
            model_row = 2 if self.show_header else 1
            self.model_frame.grid(row=model_row, column=0, sticky="ew", padx=SPACING["md"] if self.show_header else 0, pady=SPACING["xs"])
            
            # Move status label down
            self.status_label.grid(row=model_row + 1, column=0, sticky="w", padx=SPACING["md"] if self.show_header else 0, pady=(SPACING["xs"], SPACING["md"]))
            self.model_dropdown.configure(values=self.available_models)
            
            # Auto-select first recommended model
            if self.available_models:
                # Prefer flash models
                for model in self.available_models:
                    if "flash" in model.lower():
                        self.model_dropdown.set(model)
                        self._on_model_selected(model)
                        break
                else:
                    self.model_dropdown.set(self.available_models[0])
                    self._on_model_selected(self.available_models[0])
            
            # Show token display
            # Show token display
            self.token_frame.grid(row=model_row + 2, column=0, sticky="ew", padx=SPACING["md"] if self.show_header else 0, pady=(SPACING["xs"], SPACING["md"]))
            
            # Callback
            if self.on_validated:
                self.on_validated(True, self.available_models)
        else:
            self.is_validated = False
            self.status_badge.set_text("Invalid")
            self.status_badge.set_variant("error")
            self._set_status(result.message, "error")
            
            # Hide model selector
            self.model_frame.grid_remove()
            self.token_frame.grid_remove()
            
            if self.on_validated:
                self.on_validated(False, [])
    
    def _handle_validation_error(self, error: str):
        """Handle validation error."""
        self.validate_btn.configure(state="normal", text="Validate")
        self.is_validated = False
        self.status_badge.set_text("Error")
        self.status_badge.set_variant("error")
        self._set_status(f"Validation error: {error}", "error")
        
        if self.on_validated:
            self.on_validated(False, [])
    
    def _set_status(self, message: str, variant: str = "info"):
        """Set status message with color."""
        color_map = {
            "info": COLORS["text_secondary"],
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "error": COLORS["error"],
        }
        self.status_label.configure(text=message, text_color=color_map.get(variant, COLORS["text_secondary"]))
    
    def _on_model_selected(self, model_name: str):
        """Handle model selection."""
        # Update model info
        from core.translator import get_api_manager
        api_manager = get_api_manager()
        
        if api_manager.select_model(model_name):
            model_info = api_manager.get_selected_model_info()
            if model_info:
                info_text = f"Input: {model_info.input_token_limit:,} | Output: {model_info.output_token_limit:,} tokens"
                self.model_info_label.configure(text=info_text)
        
        if self.on_model_changed:
            self.on_model_changed(model_name)
    
    def set_api_key(self, api_key: str):
        """Set the API key in the entry field."""
        self.api_key_entry.delete(0, "end")
        self.api_key_entry.insert(0, api_key)
    
    def get_api_key(self) -> str:
        """Get the current API key."""
        return self.api_key_entry.get().strip()
    
    def get_selected_model(self) -> str:
        """Get the selected model name."""
        return self.model_dropdown.get()
    
    def set_model(self, model_name: str):
        """Set the selected model programmatically."""
        if model_name in self.available_models:
            self.model_dropdown.set(model_name)
            self._on_model_selected(model_name)
        elif self.is_validated:
            # Try to select even if not in list (might be hidden or new)
            self.model_dropdown.set(model_name)
            self._on_model_selected(model_name)
    
    def update_token_usage(self, prompt: int, completion: int, total: int):
        """Update the token usage display."""
        self.token_label.configure(
            text=f"Prompt: {prompt:,} | Completion: {completion:,} | Total: {total:,}"
        )
    
    def reset_token_usage(self):
        """Reset the token usage display."""
        self.token_label.configure(text="Prompt: 0 | Completion: 0 | Total: 0")


class SummaryWindow(ctk.CTkFrame):
    """
    Custom themed summary view for displaying translation results.
    Overlays the main content area.
    """
    
    def __init__(
        self,
        master,
        output_path: str,
        lines_translated: int,
        model_used: str,
        duration_seconds: float,
        removed_old_subs: bool,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        estimated_cost: Optional[float] = None,
        provider: str = "Unknown",
        on_open_folder: Optional[Callable[[], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color=COLORS["bg_dark"], **kwargs)
        
        self.output_path = output_path
        self.lines_translated = lines_translated
        self.model_used = model_used
        self.duration_seconds = duration_seconds
        self.removed_old_subs = removed_old_subs
        self.provider = provider
        self.on_open_folder = on_open_folder
        self.on_close_callback = on_close
        
        self._setup_ui(
            output_path, lines_translated, model_used, duration_seconds,
            removed_old_subs, prompt_tokens, completion_tokens, total_tokens,
            estimated_cost
        )
    
    def _setup_ui(
        self,
        output_path: str,
        lines_translated: int,
        model_used: str,
        duration_seconds: float,
        removed_old_subs: bool,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        estimated_cost: Optional[float] = None
    ):
        """Setup the summary view UI."""
        # 1. Header (Top)
        header_frame = ctk.CTkFrame(self, fg_color=COLORS["success_bg"], corner_radius=0, height=80)
        header_frame.pack(side="top", fill="x")
        header_frame.grid_propagate(False)
        
        header_content = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_content.place(relx=0.5, rely=0.5, anchor="center")
        
        success_icon = ctk.CTkLabel(
            header_content,
            text="✅",
            font=(FONTS["family"], 32),
            text_color=COLORS["success"]
        )
        success_icon.pack(side="left", padx=(0, SPACING["sm"]))
        
        success_text = ctk.CTkLabel(
            header_content,
            text="Translation Complete!",
            font=(FONTS["family"], FONTS["heading_size"], "bold"),
            text_color=COLORS["success"]
        )
        success_text.pack(side="left")

        # 2. Content (Scrollable)
        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(side="top", fill="both", expand=True, padx=SPACING["lg"], pady=SPACING["md"])
        
        # Main container to center everything
        main_container = ctk.CTkFrame(content, fg_color="transparent")
        main_container.pack(expand=True, fill="both")
        
        # Summary items table
        summary_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        summary_frame.pack(pady=SPACING["md"])
        
        # Format cost nicely if available
        cost_value = "N/A"
        if estimated_cost is not None:
             if estimated_cost < 0.01:
                cost_value = f"${estimated_cost:.6f}"
             elif estimated_cost < 1.0:
                cost_value = f"${estimated_cost:.4f}"
             else:
                cost_value = f"${estimated_cost:.2f}"

        summary_items = [
            ("🤖", "Provider", self.provider.title()),
            ("🧠", "Model", self.model_used),
        ]
        
        # Add cost if applicable
        if estimated_cost is not None:
            summary_items.append(("💰", "Est. Cost", cost_value))

        summary_items.extend([
            ("⏱️", "Duration", self._format_duration(self.duration_seconds)),
            ("📝", "Lines", f"{self.lines_translated:,}"),
            ("🗑️", "Cleaned", "Yes" if self.removed_old_subs else "No")
        ])
        
        for i, (icon, label, value) in enumerate(summary_items):
            self._create_summary_row(summary_frame, i, icon, label, value)
            
        # Separator
        separator = ctk.CTkFrame(main_container, fg_color=COLORS["border"], height=1)
        separator.pack(fill="x", padx=SPACING["xl"], pady=SPACING["md"])
        
        # Token usage section
        token_section = ctk.CTkFrame(main_container, fg_color="transparent")
        token_section.pack(pady=SPACING["sm"])
        
        token_header = ctk.CTkLabel(
            token_section,
            text="📊 Token Usage",
            **get_label_style("subheading")
        )
        token_header.pack(anchor="center", pady=(0, SPACING["sm"]))
        
        token_frame = ctk.CTkFrame(token_section, fg_color=COLORS["bg_medium"], corner_radius=RADIUS["md"])
        token_frame.pack()
        token_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Token stats
        token_stats = [
            ("Prompt", prompt_tokens),
            ("Completion", completion_tokens),
            ("Total", total_tokens),
        ]
        
        for i, (label, value) in enumerate(token_stats):
            stat_frame = ctk.CTkFrame(token_frame, fg_color="transparent")
            stat_frame.grid(row=0, column=i, padx=SPACING["lg"], pady=SPACING["md"])
            
            value_label = ctk.CTkLabel(
                stat_frame,
                text=f"{value:,}",
                font=(FONTS["family"], FONTS["subheading_size"], "bold"),
                text_color=COLORS["primary_light"]
            )
            value_label.pack()
            
            name_label = ctk.CTkLabel(
                stat_frame,
                text=label,
                **get_label_style("muted")
            )
            name_label.pack()
        
        # Output path
        output_section = ctk.CTkFrame(main_container, fg_color="transparent")
        output_section.pack(pady=SPACING["md"], fill="x", padx=SPACING["xl"])
        
        output_header = ctk.CTkLabel(
            output_section,
            text="📁 Output File",
            **get_label_style("subheading")
        )
        output_header.pack(anchor="center", pady=(0, SPACING["sm"]))
        
        output_frame = ctk.CTkFrame(output_section, fg_color=COLORS["bg_medium"], corner_radius=RADIUS["md"])
        output_frame.pack(fill="x")
        
        # Truncate path if too long
        display_path = output_path
        if len(display_path) > 60:
            display_path = "..." + display_path[-57:]
        
        path_label = ctk.CTkLabel(
            output_frame,
            text=display_path,
            font=(FONTS["mono_family"], FONTS["small_size"]),
            text_color=COLORS["text_secondary"],
            wraplength=500
        )
        path_label.pack(pady=SPACING["sm"], padx=SPACING["md"])
        
        # 3. Footer (Buttons)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", pady=SPACING["lg"])
        
        # Center buttons
        btn_container = ctk.CTkFrame(btn_frame, fg_color="transparent")
        btn_container.pack()
        
        open_folder_btn = ctk.CTkButton(
            btn_container,
            text="📂 Open Folder",
            width=140,
            height=40,
            command=self._open_folder,
            **get_button_style("primary")
        )
        open_folder_btn.pack(side="left", padx=SPACING["sm"])
        
        close_btn = ctk.CTkButton(
            btn_container,
            text="Close",
            width=100,
            height=40,
            command=self._close,
            **get_button_style("secondary")
        )
        close_btn.pack(side="left", padx=SPACING["sm"])
    
    def _create_summary_row(self, parent, row: int, icon: str, label: str, value: str):
        """Create a summary row with icon, label, and value."""
        icon_label = ctk.CTkLabel(
            parent,
            text=icon,
            font=(FONTS["family"], 20),
            width=30
        )
        icon_label.grid(row=row, column=0, sticky="w", pady=SPACING["xs"])
        
        label_widget = ctk.CTkLabel(
            parent,
            text=label,
            **get_label_style("body"),
            anchor="w"
        )
        label_widget.grid(row=row, column=1, sticky="w", padx=SPACING["sm"], pady=SPACING["xs"])
        
        value_widget = ctk.CTkLabel(
            parent,
            text=value,
            font=(FONTS["family"], FONTS["body_size"], "bold"),
            text_color=COLORS["text_primary"],
            anchor="e"
        )
        value_widget.grid(row=row, column=2, sticky="e", pady=SPACING["xs"])
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human readable string."""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def _open_folder(self):
        """Open the output folder."""
        if self.on_open_folder:
            self.on_open_folder()
        else:
            import os
            try:
                os.startfile(Path(self.output_path).parent)
            except Exception:
                pass
        self._close()
        
    def _close(self):
        """Handle close."""
        if self.on_close_callback:
            self.on_close_callback()
        else:
            self.destroy()


class LogPanel(ctk.CTkFrame):
    """
    Expandable activity log panel.
    Displays logs from the core Logger.
    """
    
    def __init__(self, parent, logger_instance, on_toggle=None, expanded=False, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.logger = logger_instance
        self.on_toggle = on_toggle
        self.is_expanded = expanded
        
        # Header (Always visible)
        self.header_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_medium"], height=40, corner_radius=RADIUS["md"])
        self.header_frame.pack(fill="x", pady=(0, 5))
        self.header_frame.grid_propagate(False) # Fixed height
        
        # Toggle button
        self.toggle_btn = ctk.CTkButton(
            self.header_frame,
            text="▼ Activity Log" if self.is_expanded else "▶ Activity Log", # Right arrow when collapsed
            width=120,
            height=30,
            fg_color="transparent",
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["bg_dark"],
            anchor="w",
            command=self._toggle_expand
        )
        self.toggle_btn.pack(side="left", padx=SPACING["sm"])
        
        # Last log preview (visible when collapsed)
        self.preview_label = ctk.CTkLabel(
            self.header_frame,
            text="",
            text_color=COLORS["text_muted"],
            font=(FONTS["family"], FONTS["small_size"]),
            anchor="w"
        )
        if not self.is_expanded:
            self.preview_label.pack(side="left", fill="x", expand=True, padx=SPACING["md"])
        
        # Actions frame (visible when expanded)
        self.actions_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        if self.is_expanded:
            self.actions_frame.pack(side="right", padx=SPACING["sm"])
        
        # Clear button
        self.clear_btn = ctk.CTkButton(
            self.actions_frame,
            text="Clear",
            width=60,
            height=24,
            font=(FONTS["family"], FONTS["small_size"]),
            fg_color=COLORS["bg_light"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            command=self._clear_logs
        )
        self.clear_btn.pack(side="right", padx=5)
        
        # Save button
        self.save_btn = ctk.CTkButton(
            self.actions_frame,
            text="Save Log",
            width=70,
            height=24,
            font=(FONTS["family"], FONTS["small_size"]),
            fg_color=COLORS["bg_light"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            command=self._save_logs
        )
        self.save_btn.pack(side="right", padx=5)
        
        # Content frame (Hidden by default)
        self.content_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_medium"], corner_radius=RADIUS["md"])
        if self.is_expanded:
            self.content_frame.pack(fill="both", expand=True)
        
        # Log text area
        # Log text area
        self.log_text = ctk.CTkTextbox(
            self.content_frame,
            font=("Consolas", 12),
            activate_scrollbars=True,
            fg_color=COLORS["bg_dark"],
            text_color=COLORS["text_secondary"],
            height=150
        )
        self.log_text.pack(fill="both", expand=True, padx=SPACING["sm"], pady=SPACING["sm"])
        
        # Configure tags for coloring
        self.log_text.tag_config("ERROR", foreground=COLORS["error"])
        self.log_text.tag_config("WARNING", foreground=COLORS["warning"])
        self.log_text.tag_config("INFO", foreground=COLORS["text_secondary"])
        self.log_text.tag_config("SUCCESS", foreground=COLORS["success"])
        
        self.log_text.configure(state="disabled")
        
        # Register callback
        self.logger.add_callback(self.append_log)
        
    def _toggle_expand(self):
        """Toggle panel expansion."""
        self.is_expanded = not self.is_expanded
        
        if self.is_expanded:
            self.toggle_btn.configure(text="▼ Activity Log")
            self.preview_label.pack_forget()
            self.actions_frame.pack(side="right", padx=SPACING["sm"])
            self.content_frame.pack(fill="both", expand=True)
        else:
            self.toggle_btn.configure(text="▶ Activity Log")
            self.content_frame.pack_forget()
            self.actions_frame.pack_forget()
            self.preview_label.pack(side="left", fill="x", expand=True, padx=SPACING["md"])
            
        if self.on_toggle:
            self.on_toggle(self.is_expanded)
            
    def append_log(self, timestamp: str, level: str, message: str):
        """Callback to add log message."""
        formatted_line = f"[{timestamp}] [{level}] {message}\n"
        
        # Determine tag based on level
        tag = "INFO"
        if level in ["ERROR", "CRITICAL"]:
            tag = "ERROR"
        elif level == "WARNING":
            tag = "WARNING"
        elif "success" in message.lower() or "complete" in message.lower():
            tag = "SUCCESS"
            
        def _update_ui():
            try:
                # Update preview (if not expanded)
                if not self.is_expanded:
                    preview_text = f"[{level}] {message}"
                    if len(preview_text) > 80:
                        preview_text = preview_text[:77] + "..."
                    
                    # Set preview color
                    color = COLORS["text_muted"]
                    if tag == "ERROR":
                        color = COLORS["error"]
                    elif tag == "WARNING":
                        color = COLORS["warning"]
                    elif tag == "SUCCESS":
                        color = COLORS["success"]
                        
                    self.preview_label.configure(text=preview_text, text_color=color)
                
                # Update text widget
                self.log_text.configure(state="normal")
                self.log_text.insert("end", formatted_line, tag)
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
            except Exception:
                pass # GUI might be destroyed

        # Ensure UI updates happen on main thread
        self.after(0, _update_ui)
        
    def _clear_logs(self):
        """Clear all logs."""
        self.logger.clear()
        self.log_text.configure(state="normal")
        self.log_text.delete("0.0", "end")
        self.log_text.configure(state="disabled")
        self.preview_label.configure(text="Logs cleared")
        
    def _save_logs(self):
        """Save logs to file."""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=f"subauto_log_{int(time.time())}.txt"
        )
        if filename:
            self.logger.save_to_file(filename)
            self.logger.info(f"Log saved to: {filename}")

class ModelSelectorDialog(ctk.CTkToplevel):
    """
    Searchable, scrollable model selector dialog.
    """
    
    def __init__(
        self,
        parent,
        models: List[str],
        on_select: Callable[[str], None],
        current_model: str = "",
        title: str = "Select Model"
    ):
        super().__init__(parent)
        
        self.models = models
        self.filtered_models = models
        self.on_select_callback = on_select
        self.current_model = current_model
        
        # Window setup
        self.title(title)
        self.configure(fg_color=COLORS["bg_dark"])
        
        # Set transient BEFORE geometry to avoid parent window position jumps
        # Find the toplevel window (root)
        root = parent.winfo_toplevel()
        self.transient(root)
        
        # Center dialog on parent window (not screen center)
        width = 400
        height = 500
        
        # Wait for parent geometry to be available
        root.update_idletasks()
        
        parent_x = root.winfo_x()
        parent_y = root.winfo_y()
        parent_width = root.winfo_width()
        parent_height = root.winfo_height()
        
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        self.grab_set()
        
        self._setup_ui()
        self.focus_force()
        
    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header / Search
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=SPACING["md"], pady=SPACING["md"])
        header.grid_columnconfigure(0, weight=1)
        
        self.search_entry = ctk.CTkEntry(
            header,
            placeholder_text="🔍 Search models...",
            **get_input_style()
        )
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search)
        
        # Models List
        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            label_text=None
        )
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=SPACING["sm"], pady=(0, SPACING["md"]))
        self.list_frame.grid_columnconfigure(0, weight=1)
        
        self._populate_list(self.models)
        
        # Close button
        close_btn = ctk.CTkButton(
            self,
            text="Cancel",
            command=self.destroy,
            **get_button_style("secondary")
        )
        close_btn.grid(row=2, column=0, pady=(0, SPACING["md"]))
        
    def _populate_list(self, models: List[str]):
        """Populate the list with model buttons."""
        # Clear existing
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        if not models:
            lbl = ctk.CTkLabel(self.list_frame, text="No models found", **get_label_style("muted"))
            lbl.pack(pady=SPACING["md"])
            return
            
        for model in models:
            is_selected = model == self.current_model
            
            btn = ctk.CTkButton(
                self.list_frame,
                text=model,
                anchor="w",
                fg_color=COLORS["primary"] if is_selected else COLORS["bg_light"],
                text_color=COLORS["bg_dark"] if is_selected else COLORS["text_primary"],
                hover_color=COLORS["primary_hover"] if is_selected else COLORS["border"],
                height=35,
                command=lambda m=model: self._on_select(m)
            )
            btn.pack(fill="x", pady=2, padx=2)
            
    def _on_search(self, event):
        """Filter models based on search text."""
        query = self.search_entry.get().lower()
        self.filtered_models = [m for m in self.models if query in m.lower()]
        self._populate_list(self.filtered_models)
        
        # Scroll to top after filtering
        try:
            self.list_frame._parent_canvas.yview_moveto(0)
        except Exception:
            pass  # Ignore if canvas not available
        
        if self.on_select_callback:
            self.on_select_callback(model)
        self.destroy()


class SubtitleEditor(ctk.CTkToplevel):
    """
    Subtitle editor dialog for reviewing and editing translated subtitles.
    Displays the SRT content in an editable text area with save/discard options.
    Opens as a resizable window.
    """
    
    def __init__(
        self,
        master,
        subtitle_path: str,
        on_approve: Optional[Callable[[str], None]] = None,
        on_discard: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        
        self.subtitle_path = subtitle_path
        self.on_approve_callback = on_approve
        self.on_discard_callback = on_discard
        self.original_content = ""
        
        # Window configuration
        self.title("Review Subtitle Translation")
        self.configure(fg_color=COLORS["bg_dark"])
        
        # Set window size and position
        width = 1200
        height = 800
        
        # Center on parent window
        root = master.winfo_toplevel()
        root.update_idletasks()
        
        parent_x = root.winfo_x()
        parent_y = root.winfo_y()
        parent_width = root.winfo_width()
        parent_height = root.winfo_height()
        
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Set minimum size
        self.minsize(800, 600)
        
        # Make it modal
        self.transient(root)
        self.grab_set()
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        # Editor state
        self.undo_stack = []
        self.redo_stack = []
        self.last_content = ""
        self.search_index = "1.0"
        self.search_matches = []
        
        self._setup_ui()
        self._load_subtitle()
        
        # Setup keyboard shortcuts
        self._setup_keyboard_shortcuts()
        
        # Focus the window
        self.focus_force()
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts."""
        self.bind("<Control-s>", lambda e: self._on_approve())
        self.bind("<Control-f>", lambda e: self._show_find_dialog())
        self.bind("<Control-h>", lambda e: self._show_replace_dialog())
        self.bind("<Control-g>", lambda e: self._show_goto_dialog())
        self.bind("<Escape>", lambda e: self._on_window_close())
        # Note: Undo/Redo handled by CTkTextbox natively
    
    def _setup_ui(self):
        """Setup the editor UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Toolbar
        self.grid_rowconfigure(1, weight=0) # Info
        self.grid_rowconfigure(2, weight=1) # Editor area gets the weight
        
        # Toolbar
        toolbar_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_medium"], corner_radius=0)
        toolbar_frame.grid(row=0, column=0, sticky="ew", pady=0)
        
        toolbar_content = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
        toolbar_content.pack(fill="x", padx=SPACING["lg"], pady=SPACING["sm"])
        
        # Search button
        search_btn = ctk.CTkButton(
            toolbar_content,
            text="🔍 Find",
            width=80,
            height=28,
            command=self._show_find_dialog,
            **get_button_style("ghost")
        )
        search_btn.pack(side="left", padx=(0, SPACING["xs"]))
        
        # Replace button
        replace_btn = ctk.CTkButton(
            toolbar_content,
            text="Aa Replace",
            width=80,
            height=28,
            command=self._show_replace_dialog,
            **get_button_style("ghost")
        )
        replace_btn.pack(side="left", padx=(0, SPACING["xs"]))
        
        # Go to entry button
        goto_btn = ctk.CTkButton(
            toolbar_content,
            text="↗️ Go to",
            width=80,
            height=28,
            command=self._show_goto_dialog,
            **get_button_style("ghost")
        )
        goto_btn.pack(side="left", padx=SPACING["xs"])
        
        # Separator
        sep1 = ctk.CTkLabel(toolbar_content, text="|", text_color=COLORS["border"])
        sep1.pack(side="left", padx=SPACING["sm"])
        
        # Validate button
        validate_btn = ctk.CTkButton(
            toolbar_content,
            text="✓ Validate",
            width=90,
            height=28,
            command=self._validate_content,
            **get_button_style("ghost")
        )
        validate_btn.pack(side="left", padx=SPACING["xs"])
        
        # Separator
        sep2 = ctk.CTkLabel(toolbar_content, text="|", text_color=COLORS["border"])
        sep2.pack(side="left", padx=SPACING["sm"])
        
        # Syntax highlighting toggle
        self.syntax_enabled = True
        self.syntax_btn = ctk.CTkButton(
            toolbar_content,
            text="🎨 Syntax: ON",
            width=110,
            height=28,
            command=self._toggle_syntax,
            **get_button_style("ghost")
        )
        self.syntax_btn.pack(side="left", padx=SPACING["xs"])
        
        # Info on right side
        shortcuts_label = ctk.CTkLabel(
            toolbar_content,
            text="💡 Ctrl+S: Save | Ctrl+F: Find | Ctrl+G: Go to | Esc: Close",
            **get_label_style("muted")
        )
        shortcuts_label.pack(side="right", padx=SPACING["sm"])
        
        # Info bar
        info_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_medium"], corner_radius=0)
        info_frame.grid(row=1, column=0, sticky="ew", pady=(0, SPACING["sm"]))
        
        info_label = ctk.CTkLabel(
            info_frame,
            text="💡 Review and edit the translated subtitles below. Click 'Approve & Merge' when ready.",
            **get_label_style("body"),
            anchor="w"
        )
        info_label.pack(fill="x", padx=SPACING["md"], pady=SPACING["sm"])
        
        # Editor area
        editor_container = ctk.CTkFrame(self, fg_color="transparent")
        editor_container.grid(row=2, column=0, sticky="nsew", padx=SPACING["lg"], pady=(0, SPACING["sm"]))
        editor_container.grid_columnconfigure(0, weight=1)
        editor_container.grid_rowconfigure(0, weight=1)
        
        # Text editor with improved styling
        self.text_editor = ctk.CTkTextbox(
            editor_container,
            font=(FONTS["mono_family"], FONTS["body_size"] + 1),  # Slightly larger
            fg_color=COLORS["bg_dark"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border_light"],
            border_width=2,
            wrap="word",
            activate_scrollbars=True,
            undo=True,
            maxundo=-1
        )
        self.text_editor.grid(row=0, column=0, sticky="nsew")
        
        # Bind Undo/Redo keys explicitly
        self.text_editor.bind("<Control-z>", lambda e: self.text_editor.edit_undo())
        self.text_editor.bind("<Control-y>", lambda e: self.text_editor.edit_redo())
        self.text_editor.bind("<Control-Shift-z>", lambda e: self.text_editor.edit_redo())
        
        # Configure syntax highlighting tags
        self.text_editor.tag_config("number", foreground=COLORS["syntax_number"])
        self.text_editor.tag_config("timestamp", foreground=COLORS["syntax_timestamp"])
        self.text_editor.tag_config("arrow", foreground=COLORS["syntax_arrow"])
        self.text_editor.tag_config("text", foreground=COLORS["syntax_text"])
        self.text_editor.tag_config("error", foreground=COLORS["syntax_error"], background=COLORS["error_bg"])
        self.text_editor.tag_config("search_highlight", background=COLORS["warning_bg"], foreground=COLORS["warning"])
        
        # Bind events
        self.text_editor.bind("<<Modified>>", self._on_text_modified)
        
        # Stats label with more info
        self.stats_label = ctk.CTkLabel(
            editor_container,
            text="",
            **get_label_style("muted"),
            anchor="e"
        )
        self.stats_label.grid(row=1, column=0, sticky="e", pady=(SPACING["xs"], 0))
        
        # Footer with buttons
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=3, column=0, sticky="ew", pady=SPACING["lg"])
        
        # Center buttons
        btn_container = ctk.CTkFrame(footer_frame, fg_color="transparent")
        btn_container.pack()
        
        discard_btn = ctk.CTkButton(
            btn_container,
            text="Discard",
            width=120,
            height=40,
            command=self._on_discard,
            **get_button_style("secondary")
        )
        discard_btn.pack(side="left", padx=SPACING["sm"])
        
        approve_btn = ctk.CTkButton(
            btn_container,
            text="✓ Approve & Merge",
            width=180,
            height=40,
            command=self._on_approve,
            **get_button_style("success")
        )
        approve_btn.pack(side="left", padx=SPACING["sm"])
    
    def _load_subtitle(self):
        """Load subtitle content from file."""
        try:
            with open(self.subtitle_path, 'r', encoding='utf-8') as f:
                self.original_content = f.read()
            
            self.text_editor.delete("0.0", "end")
            self.text_editor.insert("0.0", self.original_content)
            
            # Update stats
            lines = self.original_content.strip().split('\n')
            # Count subtitle entries (rough estimate: every block separated by blank line)
            subtitle_count = self.original_content.count('\n\n') + 1
            char_count = len(self.original_content)
            
            self.stats_label.configure(
                text=f"📊 {subtitle_count} entries • {char_count:,} characters • {len(lines):,} lines"
            )
            
            # Apply syntax highlighting
            self.last_content = self.original_content
            if self.syntax_enabled:
                self._apply_syntax_highlighting()
            
        except Exception as e:
            self.text_editor.insert("0.0", f"Error loading subtitle: {str(e)}")
            self.stats_label.configure(text="⚠ Error loading file")

    def _on_text_modified(self, event=None):
        """Handle text modification for syntax highlighting."""
        if self.syntax_enabled:
            # Debounce: only apply if content actually changed
            current = self.text_editor.get("0.0", "end-1c")
            if current != self.last_content:
                self.last_content = current
                self.after(100, self._apply_syntax_highlighting)  # Debounce 100ms
    
    def _apply_syntax_highlighting(self):
        """Apply syntax highlighting to SRT format."""
        try:
            # Remove all tags first
            for tag in ["number", "timestamp", "arrow", "text", "error"]:
                self.text_editor.tag_remove(tag, "1.0", "end")
            
            content = self.text_editor.get("1.0", "end-1c")
            lines = content.split('\n')
            
            import re
            line_num = 1
            i = 0
            
            while i < len(lines):
                line = lines[i]
                
                # Entry number (should be just digits)
                if line.strip().isdigit():
                    start = f"{line_num}.0"
                    end = f"{line_num}.end"
                    self.text_editor.tag_add("number", start, end)
                
                # Timestamp line (HH:MM:SS,mmm --> HH:MM:SS,mmm)
                elif '-->' in line:
                    # Validate timestamp format
                    timestamp_pattern = r'^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}$'
                    if re.match(timestamp_pattern, line.strip()):
                        # Valid timestamp
                        parts = line.split('-->')
                        if len(parts) == 2:
                            # Highlight first timestamp
                            start_pos = f"{line_num}.0"
                            arrow_start = f"{line_num}.{len(parts[0])}"
                            self.text_editor.tag_add("timestamp", start_pos, arrow_start)
                            
                            # Highlight arrow
                            arrow_end = f"{line_num}.{len(parts[0]) + 3}"
                            self.text_editor.tag_add("arrow", arrow_start, arrow_end)
                            
                            # Highlight second timestamp
                            end_pos = f"{line_num}.end"
                            self.text_editor.tag_add("timestamp", arrow_end, end_pos)
                    else:
                        # Invalid timestamp format
                        start = f"{line_num}.0"
                        end = f"{line_num}.end"
                        self.text_editor.tag_add("error", start, end)
                
                # Subtitle text (non-empty, not number, not timestamp)
                elif line.strip() and not line.strip().isdigit() and '-->' not in line:
                    start = f"{line_num}.0"
                    end = f"{line_num}.end"
                    self.text_editor.tag_add("text", start, end)
                
                line_num += 1
                i += 1
                
        except Exception as e:
            pass  # Silently fail syntax highlighting
    
    def _toggle_syntax(self):
        """Toggle syntax highlighting on/off."""
        self.syntax_enabled = not self.syntax_enabled
        
        if self.syntax_enabled:
            self.syntax_btn.configure(text="🎨 Syntax: ON")
            self._apply_syntax_highlighting()
        else:
            self.syntax_btn.configure(text="🎨 Syntax: OFF")
            # Remove all syntax tags
            for tag in ["number", "timestamp", "arrow", "text", "error"]:
                self.text_editor.tag_remove(tag, "1.0", "end")
    
    def _show_find_dialog(self):
        """Show find dialog."""
        dialog = ctk.CTkInputDialog(
            text="Enter text to find:",
            title="Find"
        )
        search_text = dialog.get_input()
        
        if search_text:
            self._find_text(search_text)
    
    def _find_text(self, search_text: str):
        """Find and highlight text in editor."""
        # Remove previous highlights
        self.text_editor.tag_remove("search_highlight", "1.0", "end")
        
        # Find all occurrences
        self.search_matches = []
        start_pos = "1.0"
        
        while True:
            pos = self.text_editor.search(search_text, start_pos, stopindex="end", nocase=True)
            if not pos:
                break
            
            end_pos = f"{pos}+{len(search_text)}c"
            self.text_editor.tag_add("search_highlight", pos, end_pos)
            self.search_matches.append(pos)
            start_pos = end_pos
        
        # Jump to first match
        if self.search_matches:
            self.text_editor.see(self.search_matches[0])
            self.stats_label.configure(
                text=f"🔍 Found {len(self.search_matches)} matches"
            )
        else:
            self.stats_label.configure(text="🔍 No matches found")
    
    def _show_replace_dialog(self):
        """Show replace dialog."""
        # Custom dialog for replace
        dialog = ctk.CTkToplevel(self)
        dialog.title("Find & Replace")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Center dialog
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # UI
        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Find
        ctk.CTkLabel(frame, text="Find what:").grid(row=0, column=0, sticky="w", pady=(0, 10))
        find_entry = ctk.CTkEntry(frame, width=250)
        find_entry.grid(row=0, column=1, pady=(0, 10))
        find_entry.focus_set()
        
        # Replace
        ctk.CTkLabel(frame, text="Replace with:").grid(row=1, column=0, sticky="w", pady=(0, 20))
        replace_entry = ctk.CTkEntry(frame, width=250)
        replace_entry.grid(row=1, column=1, pady=(0, 20))
        
        # Buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        
        def do_replace():
            find_txt = find_entry.get()
            rep_txt = replace_entry.get()
            if find_txt:
                count = self._replace_text(find_txt, rep_txt)
                dialog.destroy()
                from tkinter import messagebox
                messagebox.showinfo("Replace", f"Replaced {count} occurrences.")
                self.stats_label.configure(text=f"Aa Replaced {count} occurrences")
        
        ctk.CTkButton(btn_frame, text="Replace All", command=do_replace, width=100).pack(side="right")
        ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy, fg_color=COLORS["bg_light"], hover_color=COLORS["border"], width=80).pack(side="right", padx=10)

    def _replace_text(self, find_text: str, replace_text: str) -> int:
        """Replace all occurrences of text."""
        content = self.text_editor.get("1.0", "end-1c")
        new_content, count = content.replace(find_text, replace_text), content.count(find_text)
        
        if count > 0:
            self.text_editor.delete("1.0", "end")
            self.text_editor.insert("1.0", new_content)
            # Re-apply syntax highlighting
            if self.syntax_enabled:
                self._apply_syntax_highlighting()
                
        return count

    def _show_goto_dialog(self):
        """Show go to entry dialog."""
        dialog = ctk.CTkInputDialog(
            text="Enter entry number to jump to:",
            title="Go to Entry"
        )
        entry_num = dialog.get_input()
        
        if entry_num and entry_num.isdigit():
            self._goto_entry(int(entry_num))
    
    def _goto_entry(self, entry_num: int):
        """Jump to specific subtitle entry."""
        try:
            content = self.text_editor.get("1.0", "end-1c")
            lines = content.split('\n')
            
            # Find the line with this entry number
            for i, line in enumerate(lines):
                if line.strip() == str(entry_num):
                    # Jump to this line
                    line_pos = f"{i + 1}.0"
                    self.text_editor.see(line_pos)
                    self.text_editor.mark_set("insert", line_pos)
                    self.stats_label.configure(text=f"↗️ Jumped to entry {entry_num}")
                    return
            
            self.stats_label.configure(text=f"⚠️ Entry {entry_num} not found")
        except Exception as e:
            self.stats_label.configure(text=f"⚠️ Error: {str(e)}")
    
    def _validate_content(self):
        """Validate SRT format and show errors."""
        try:
            content = self.text_editor.get("1.0", "end-1c")
            lines = content.split('\n')
            
            errors = []
            import re
            
            i = 0
            entry_count = 0
            expected_num = 1
            
            while i < len(lines):
                line = lines[i].strip()
                
                # Skip empty lines
                if not line:
                    i += 1
                    continue
                
                # Should be entry number
                if not line.isdigit():
                    errors.append(f"Line {i+1}: Expected entry number, got '{line[:30]}'")
                    i += 1
                    continue
                
                entry_num = int(line)
                if entry_num != expected_num:
                    errors.append(f"Line {i+1}: Entry number {entry_num} out of sequence (expected {expected_num})")
                
                expected_num += 1
                entry_count += 1
                i += 1
                
                # Next should be timestamp
                if i >= len(lines):
                    errors.append(f"Entry {entry_num}: Missing timestamp")
                    break
                
                timestamp_line = lines[i].strip()
                timestamp_pattern = r'^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}$'
                
                if not re.match(timestamp_pattern, timestamp_line):
                    errors.append(f"Line {i+1}: Invalid timestamp format")
                
                i += 1
                
                # Next should be subtitle text (at least one line)
                has_text = False
                while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                    has_text = True
                    i += 1
                
                if not has_text:
                    errors.append(f"Entry {entry_num}: Missing subtitle text")
            
            # Show results
            if errors:
                error_msg = f"⚠️ Found {len(errors)} error(s):\n" + "\n".join(errors[:5])
                if len(errors) > 5:
                    error_msg += f"\n... and {len(errors) - 5} more"
                
                # Show in a dialog
                from tkinter import messagebox
                messagebox.showwarning("Validation Errors", error_msg)
                self.stats_label.configure(text=f"⚠️ {len(errors)} validation error(s)")
            else:
                from tkinter import messagebox
                messagebox.showinfo("Validation", f"✓ Valid SRT format!\n{entry_count} entries checked.")
                self.stats_label.configure(text=f"✓ Valid SRT format ({entry_count} entries)")
                
        except Exception as e:
            self.stats_label.configure(text=f"⚠️ Validation error: {str(e)}")
    
    def _on_approve(self):
        """Handle approve button click."""
        content = self.text_editor.get("0.0", "end-1c")  # Get all text except trailing newline
        
        if self.on_approve_callback:
            self.on_approve_callback(content)
        
        # Close window
        self.grab_release()
        self.destroy()
    
    def _on_discard(self):
        """Handle discard button click."""
        if self.on_discard_callback:
            self.on_discard_callback()
        
        # Close window
        self.grab_release()
        self.destroy()
    
    def _on_window_close(self):
        """Handle window close button (X)."""
        # Treat as discard
        self._on_discard()


class VerticalStepperItem(ctk.CTkFrame):
    """
    A single step item for the vertical stepper.
    """
    def __init__(
        self,
        master,
        step_number: int,
        title: str,
        description: Optional[str] = None,
        is_active: bool = False,
        is_completed: bool = False,
        is_last: bool = False,
        on_click: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.step_number = step_number
        self.title = title
        self.description = description
        self.is_active = is_active
        self.is_completed = is_completed
        self.is_last = is_last
        self.on_click = on_click
        
        self._setup_ui()
        
    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        
        # Colors based on state
        if self.is_active:
            icon_color = COLORS["accent"] # Changed from primary (text color) to accent (blue)
            text_color = COLORS["text_primary"]
            desc_color = COLORS["text_secondary"]
            font_weight = "bold"
        elif self.is_completed:
            icon_color = COLORS["success"]
            text_color = COLORS["text_primary"]
            desc_color = COLORS["text_muted"]
            font_weight = "normal"
        else:
            icon_color = COLORS["border"]
            text_color = COLORS["text_muted"]
            desc_color = COLORS["text_muted"]
            font_weight = "normal"
            
        # Icon / Number
        self.icon_frame = ctk.CTkFrame(
            self,
            width=32,
            height=32,
            corner_radius=16,
            fg_color=icon_color
        )
        self.icon_frame.grid(row=0, column=0, sticky="n")
        
        # Center the number/check
        icon_text = "✓" if self.is_completed and not self.is_active else str(self.step_number)
        
        self.icon_label = ctk.CTkLabel(
            self.icon_frame,
            text=icon_text,
            font=(FONTS["family"], 14, "bold"),
            text_color="white" if self.is_active or self.is_completed else COLORS["text_secondary"]
        )
        self.icon_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text=self.title,
            font=(FONTS["family"], FONTS["body_size"], font_weight),
            text_color=text_color
        )
        self.title_label.grid(row=0, column=1, sticky="w", padx=SPACING["md"], pady=(2, 0))
        
        # Description (Subtitle)
        if self.description:
            self.desc_label = ctk.CTkLabel(
                self,
                text=self.description,
                font=(FONTS["family"], FONTS["small_size"]),
                text_color=desc_color,
                wraplength=160,
                justify="left"
            )
            self.desc_label.grid(row=1, column=1, sticky="w", padx=SPACING["md"], pady=(0, 4))
        
        # Connector Line (if not last)
        if not self.is_last:
            self.line = ctk.CTkFrame(
                self,
                width=2,
                height=15, # Minimum height
                fg_color=COLORS["success"] if self.is_completed else COLORS["border"]
            )
            
            # If description exists, line needs to span more rows or be placed differently
            # Simple grid approach: place in row 1 (and 2 if desc)
            row_span = 2 if self.description else 1
            self.line.grid(row=1, column=0, rowspan=row_span, sticky="n", pady=(2, 0))
            # Ensure line stretches to fill height
            self.grid_rowconfigure(1, weight=1)
            
        # Click event
        if self.on_click:
            for widget in [self, self.title_label, self.icon_frame, self.icon_label]:
                widget.bind("<Button-1>", lambda e: self.on_click(self.step_number))
            if self.description:
                self.desc_label.bind("<Button-1>", lambda e: self.on_click(self.step_number))
            
            # Cursor
            self.configure(cursor="hand2")
            self.title_label.configure(cursor="hand2")
            self.icon_frame.configure(cursor="hand2")
            self.icon_label.configure(cursor="hand2")
            if self.description:
                self.desc_label.configure(cursor="hand2")


class VerticalStepper(ctk.CTkFrame):
    """
    Vertical stepper navigation component.
    """
    def __init__(
        self,
        master,
        steps: List[str],
        current_step: int = 1,
        on_step_change: Optional[Callable[[int], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.steps = steps
        self.current_step = current_step
        self.on_step_change = on_step_change
        self.step_descriptions = {} # step_idx -> text
        self.completed_steps = set() # Set of completed step indices
        self.items = []
        
        self._refresh()
        
    def _refresh(self):
        # Clear
        for widget in self.winfo_children():
            widget.destroy()
        self.items = []
        
        for i, title in enumerate(self.steps, 1):
            is_active = (i == self.current_step)
            is_completed = (i in self.completed_steps) or (i < self.current_step)
            is_last = (i == len(self.steps))
            
            desc = self.step_descriptions.get(i)
            
            item = VerticalStepperItem(
                self,
                step_number=i,
                title=title,
                description=desc,
                is_active=is_active,
                is_completed=is_completed,
                is_last=is_last,
                on_click=self._handle_click
            )
            item.pack(fill="x", pady=0)
            self.items.append(item)
            
    def _handle_click(self, step_number: int):
        # Prevent jumping ahead to incomplete steps if desired
        # For now, allow navigation to any previous step or the current step
        if self.on_step_change:
            self.on_step_change(step_number)
            
    def set_step(self, step_number: int):
        if 1 <= step_number <= len(self.steps):
            self.current_step = step_number
            self._refresh()
            
    def update_step_description(self, step_number: int, description: str):
        """Update the description/subtitle for a step."""
        if 1 <= step_number <= len(self.steps):
            self.step_descriptions[step_number] = description
            self._refresh()
            
    def clear_step_description(self, step_number: int):
        """Clear description for a step."""
        if step_number in self.step_descriptions:
            del self.step_descriptions[step_number]
            self._refresh()
            
    def set_completed_steps(self, steps: List[int]):
        """Set the list of completed steps."""
        self.completed_steps = set(steps)
        self._refresh()


class HorizontalStepperItem(ctk.CTkFrame):
    """
    A single step item for the horizontal stepper.
    """
    def __init__(
        self,
        master,
        step_number: int,
        title: str,
        is_active: bool = False,
        is_completed: bool = False,
        is_last: bool = False,
        on_click: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.step_number = step_number
        self.title = title
        self.is_active = is_active
        self.is_completed = is_completed
        self.is_last = is_last
        self.on_click = on_click
        
        self._setup_ui()
        
    def _setup_ui(self):
        # Style 3: Minimalist Underline
        # - Text only (with number)
        # - Active: Highlighted text + Underline bar
        # - Completed: Green text
        # - Inactive: Gray text
        
        # Colors & Font
        if self.is_active:
            text_color = COLORS["text_primary"]
            font_weight = "bold"
            underline_color = COLORS["info"] # Blue/Cyan for active
        elif self.is_completed:
            text_color = COLORS["success"]
            font_weight = "normal"
            underline_color = "transparent"
        else:
            text_color = COLORS["text_muted"]
            font_weight = "normal"
            underline_color = "transparent"
            
        # Main Container Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) # Text area
        self.grid_rowconfigure(1, weight=0) # Underline area
        
        # Text Content
        # Format: "1. Title"
        display_text = f"{self.step_number}. {self.title}"
        
        self.title_label = ctk.CTkLabel(
            self,
            text=display_text,
            font=(FONTS["family"], FONTS["body_size"], font_weight),
            text_color=text_color
        )
        self.title_label.grid(row=0, column=0, padx=SPACING["md"], pady=(2, 2))
        
        # Underline Bar (Active Only)
        if self.is_active:
            self.underline = ctk.CTkFrame(
                self,
                width=0, # Will expand with sticky=ew
                height=3,
                fg_color=underline_color,
                corner_radius=2
            )
            self.underline.grid(row=1, column=0, sticky="ew", padx=SPACING["md"])
            
        # Click binding
        if self.on_click:
            self.bind("<Button-1>", lambda e: self.on_click(self.step_number))
            self.title_label.bind("<Button-1>", lambda e: self.on_click(self.step_number))
            
            self.configure(cursor="hand2")
            self.title_label.configure(cursor="hand2")
            if hasattr(self, 'underline'):
                self.underline.bind("<Button-1>", lambda e: self.on_click(self.step_number))
                self.underline.configure(cursor="hand2")


class HorizontalStepper(ctk.CTkFrame):
    """
    Horizontal stepper navigation component.
    """
    def __init__(
        self,
        master,
        steps: List[str],
        current_step: int = 1,
        on_step_change: Optional[Callable[[int], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.steps = steps
        self.current_step = current_step
        self.on_step_change = on_step_change
        self.completed_steps = set()
        self.step_descriptions = {} # Ignored but kept for interface compatibility
        
        self._refresh()
        
    def _refresh(self):
        # Clear existing
        for widget in self.winfo_children():
            widget.destroy()
            
        # Centering container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(expand=True, anchor="center")
        
        for i, title in enumerate(self.steps, 1):
            is_active = (i == self.current_step)
            is_completed = (i in self.completed_steps) or (i < self.current_step)
            is_last = (i == len(self.steps))
            
            item = HorizontalStepperItem(
                container,
                step_number=i,
                title=title,
                is_active=is_active,
                is_completed=is_completed,
                is_last=is_last,
                on_click=self._handle_click
            )
            item.pack(side="left")
            
    def _handle_click(self, step_number: int):
        if self.on_step_change:
            self.on_step_change(step_number)
            
    def set_step(self, step_number: int):
        if 1 <= step_number <= len(self.steps):
            self.current_step = step_number
            self._refresh()
            
    def update_step_description(self, step_number: int, description: str):
        # Not used in horizontal layout
        pass
            
    def clear_step_description(self, step_number: int):
        pass
            
    def set_completed_steps(self, steps: List[int]):
        self.completed_steps = set(steps)
        self._refresh()

