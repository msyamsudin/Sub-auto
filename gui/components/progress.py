import customtkinter as ctk
from typing import Optional, Callable
from .styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_frame_style, get_label_style
)

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
        # Try to get actual width if not stored
        if self._current_width <= 1:
            self.update_idletasks() # Ensure layout is updated
            self._current_width = self.winfo_width()

        if self._current_width <= 1:
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
        if self._segments_count <= 0:
            self._draw()
            
        if self._segments_count <= 0:
            return

        target_active = int(self.progress * self._segments_count)
        
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
        target_idx = self._active_count - 1
        tag = f"seg_{target_idx}"
        
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
        c1 = c1.lstrip('#')
        c2 = c2.lstrip('#')
        
        r1, g1, b1 = tuple(int(c1[i:i+2], 16) for i in (0, 2, 4))
        r2, g2, b2 = tuple(int(c2[i:i+2], 16) for i in (0, 2, 4))
        
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
        self.status_label.configure(text=status)
    
    def stop_indeterminate(self):
        """Stop indeterminate mode."""
        pass
    
    def reset(self):
        """Reset progress panel."""
        self.progress_bar.set(0)
        self.status_label.configure(text="Ready")
        self.detail_label.configure(text="")
    
    def set_success(self, message: str = "Complete!"):
        """Show success state."""
        self.progress_bar.set(1)
        self.progress_bar.configure(progress_color=COLORS["success"])
        self.status_label.configure(text=message, text_color=COLORS["success"])
    
    def set_error(self, message: str = "Error occurred"):
        """Show error state."""
        self.progress_bar.configure(progress_color=COLORS["error"])
        self.status_label.configure(text=message, text_color=COLORS["error"])
