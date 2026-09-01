"""
Groq provider frame and validation for the settings dialog.
Combined into SettingsDialog via mixins.
"""

import threading

import customtkinter as ctk

from ..styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_button_style, get_input_style
)
from core.translator import get_api_manager


class GroqMixin:
    """Groq connection frame + key/model validation."""

    def _setup_groq_frame(self, connection_section):
        """Build the Groq credentials + model picker frame."""
        self.groq_frame = ctk.CTkFrame(connection_section, fg_color="transparent")
        self.groq_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.groq_frame.grid_columnconfigure(1, weight=1)

        gq_row = 0
        label_gq_api = self._create_field_label(self.groq_frame, "Groq API Key:")
        label_gq_api.grid(row=gq_row, column=0, sticky="w", pady=(0, SPACING["sm"]))

        gq_api_container = ctk.CTkFrame(self.groq_frame, fg_color="transparent")
        gq_api_container.grid(row=gq_row, column=1, sticky="ew", padx=(SPACING["md"], 0))
        gq_api_container.grid_columnconfigure(0, weight=1)

        self.groq_api_key_entry = ctk.CTkEntry(
            gq_api_container,
            placeholder_text="gsk_...",
            show="•",
            **get_input_style()
        )
        self.groq_api_key_entry.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))
        if self.config.groq_api_key:
            self.groq_api_key_entry.insert(0, self.config.groq_api_key)

        # Show/hide button Groq
        self.show_gq_key = False
        self.toggle_gq_key_btn = ctk.CTkButton(
            gq_api_container,
            text="👁",
            width=35,
            command=self._toggle_gq_key_visibility,
            **get_button_style("ghost")
        )
        self.toggle_gq_key_btn.grid(row=0, column=1)

        self.validate_gq_btn = ctk.CTkButton(
            gq_api_container,
            text="Test",
            width=72,
            command=self._validate_groq,
            **get_button_style("secondary")
        )
        self.validate_gq_btn.grid(row=0, column=2, padx=(SPACING["sm"], 0))

        gq_row += 1
        self.groq_status_label = self._create_status_label(self.groq_frame)
        self.groq_status_label.grid(row=gq_row, column=1, sticky="w", padx=(SPACING["md"], 0), pady=(0, SPACING["sm"]))

        gq_row += 1
        label_gq_model = self._create_field_label(self.groq_frame, "Model:")
        label_gq_model.grid(row=gq_row, column=0, sticky="w", pady=(SPACING["sm"], SPACING["sm"]))

        # Wrap dropdown in bordered frame
        groq_model_wrapper = ctk.CTkFrame(
            self.groq_frame,
            fg_color=COLORS["bg_dark"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=RADIUS["md"]
        )
        groq_model_wrapper.grid(row=gq_row, column=1, sticky="ew", padx=(SPACING["md"], 0), pady=(SPACING["sm"], SPACING["sm"]))

        self.groq_model_var = ctk.StringVar(value=self.config.groq_model or "llama3-70b-8192")
        self.groq_model_values = [self.config.groq_model] if self.config.groq_model else ["llama3-70b-8192"]
        self.groq_selected_frame = ctk.CTkFrame(groq_model_wrapper, fg_color="transparent")
        self.groq_selected_frame.pack(fill="x", padx=SPACING["sm"], pady=SPACING["sm"])
        self.groq_selected_label = ctk.CTkLabel(
            self.groq_selected_frame,
            text=self.groq_model_var.get(),
            font=(FONTS["family"], FONTS["body_size"]),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        self.groq_selected_label.pack(side="left", fill="x", expand=True)
        self.groq_choose_btn = ctk.CTkButton(
            self.groq_selected_frame,
            text="Choose",
            width=72,
            command=lambda: self._open_model_picker(
                self.groq_model_values,
                self.groq_model_var.get(),
                self._select_groq_model,
                "Choose Groq Model"
            ),
            **get_button_style("secondary")
        )
        self.groq_choose_btn.pack(side="right")

        gq_row += 1
        gq_hint = ctk.CTkLabel(
            self.groq_frame,
            text="Get a key from: https://console.groq.com/keys",
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["text_secondary"]
        )
        gq_hint.grid(row=gq_row, column=0, columnspan=2, sticky="w", pady=(0, SPACING["sm"]))

    def _toggle_gq_key_visibility(self):
        """Toggle Groq API key visibility."""
        self.show_gq_key = not self.show_gq_key
        if self.show_gq_key:
            self.groq_api_key_entry.configure(show="")
            self.toggle_gq_key_btn.configure(text="🙈")
        else:
            self.groq_api_key_entry.configure(show="•")
            self.toggle_gq_key_btn.configure(text="👁")

    def _validate_groq(self):
        """Validate Groq API Key and fetch models."""
        api_key = self.groq_api_key_entry.get().strip()
        if not api_key:
            self._show_toast("Please enter Groq API Key", "error")
            return

        self.validate_gq_btn.configure(state="disabled")
        self.groq_status_label.configure(text="Connecting...", text_color=COLORS["text_secondary"])

        thread = threading.Thread(target=self._do_validate_groq, args=(api_key,), daemon=True)
        thread.start()

    def _do_validate_groq(self, api_key):
        """Background validation for Groq."""
        try:
            manager = get_api_manager()
            # Temporarily update the key in the shared config object for validation
            manager.config.groq_api_key = api_key
            result = manager.validate_connection(provider_name="groq")

            if result.is_valid:
                model_names = [m.name for m in result.available_models]
                self.after(0, lambda: self._on_groq_validate_result(True, model_names))
            else:
                self.after(0, lambda: self._on_groq_validate_result(False, result.message))
        except Exception as e:
            self.after(0, lambda: self._on_groq_validate_result(False, str(e)))

    def _on_groq_validate_result(self, success, result):
        """Handle Groq validation result."""
        if not self.winfo_exists():
            return

        self.validate_gq_btn.configure(state="normal")

        if success:
            models = result
            if models:
                self.groq_model_values = models
                # If current model not in list, select first
                if self.groq_model_var.get() not in models:
                    self.groq_model_var.set(models[0])
                self.groq_selected_label.configure(text=self.groq_model_var.get())

                self._show_toast("Groq Connected", "success")
            self.groq_status_label.configure(text="Connected", text_color=COLORS["success"])
        else:
            self.groq_status_label.configure(text="Error", text_color=COLORS["error"])
            self._show_toast(f"Error: {result}", "error")

    def _select_groq_model(self, model: str):
        self.groq_model_var.set(model)
        self.groq_selected_label.configure(text=model)
