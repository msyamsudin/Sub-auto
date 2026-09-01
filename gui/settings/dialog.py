"""
Settings Dialog for Sub-auto.
Modal dialog for application settings, composed from focused mixins:
general tab layout, per-provider connection frames, and shared UI helpers.
"""

from typing import Optional, Callable

import customtkinter as ctk

from ..styles import COLORS, FONTS, SPACING, RADIUS, get_button_style
from core.translator import get_api_manager

from .base import SettingsHelpersMixin, ProviderSelectorMixin
from .general_tab import GeneralTabMixin
from .provider_openrouter import OpenRouterMixin
from .provider_groq import GroqMixin
from .provider_ollama import OllamaMixin


class SettingsDialog(
    GeneralTabMixin,
    OpenRouterMixin,
    GroqMixin,
    OllamaMixin,
    ProviderSelectorMixin,
    SettingsHelpersMixin,
    ctk.CTkFrame
):
    """
    Settings view (embedded) for application settings.
    Contains settings that are not frequently changed.
    """

    def __init__(
        self,
        parent,
        config,  # ConfigManager instance
        on_save: Optional[Callable] = None,
        on_close: Optional[Callable] = None,
        on_active_prompt_change: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(parent, fg_color=COLORS["bg_dark"], **kwargs)

        self.config = config
        self.on_save = on_save
        self.on_close_callback = on_close
        self.on_active_prompt_change = on_active_prompt_change

        self._setup_ui()

    def _on_close(self):
        """Handle close button click."""
        if self.on_close_callback:
            self.on_close_callback()
        else:
            self.destroy()

    def _setup_ui(self):
        # Import PromptManager and tab
        from core.prompt_manager import PromptManager
        from ..prompt_settings import PromptSettingsTab

        # Create tabview
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=COLORS["bg_medium"],
            segmented_button_fg_color=COLORS["bg_light"],
            segmented_button_selected_color=COLORS["accent_bg"],
            segmented_button_selected_hover_color=COLORS["border_light"],
            segmented_button_unselected_color=COLORS["bg_medium"],
            segmented_button_unselected_hover_color=COLORS["bg_light"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"]
        )
        self.tabview.pack(
            side="top",
            fill="both",
            expand=True,
            padx=SPACING["md"],
            pady=(SPACING["md"], SPACING["sm"])
        )

        # Add tabs
        self.tabview.add("General")
        self.tabview.add("Prompts")

        # Setup General tab (existing settings)
        self._setup_general_tab()

        # Setup Prompts tab
        self.prompt_manager = PromptManager()
        self.prompt_tab = PromptSettingsTab(
            self.tabview.tab("Prompts"),
            prompt_manager=self.prompt_manager,
            on_active_prompt_change=self.on_active_prompt_change
        )
        self.prompt_tab.pack(fill="both", expand=True)

        # Footer (Bottom)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(
            side="bottom",
            fill="x",
            padx=SPACING["md"],
            pady=SPACING["md"]
        )

        # Save and Cancel buttons
        save_btn = ctk.CTkButton(
            footer,
            text="Save Changes",
            width=100,
            command=self._save_settings,
            **get_button_style("secondary")
        )
        save_btn.pack(side="right", padx=SPACING["sm"])

        cancel_btn = ctk.CTkButton(
            footer,
            text="Cancel",
            width=100,
            command=self._on_close,
            **get_button_style("secondary")
        )
        cancel_btn.pack(side="right", padx=SPACING["sm"])

    def _save_settings(self):
        """Save settings and close."""
        # Provider
        new_provider = self.provider_var.get()
        provider_changed = new_provider != self.config.provider
        self.config.provider = new_provider

        # OpenRouter
        new_api_key = self.api_key_entry.get().strip()
        api_key_changed = new_api_key != (self.config.openrouter_api_key or "")
        if new_api_key:
            self.config.openrouter_api_key = new_api_key

        new_or_model = self.or_model_var.get()
        or_model_changed = new_or_model != self.config.openrouter_model
        self.config.openrouter_model = new_or_model

        # OLLAMA
        new_ollama_url = self.ollama_url_entry.get().strip()
        ollama_url_changed = new_ollama_url != self.config.ollama_base_url
        self.config.ollama_base_url = new_ollama_url

        new_ollama_model = self.ollama_model_var.get()
        ollama_model_changed = new_ollama_model != self.config.ollama_model
        self.config.ollama_model = new_ollama_model

        # Groq
        new_gq_api_key = self.groq_api_key_entry.get().strip()
        gq_api_key_changed = new_gq_api_key != (self.config.groq_api_key or "")
        if new_gq_api_key:
            self.config.groq_api_key = new_gq_api_key

        new_gq_model = self.groq_model_var.get()
        gq_model_changed = new_gq_model != self.config.groq_model
        self.config.groq_model = new_gq_model

        # MKV
        self.config.mkvtoolnix_path = self.mkv_path_entry.get().strip()

        self.config.save()

        # Update ModelManager state so app.py picks it up immediately
        manager = get_api_manager()
        manager.configure(new_provider)
        if new_provider == "openrouter":
            manager.select_model(new_or_model)
        elif new_provider == "ollama":
            manager.select_model(new_ollama_model)
        elif new_provider == "groq":
            manager.select_model(new_gq_model)

        # Notify if AI settings changed
        ai_settings_changed = (
            provider_changed
            or (new_provider == "openrouter" and (api_key_changed or or_model_changed))
            or (new_provider == "ollama" and (ollama_url_changed or ollama_model_changed))
            or (new_provider == "groq" and (gq_api_key_changed or gq_model_changed))
        )

        if self.on_save:
            self.on_save({
                "mkvtoolnix_path": self.config.mkvtoolnix_path,
                "remove_old_subs": self.remove_subs_var.get(),
                "ai_settings_changed": ai_settings_changed,
                "provider": new_provider
            })

        self._on_close()

    def get_remove_subs(self) -> bool:
        """Get remove old subs setting."""
        return self.remove_subs_var.get()
