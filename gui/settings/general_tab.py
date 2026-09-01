"""
General settings tab for the settings dialog.
Builds the scrollable General tab and delegates each provider's connection
frame to its own mixin. Combined into SettingsDialog via mixins.
"""

import customtkinter as ctk
from tkinter import filedialog

from ..styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_button_style, get_input_style, get_label_style
)


class GeneralTabMixin:
    """The General tab: provider selection, connection settings, application paths."""

    def _setup_general_tab(self):
        """Setup the General settings tab (existing content)."""
        # Content (Scrollable)
        content = ctk.CTkScrollableFrame(
            self.tabview.tab("General"),
            fg_color="transparent",
            scrollbar_button_color=COLORS["bg_light"],
            scrollbar_button_hover_color=COLORS["border_light"]
        )
        content.pack(
            fill="both",
            expand=True
        )
        content.grid_columnconfigure(1, weight=1)

        # === Populate Content ===
        row = 0

        provider_section = self._create_section_card(
            content,
            row,
            "AI Provider",
            "Choose the provider you want to use for translation."
        )
        row += 1

        self.provider_var = ctk.StringVar(value=self.config.provider)
        label_provider = ctk.CTkLabel(provider_section, text="Provider:", **get_label_style("body"))
        label_provider.grid(row=row, column=0, sticky="nw", pady=(0, SPACING["sm"]))

        self.provider_selector = self._create_provider_selector(provider_section)
        self.provider_selector.grid(row=row, column=1, sticky="ew", pady=(0, SPACING["sm"]), padx=(SPACING["md"], 0))

        connection_section = self._create_section_card(
            content,
            1,
            "Connection",
            "Add credentials, test the connection, then choose an available model."
        )

        # Per-provider connection frames (each owned by its provider mixin)
        self._setup_openrouter_frame(connection_section)
        self._setup_groq_frame(connection_section)
        self._setup_ollama_frame(connection_section)

        app_section = self._create_section_card(
            content,
            2,
            "Application",
            "Set local tools and workspace paths used during processing."
        )
        row = 0

        # MKVToolnix Path
        label1 = ctk.CTkLabel(app_section, text="MKVToolnix Path:", **get_label_style("body"))
        label1.grid(row=row, column=0, sticky="w", pady=(0, SPACING["sm"]))

        row += 1
        path_frame = ctk.CTkFrame(app_section, fg_color="transparent")
        path_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, SPACING["md"]))
        path_frame.grid_columnconfigure(0, weight=1)

        self.mkv_path_entry = ctk.CTkEntry(
            path_frame,
            placeholder_text="C:\\Program Files\\MKVToolNix",
            **get_input_style()
        )
        self.mkv_path_entry.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))
        if self.config.mkvtoolnix_path:
            self.mkv_path_entry.insert(0, self.config.mkvtoolnix_path)

        browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse",
            width=80,
            command=self._browse_mkv_path,
            **get_button_style("secondary")
        )
        browse_btn.grid(row=0, column=1)

        # Remove old subtitles (checkbox hidden but variable kept)
        self.remove_subs_var = ctk.BooleanVar(value=True)

        # Initial state setup
        self._on_provider_change(self.provider_var.get())

        # Auto-fetch OpenRouter models if key exists and provider is OpenRouter
        if self.config.provider == "openrouter" and self.config.openrouter_api_key:
             self.after(500, self._validate_openrouter)
        elif self.config.provider == "ollama":
             self.after(500, lambda: self._refresh_ollama_models(silent=True))
        elif self.config.provider == "groq" and self.config.groq_api_key:
             self.after(500, self._validate_groq)

    def _browse_mkv_path(self):
        """Browse for MKVToolnix folder."""
        path = filedialog.askdirectory(title="Select MKVToolnix Folder")
        if path:
            self.mkv_path_entry.delete(0, "end")
            self.mkv_path_entry.insert(0, path)

    def _on_provider_change(self, choice):
        """Handle provider dropdown change."""
        if choice == "openrouter":
            self.openrouter_frame.grid()
            self.ollama_frame.grid_remove()
            self.groq_frame.grid_remove()
        elif choice == "groq":
            self.openrouter_frame.grid_remove()
            self.ollama_frame.grid_remove()
            self.groq_frame.grid()
        else:
            self.openrouter_frame.grid_remove()
            self.ollama_frame.grid()
            self.groq_frame.grid_remove()
