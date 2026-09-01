"""
Ollama provider frame and validation for the settings dialog.
Combined into SettingsDialog via mixins.
"""

import threading

import customtkinter as ctk

from ..styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_button_style, get_input_style, get_label_style
)
from core.translator import get_api_manager


class OllamaMixin:
    """Ollama connection frame + URL/model refresh."""

    def _setup_ollama_frame(self, connection_section):
        """Build the Ollama credentials + model picker frame."""
        self.ollama_frame = ctk.CTkFrame(connection_section, fg_color="transparent")
        self.ollama_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.ollama_frame.grid_columnconfigure(1, weight=1)

        ol_row = 0
        label_url = self._create_field_label(self.ollama_frame, "Base URL:")
        label_url.grid(row=ol_row, column=0, sticky="w", pady=(0, SPACING["sm"]))

        # URL Container with Refresh Button
        url_container = ctk.CTkFrame(self.ollama_frame, fg_color="transparent")
        url_container.grid(row=ol_row, column=1, sticky="ew", padx=(SPACING["md"], 0))
        url_container.grid_columnconfigure(0, weight=1)

        self.ollama_url_entry = ctk.CTkEntry(
            url_container,
            placeholder_text="http://localhost:11434",
            **get_input_style()
        )
        self.ollama_url_entry.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))
        if self.config.ollama_base_url:
            self.ollama_url_entry.insert(0, self.config.ollama_base_url)

        self.refresh_btn = ctk.CTkButton(
            url_container,
            text="Test",
            width=72,
            command=self._refresh_ollama_models,
            **get_button_style("secondary")
        )
        self.refresh_btn.grid(row=0, column=1)

        self.ollama_status_label = self._create_status_label(url_container)
        self.ollama_status_label.grid(row=0, column=2, padx=(SPACING["sm"], 0))

        ol_row += 1
        label_model = self._create_field_label(self.ollama_frame, "Model:")
        label_model.grid(row=ol_row, column=0, sticky="w", pady=(SPACING["sm"], SPACING["sm"]))

        # Wrap dropdown in bordered frame
        ollama_model_wrapper = ctk.CTkFrame(
            self.ollama_frame,
            fg_color=COLORS["bg_dark"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=RADIUS["md"]
        )
        ollama_model_wrapper.grid(row=ol_row, column=1, sticky="ew", padx=(SPACING["md"], 0), pady=(SPACING["sm"], SPACING["sm"]))

        self.ollama_model_var = ctk.StringVar(value=self.config.ollama_model or "llama3.2")
        self.ollama_model_values = [self.config.ollama_model] if self.config.ollama_model else ["llama3.2"]
        self.ollama_selected_frame = ctk.CTkFrame(ollama_model_wrapper, fg_color="transparent")
        self.ollama_selected_frame.pack(fill="x", padx=SPACING["sm"], pady=SPACING["sm"])
        self.ollama_selected_label = ctk.CTkLabel(
            self.ollama_selected_frame,
            text=self.ollama_model_var.get(),
            font=(FONTS["family"], FONTS["body_size"]),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        self.ollama_selected_label.pack(side="left", fill="x", expand=True)
        self.ollama_choose_btn = ctk.CTkButton(
            self.ollama_selected_frame,
            text="Choose",
            width=72,
            command=lambda: self._open_model_picker(
                self.ollama_model_values,
                self.ollama_model_var.get(),
                self._select_ollama_model,
                "Choose Ollama Model"
            ),
            **get_button_style("secondary")
        )
        self.ollama_choose_btn.pack(side="right")

        # Auto-populate models if available
        self._try_populate_ollama_models()

    def _try_populate_ollama_models(self):
        """Try to populate models from cache or trigger silent refresh."""
        if not self.config.ollama_base_url:
            return

        # Try cache first
        manager = get_api_manager()
        # Only use cache if it matches current provider config (OLLAMA)
        if manager.available_models and any(m.provider == "OLLAMA" for m in manager.available_models):
            models = [m.name for m in manager.available_models if m.provider == "OLLAMA"]
            if models:
                self.ollama_model_values = models
                if self.config.ollama_model in models:
                    self.ollama_model_var.set(self.config.ollama_model)
                elif models:
                    self.ollama_model_var.set(models[0])
                self.ollama_selected_label.configure(text=self.ollama_model_var.get())
                return

        # If no cache, trigger silent refresh
        self._refresh_ollama_models(silent=True)

    def _refresh_ollama_models(self, silent=False):
        """Refresh OLLAMA models list."""
        url = self.ollama_url_entry.get().strip()
        if not url:
            if not silent:
                self._show_toast("Please enter OLLAMA URL", "error")
            return

        self.refresh_btn.configure(state="disabled")
        self.ollama_status_label.configure(text="Connecting...", text_color=COLORS["text_secondary"])

        # Run in background
        thread = threading.Thread(target=self._do_refresh_ollama, args=(url, silent), daemon=True)
        thread.start()

    def _do_refresh_ollama(self, url, silent):
        """Perform OLLAMA refresh in background."""
        try:
            manager = get_api_manager()
            # Update the URL in the shared config object for validation
            manager.config.ollama_base_url = url
            # Pass provider name to validate without permanently overriding config yet
            result = manager.validate_connection(provider_name="ollama")

            if result.is_valid:
                model_names = [m.name for m in result.available_models]
                self.after(0, lambda: self._on_ollama_refresh_result(True, model_names, silent))
            else:
                self.after(0, lambda: self._on_ollama_refresh_result(False, result.message, silent))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda err=error_msg: self._on_ollama_refresh_result(False, err, silent))

    def _on_ollama_refresh_result(self, success, result, silent):
        """Handle refresh result."""
        if not self.winfo_exists():
            return

        self.refresh_btn.configure(state="normal")

        if success:
            models = result
            if models:
                self.ollama_model_values = models
                self.ollama_model_var.set(models[0])
                self.ollama_selected_label.configure(text=self.ollama_model_var.get())
                if not silent:
                    self._show_toast("OLLAMA Connected", "success")
            else:
                if not silent:
                    self._show_toast("Connected but no models found", "warning")
            self.ollama_status_label.configure(text="Connected", text_color=COLORS["success"])
        else:
            if not silent:
                self._show_toast(f"Connection failed: {result}", "error")
            self.ollama_status_label.configure(text="Offline", text_color=COLORS["error"])

    def _select_ollama_model(self, model: str):
        self.ollama_model_var.set(model)
        self.ollama_selected_label.configure(text=model)
