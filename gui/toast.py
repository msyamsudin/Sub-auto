"""
Toast Notification Component for Sub-auto
Non-blocking notification messages.
"""

import customtkinter as ctk
from typing import Optional, Callable

from .styles import COLORS, FONTS, SPACING, RADIUS


class Toast(ctk.CTkFrame):
    """
    A toast notification that appears at the bottom of the window.
    Auto-dismisses after a timeout.
    """
    
    def __init__(
        self,
        master,
        message: str,
        variant: str = "info",  # info, success, warning, error
        duration: int = 5000,   # ms before auto-dismiss
        action_text: Optional[str] = None,
        on_action: Optional[Callable] = None,
        on_dismiss: Optional[Callable] = None,
        **kwargs
    ):
        # Get colors based on variant
        color_map = {
            "info": (COLORS["info"], COLORS["info_bg"]),
            "success": (COLORS["success"], COLORS["success_bg"]),
            "warning": (COLORS["warning"], COLORS["warning_bg"]),
            "error": (COLORS["error"], COLORS["error_bg"]),
        }
        
        icon_map = {
            "info": "ℹ️",
            "success": "✓",
            "warning": "⚠",
            "error": "✕",
        }
        
        accent_color, bg_color = color_map.get(variant, color_map["info"])
        icon = icon_map.get(variant, "ℹ️")
        
        super().__init__(
            master,
            fg_color=bg_color,
            corner_radius=RADIUS["md"],
            border_width=1,
            border_color=accent_color,
            **kwargs
        )
        
        self.on_dismiss = on_dismiss
        self.duration = duration
        self._dismiss_id = None
        
        self._setup_ui(message, icon, accent_color, action_text, on_action)
        
        # Auto-dismiss
        if duration > 0:
            self._dismiss_id = self.after(duration, self.dismiss)
    
    def _setup_ui(
        self,
        message: str,
        icon: str,
        accent_color: str,
        action_text: Optional[str],
        on_action: Optional[Callable]
    ):
        """Setup toast UI."""
        self.grid_columnconfigure(1, weight=1)
        
        # Icon
        icon_label = ctk.CTkLabel(
            self,
            text=icon,
            font=(FONTS["family"], 16),
            text_color=accent_color,
            width=30
        )
        icon_label.grid(row=0, column=0, padx=(SPACING["md"], 0), pady=SPACING["md"])
        
        # Message
        msg_label = ctk.CTkLabel(
            self,
            text=message,
            font=(FONTS["family"], FONTS["body_size"]),
            text_color=COLORS["text_primary"],
            anchor="w",
            wraplength=400
        )
        msg_label.grid(row=0, column=1, sticky="w", padx=SPACING["sm"], pady=SPACING["md"])
        
        # Action button (optional)
        if action_text and on_action:
            action_btn = ctk.CTkButton(
                self,
                text=action_text,
                width=80,
                height=28,
                fg_color="transparent",
                hover_color=COLORS["bg_light"],
                text_color=accent_color,
                corner_radius=RADIUS["sm"],
                command=on_action
            )
            action_btn.grid(row=0, column=2, padx=SPACING["sm"])
        
        # Dismiss button
        dismiss_btn = ctk.CTkButton(
            self,
            text="✕",
            width=28,
            height=28,
            fg_color="transparent",
            hover_color=COLORS["bg_light"],
            text_color=COLORS["text_muted"],
            corner_radius=RADIUS["sm"],
            command=self.dismiss
        )
        dismiss_btn.grid(row=0, column=3, padx=(0, SPACING["sm"]))
    
    def dismiss(self):
        """Dismiss the toast."""
        if self._dismiss_id:
            self.after_cancel(self._dismiss_id)
        
        if self.on_dismiss:
            self.on_dismiss(self)
        
        self.destroy()


class ToastManager:
    """
    Manages toast notifications for an application.
    Shows toasts in a stack at the bottom of the window.
    """
    
    def __init__(self, parent):
        self.parent = parent
        self.toasts = []
        self.max_toasts = 3
        
        # Container for toasts
        self.container = ctk.CTkFrame(parent, fg_color="transparent")
        # Initially hidden
        # self.container.place(relx=0.5, rely=1.0, anchor="s", y=-20)

    def show(
        self,
        message: str,
        variant: str = "info",
        duration: int = 5000,
        action_text: Optional[str] = None,
        on_action: Optional[Callable] = None
    ):
        """Show a toast notification."""
        # Show container if hidden
        if not self.toasts:
             self.container.place(relx=0.5, rely=1.0, anchor="s", y=-20)
             self.container.lift()

        # Remove oldest if at max
        while len(self.toasts) >= self.max_toasts:
            oldest = self.toasts.pop(0)
            oldest.dismiss()
        
        # Create new toast
        toast = Toast(
            self.container,
            message=message,
            variant=variant,
            duration=duration,
            action_text=action_text,
            on_action=on_action,
            on_dismiss=self._on_toast_dismiss
        )
        toast.pack(pady=(0, SPACING["sm"]))
        
        self.toasts.append(toast)
        
        # Raise container to top
        self.container.lift()
        
        return toast
    
    def _on_toast_dismiss(self, toast):
        """Handle toast dismissal."""
        if toast in self.toasts:
            self.toasts.remove(toast)
            
        # Hide container if empty
        if not self.toasts:
            self.container.place_forget()

    
    def info(self, message: str, **kwargs):
        """Show info toast."""
        return self.show(message, variant="info", **kwargs)
    
    def success(self, message: str, **kwargs):
        """Show success toast."""
        return self.show(message, variant="success", **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Show warning toast."""
        return self.show(message, variant="warning", **kwargs)
    
    def error(self, message: str, **kwargs):
        """Show error toast."""
        return self.show(message, variant="error", duration=8000, **kwargs)
    
    def clear_all(self):
        """Clear all toasts."""
        for toast in self.toasts[:]:
            toast.dismiss()
        self.toasts.clear()
