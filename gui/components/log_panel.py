import customtkinter as ctk
import time
from .styles import (
    COLORS, FONTS, SPACING, RADIUS
)

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
        self.log_text = ctk.CTkTextbox(
            self.content_frame,
            font=(FONTS["mono_family"], 12),
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
