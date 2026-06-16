import customtkinter as ctk
import ctypes
from typing import Optional, Callable, List
from pathlib import Path
from .styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_button_style, get_label_style
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
        on_history: Optional[Callable] = None,
        show_settings: bool = True,
        show_history: bool = True,
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
        self.on_history = on_history
        self.show_settings = show_settings
        self.show_history = show_history
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
        bar_height = 22 if self.is_dialog else 40
        btn_height = 20 if self.is_dialog else 30
        btn_width = 30 if self.is_dialog else 40
        
        title_font_size = 9 if self.is_dialog else FONTS["body_size"] - 2
        
        self.configure(height=bar_height)
        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)
        
        # Left side - App icon and title
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="w", padx=SPACING["md"], pady=SPACING["sm"])

        if not self.is_dialog:
            self.brand_dot = ctk.CTkFrame(
                left_frame,
                width=12,
                height=12,
                corner_radius=6,
                fg_color=COLORS["accent"]
            )
            self.brand_dot.pack(side="left", padx=(0, SPACING["sm"]))
            self.brand_dot.pack_propagate(False)
        
        # Title
        self.title_label = ctk.CTkLabel(
            left_frame,
            text=self.title_text,
            font=(FONTS["family"], FONTS["heading_size"], "bold"),
            text_color=COLORS["text_primary"]
        )
        self.title_label.pack(side="left")

        if self.version:
            self.version_badge = ctk.CTkLabel(
                left_frame,
                text=self.version,
                font=(FONTS["family"], FONTS["small_size"], "bold"),
                text_color=COLORS["text_secondary"],
                fg_color=COLORS["bg_light"],
                corner_radius=RADIUS["xl"],
                padx=SPACING["sm"],
                pady=2
            )
            self.version_badge.pack(side="left", padx=(SPACING["sm"], 0))
        
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
            self.api_status.pack(side="right", padx=SPACING["md"], pady=(2, 0))

            self.prompt_status = ctk.CTkLabel(
                self.drag_area,
                text="",
                font=(FONTS["family"], FONTS["small_size"]),
                text_color=COLORS["text_muted"]
            )
            self.prompt_status.pack(side="right", padx=SPACING["md"], pady=(2, 0))
        
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
        
        # History button (optional)
        if self.show_history and self.on_history:
            self.history_btn = ctk.CTkButton(
                controls_frame,
                text="⏳",
                width=btn_width,
                height=btn_height,
                corner_radius=0,
                fg_color="transparent",
                hover_color=COLORS["bg_light"],
                text_color=COLORS["text_secondary"],
                command=self.on_history
            )
            self.history_btn.pack(side="left")
        
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
        
        # Maximize button
        if not self.is_dialog:
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
        
        # Bind drag
        for widget in left_frame.winfo_children():
            self._bind_widget_drag(widget)
    
    def _bind_drag_events(self):
        self.bind("<Button-1>", self._on_drag_start)
        self.bind("<B1-Motion>", self._on_drag_motion)
        self.bind("<Double-Button-1>", self._on_double_click)
        
        self.drag_area.bind("<Button-1>", self._on_drag_start)
        self.drag_area.bind("<B1-Motion>", self._on_drag_motion)
        self.drag_area.bind("<Double-Button-1>", self._on_double_click)
    
    def _bind_widget_drag(self, widget):
        widget.bind("<Button-1>", self._on_drag_start)
        widget.bind("<B1-Motion>", self._on_drag_motion)
        widget.bind("<Double-Button-1>", self._on_double_click)
    
    def _on_drag_start(self, event):
        self._drag_x = event.x_root - self.master.winfo_x()
        self._drag_y = event.y_root - self.master.winfo_y()
    
    def _on_drag_motion(self, event):
        if self._is_maximized:
            self._restore_window()
            self._drag_x = self.master.winfo_width() // 2
            self._drag_y = 18
        
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.master.geometry(f"+{x}+{y}")
    
    def _on_double_click(self, event):
        if not self.is_dialog:
            self._toggle_maximize()
    
    def _minimize_window(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.master.winfo_id())
            ctypes.windll.user32.ShowWindow(hwnd, 6) # SW_MINIMIZE
        except Exception:
            try:
                self.master.iconify()
            except Exception:
                pass
    
    def _toggle_maximize(self):
        if self._is_maximized:
            self._restore_window()
        else:
            self._maximize_window()
    
    def _maximize_window(self):
        if not self._is_maximized:
            self._normal_geometry = self.master.geometry()
            screen_width = self.master.winfo_screenwidth()
            screen_height = self.master.winfo_screenheight()
            self.master.geometry(f"{screen_width}x{screen_height - 40}+0+0")
            self._is_maximized = True
            if hasattr(self, 'max_btn'):
                self.max_btn.configure(text="❐")
    
    def _restore_window(self):
        if self._is_maximized and self._normal_geometry:
            self.master.geometry(self._normal_geometry)
            self._is_maximized = False
            if hasattr(self, 'max_btn'):
                self.max_btn.configure(text="□")
    
    def _close_window(self):
        if hasattr(self.master, '_on_close'):
            self.master._on_close()
        else:
            self.master.destroy()
    
    def set_api_status(self, is_valid: bool, model_name: str = "", connecting: bool = False):
        if not hasattr(self, 'api_status'):
            return
        if connecting:
            self.api_status.configure(text="⟳ Fetching models...", text_color=COLORS["text_secondary"])
        elif is_valid:
            text = f"✓ {model_name}" if model_name else "✓ API Ready"
            self.api_status.configure(text=text, text_color=COLORS["success"])
        else:
            self.api_status.configure(text="⚠ API Not Configured", text_color=COLORS["warning"])
            
    def set_active_prompt(self, name: str = ""):
        if not hasattr(self, 'prompt_status'):
            return
        if name:
            self.prompt_status.configure(text=f"📝 {name}", text_color=COLORS["text_secondary"])
        else:
            self.prompt_status.configure(text="📝 No Active Prompt", text_color=COLORS["warning"])
            
    def get_center_frame(self):
        return self.drag_area


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
        content_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content_frame.pack(side="top", fill="both", expand=True, padx=SPACING["lg"], pady=SPACING["md"])
        
        main_container = ctk.CTkFrame(content_frame, fg_color="transparent")
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
