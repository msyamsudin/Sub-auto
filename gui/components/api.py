import customtkinter as ctk
from typing import Optional, Callable, List
from .styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_button_style, get_input_style, get_label_style
)

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
                fg_color=COLORS["accent_bg"] if is_selected else COLORS["bg_light"],
                text_color=COLORS["text_primary"],
                hover_color=COLORS["border_light"] if is_selected else COLORS["border"],
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

    def _on_select(self, model: str):
        if self.on_select_callback:
            self.on_select_callback(model)
        self.destroy()


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
        from .base import StatusBadge
        super().__init__(master, **get_frame_style("card" if show_header else "transparent"), **kwargs)
        
        self.on_validated = on_validated
        self.on_model_changed = on_model_changed
        self.show_header = show_header
        self.is_validated = False
        self.available_models: List[str] = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the API key panel UI."""
        from .base import StatusBadge
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
            from core.translator import get_api_manager
            manager = get_api_manager()
            manager.config.openrouter_api_key = api_key
            manager.config.provider = "openrouter"
            result = manager.validate_connection()
            
            # Update UI on main thread
            self.after(0, lambda: self._handle_validation_result(result))
        except Exception as e:
            self.after(0, lambda e=e: self._handle_validation_error(str(e)))
    
    def _handle_validation_result(self, result):
        """Handle validation result on main thread."""
        self.validate_btn.configure(state="normal", text="Validate")
        
        if result.is_valid:
            self.is_validated = True
            self.available_models = [m.short_name for m in result.available_models]
            
            # Update UI
            self.status_badge.set_text("✓ Validated")
            self.status_badge.set_variant("success")
            self._set_status(result.message, "success")
            
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
