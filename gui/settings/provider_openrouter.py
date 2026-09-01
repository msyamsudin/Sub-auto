"""
OpenRouter provider frame and validation for the settings dialog.
Combined into SettingsDialog via mixins.
"""

import threading

import customtkinter as ctk

from ..styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_button_style, get_input_style
)
from core.translator import get_api_manager


class OpenRouterMixin:
    """OpenRouter connection frame + key/model validation."""

    def _setup_openrouter_frame(self, connection_section):
        """Build the OpenRouter credentials + model picker frame."""
        self.openrouter_frame = ctk.CTkFrame(connection_section, fg_color="transparent")
        self.openrouter_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.openrouter_frame.grid_columnconfigure(1, weight=1)

        gem_row = 0
        label_api = self._create_field_label(self.openrouter_frame, "OpenRouter Key:")
        label_api.grid(row=gem_row, column=0, sticky="w", pady=(0, SPACING["sm"]))

        api_container = ctk.CTkFrame(self.openrouter_frame, fg_color="transparent")
        api_container.grid(row=gem_row, column=1, sticky="ew", padx=(SPACING["md"], 0))
        api_container.grid_columnconfigure(0, weight=1)

        self.api_key_entry = ctk.CTkEntry(
            api_container,
            placeholder_text="sk-or-...",
            show="•",
            **get_input_style()
        )
        self.api_key_entry.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))
        if self.config.openrouter_api_key:
            self.api_key_entry.insert(0, self.config.openrouter_api_key)

        # Show/hide button
        self.show_key = False
        self.toggle_key_btn = ctk.CTkButton(
            api_container,
            text="👁",
            width=35,
            command=self._toggle_key_visibility,
            **get_button_style("ghost")
        )
        self.toggle_key_btn.grid(row=0, column=1)

        self.validate_btn = ctk.CTkButton(
            api_container,
            text="Test",
            width=72,
            command=self._validate_openrouter,
            **get_button_style("secondary")
        )
        self.validate_btn.grid(row=0, column=2, padx=(SPACING["sm"], 0))

        gem_row += 1
        self.or_status_label = self._create_status_label(self.openrouter_frame)
        self.or_status_label.grid(row=gem_row, column=1, sticky="w", padx=(SPACING["md"], 0), pady=(0, SPACING["sm"]))

        gem_row += 1
        label_model = self._create_field_label(self.openrouter_frame, "Model:")
        label_model.grid(row=gem_row, column=0, sticky="nw", pady=(0, SPACING["sm"]))

        self.or_model_var = ctk.StringVar(value=self.config.get("openrouter_model", "google/gemini-2.0-flash-exp:free"))
        self.or_available_models = []

        # Inline Model Selection Container
        self.or_model_container = ctk.CTkFrame(
            self.openrouter_frame,
            fg_color=COLORS["bg_dark"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=RADIUS["md"]
        )
        self.or_model_container.grid(row=gem_row, column=1, sticky="ew", padx=(SPACING["md"], 0), pady=(0, SPACING["sm"]))
        self.or_model_container.grid_columnconfigure(0, weight=1)

        # Selected model display (visible when collapsed)
        self.or_selected_frame = ctk.CTkFrame(self.or_model_container, fg_color="transparent")
        self.or_selected_frame.pack(fill="x", padx=SPACING["sm"], pady=SPACING["sm"])

        self.or_selected_label = ctk.CTkLabel(
            self.or_selected_frame,
            text=self.or_model_var.get() or "No model selected",
            font=(FONTS["family"], FONTS["body_size"]),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        self.or_selected_label.pack(side="left", fill="x", expand=True)

        self.or_expand_btn = ctk.CTkButton(
            self.or_selected_frame,
            text="Choose",
            width=72,
            height=24,
            command=lambda: self._open_model_picker(
                self.or_available_models,
                self.or_model_var.get(),
                self._select_model,
                "Choose OpenRouter Model"
            ),
            **get_button_style("secondary")
        )
        self.or_expand_btn.pack(side="right")

        gem_row += 1
        api_hint = ctk.CTkLabel(
            self.openrouter_frame,
            text="Get a key from: https://openrouter.ai/keys",
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["text_secondary"]
        )
        api_hint.grid(row=gem_row, column=0, columnspan=2, sticky="w", pady=(0, SPACING["sm"]))

    def _toggle_key_visibility(self):
        """Toggle API key visibility."""
        self.show_key = not self.show_key
        if self.show_key:
            self.api_key_entry.configure(show="")
            self.toggle_key_btn.configure(text="🙈")
        else:
            self.api_key_entry.configure(show="•")
            self.toggle_key_btn.configure(text="👁")

    def _validate_openrouter(self):
        """Validate OpenRouter API Key and fetch models."""
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            self._show_toast("Please enter API Key", "error")
            return

        self.validate_btn.configure(state="disabled")
        self.or_status_label.configure(text="Connecting...", text_color=COLORS["text_secondary"])

        thread = threading.Thread(target=self._do_validate_or, args=(api_key,), daemon=True)
        thread.start()

    def _do_validate_or(self, api_key):
        """Background validation for OpenRouter."""
        try:
            manager = get_api_manager()
            # Temporarily update the key in the shared config object for validation
            manager.config.openrouter_api_key = api_key
            result = manager.validate_connection(provider_name="openrouter")
            self.after(0, lambda: self._on_or_validate_result(result))
        except Exception as e:
            self.after(0, lambda: self._on_or_validate_result(None, str(e)))

    def _on_or_validate_result(self, result, error=None):
        """Handle OpenRouter validation result."""
        if not self.winfo_exists():
            return

        self.validate_btn.configure(state="normal")

        if error:
            self.or_status_label.configure(text="Result: Error", text_color=COLORS["error"])
            self._show_toast(f"Error: {error}", "error")
            return

        if result and result.is_valid:
            self.or_status_label.configure(text="Connected", text_color=COLORS["success"])
            self._show_toast("Connected to OpenRouter", "success")

            # Update models
            if result.available_models:
                self.or_available_models = [m.name for m in result.available_models]

                # Update current selection if invalid
                current = self.or_model_var.get()
                if current not in self.or_available_models and self.or_available_models:
                     self.or_model_var.set(self.or_available_models[0])
                self.or_selected_label.configure(text=self.or_model_var.get())
        else:
            self.or_status_label.configure(text="Invalid key", text_color=COLORS["error"])
            self._show_toast(result.message if result else "Validation failed", "error")

    def _select_model(self, model: str):
        """Handle OpenRouter model selection."""
        self.or_model_var.set(model)
        self.or_selected_label.configure(text=model)
