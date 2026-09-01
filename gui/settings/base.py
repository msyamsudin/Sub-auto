"""
Shared UI helpers and the provider selector for the settings dialog.
Combined into SettingsDialog via mixins; nothing here knows about a specific
provider's fields.
"""

from typing import Optional, Callable

import customtkinter as ctk

from ..styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_button_style, get_label_style
)
from ..components import ModelSelectorDialog


class SettingsHelpersMixin:
    """Small reusable UI helpers used across the settings dialog."""

    def _create_section_card(self, parent, row: int, title: str, description: str):
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_medium"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=RADIUS["lg"]
        )
        card.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, SPACING["md"]))
        card.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["md"], SPACING["sm"]))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=title,
            font=(FONTS["family"], FONTS["subheading_size"], "bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text=description,
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["text_secondary"]
        ).grid(row=1, column=0, sticky="w", pady=(SPACING["xs"], 0))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=1, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, SPACING["lg"]))
        body.grid_columnconfigure(1, weight=1)
        return body

    def _create_field_label(self, parent, text: str):
        return ctk.CTkLabel(parent, text=text, **get_label_style("body"))

    def _create_status_label(self, parent):
        return ctk.CTkLabel(
            parent,
            text="Not connected",
            font=(FONTS["family"], FONTS["small_size"], "bold"),
            text_color=COLORS["text_muted"]
        )

    def _open_model_picker(self, models, current_model: str, on_select: Callable[[str], None], title: str):
        if not models:
            self._show_toast("No models available yet. Test the connection first.", "warning")
            return
        ModelSelectorDialog(self, models=models, on_select=on_select, current_model=current_model, title=title)

    def _show_toast(self, message, type="info"):
        """Show toast message using parent's toast manager if available."""
        # master is likely the App instance
        if hasattr(self.master, "toast"):
             if type == "error":
                 self.master.toast.error(message)
             elif type == "success":
                 self.master.toast.success(message)
             elif type == "warning":
                 self.master.toast.warning(message)
             else:
                 self.master.toast.info(message)
        else:
            print(f"Toast: {message}")


class ProviderSelectorMixin:
    """Card-style provider selector (OpenRouter / Groq / Ollama)."""

    def _create_provider_selector(self, parent):
        selector = ctk.CTkFrame(parent, fg_color="transparent")
        selector.grid_columnconfigure((0, 1, 2), weight=1)

        self.provider_buttons = {}
        provider_meta = [
            ("openrouter", "OpenRouter", "Cloud models"),
            ("groq", "Groq", "Fast hosted inference"),
            ("ollama", "Ollama", "Local runtime"),
        ]

        for col, (value, title, subtitle) in enumerate(provider_meta):
            card = ctk.CTkFrame(
                selector,
                fg_color=COLORS["bg_dark"],
                border_width=1,
                border_color=COLORS["border"],
                corner_radius=RADIUS["md"],
                height=68
            )
            card.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else SPACING["sm"], 0))
            card.grid_propagate(False)
            card.grid_columnconfigure(0, weight=1)

            hitbox = ctk.CTkFrame(
                card,
                fg_color="transparent",
                corner_radius=RADIUS["md"]
            )
            hitbox.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
            hitbox.grid_columnconfigure(0, weight=1)

            title_label = ctk.CTkLabel(
                hitbox,
                text=title,
                font=(FONTS["family"], FONTS["body_size"], "bold"),
                text_color=COLORS["text_primary"]
            )
            title_label.grid(row=0, column=0, sticky="w", padx=SPACING["md"], pady=(SPACING["sm"], 0))

            subtitle_label = ctk.CTkLabel(
                hitbox,
                text=subtitle,
                font=(FONTS["family"], FONTS["small_size"]),
                text_color=COLORS["text_secondary"]
            )
            subtitle_label.grid(row=1, column=0, sticky="w", padx=SPACING["md"], pady=(SPACING["xs"], SPACING["sm"]))

            for widget in [card, hitbox, title_label, subtitle_label]:
                widget.bind("<Button-1>", lambda e, v=value: self._select_provider(v))
                widget.configure(cursor="hand2")

            self.provider_buttons[value] = {
                "card": card,
                "button": hitbox,
                "title": title_label,
                "subtitle": subtitle_label,
            }

        self._refresh_provider_selector()
        return selector

    def _refresh_provider_selector(self):
        current = self.provider_var.get()
        for value, widgets in self.provider_buttons.items():
            is_selected = value == current
            widgets["card"].configure(
                fg_color=COLORS["accent_bg"] if is_selected else COLORS["bg_dark"],
                border_color=COLORS["border_light"] if is_selected else COLORS["border"]
            )
            widgets["button"].configure(
                fg_color=COLORS["bg_light"] if is_selected else "transparent"
            )
            widgets["title"].configure(text_color=COLORS["text_primary"])
            widgets["subtitle"].configure(
                text_color=COLORS["primary_light"] if is_selected else COLORS["text_secondary"]
            )

    def _select_provider(self, provider: str):
        self.provider_var.set(provider)
        self._refresh_provider_selector()
        self._on_provider_change(provider)
