"""
Settings Dialog for Sub-auto
Modal dialog for application settings.
"""

import customtkinter as ctk
from tkinter import filedialog
from typing import Optional, Callable

from .styles import COLORS, FONTS, SPACING, RADIUS, get_button_style, get_input_style, get_label_style, get_option_menu_style
from .components import CustomTitleBar, ModelSelectorDialog


import threading
from core.translator import get_api_manager

class SettingsDialog(ctk.CTkFrame):
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
        **kwargs
    ):
        super().__init__(parent, fg_color=COLORS["bg_dark"], **kwargs)
        
        self.config = config
        self.on_save = on_save
        self.on_close_callback = on_close
        
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
        from .prompt_settings_tab import PromptSettingsTab
        
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
            prompt_manager=self.prompt_manager
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

    def _open_model_picker(self, models, current_model: str, on_select: Callable[[str], None], title: str):
        if not models:
            self._show_toast("No models available yet. Test the connection first.", "warning")
            return
        ModelSelectorDialog(self, models=models, on_select=on_select, current_model=current_model, title=title)
    
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
        row = 0

        connection_section = self._create_section_card(
            content,
            1,
            "Connection",
            "Add credentials, test the connection, then choose an available model."
        )

        # --- OpenRouter Settings Frame ---
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

        # --- Groq Settings Frame ---
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

        # --- OLLAMA Settings Frame ---
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
        
        row += 1
        
        # Batch Size Setting (Removed - Fixed to 25)
        # label_batch = ctk.CTkLabel(content, text="Batch Size:", **get_label_style("body"))
        # label_batch.grid(row=row, column=0, sticky="w", pady=(0, SPACING["sm"]))
        
        # row += 1
        # batch_frame = ctk.CTkFrame(content, fg_color="transparent")
        # batch_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, SPACING["md"]))
        
        # self.batch_size_entry = ctk.CTkEntry(
        #     batch_frame,
        #     width=80,
        #     **get_input_style()
        # )
        # self.batch_size_entry.pack(side="left")
        # self.batch_size_entry.insert(0, str(self.config.batch_size))
        
        # batch_hint = ctk.CTkLabel(
        #     batch_frame,
        #     text="(lines per request, 1-100)",
        #     **get_label_style("muted")
        # )
        # batch_hint.pack(side="left", padx=SPACING["sm"])
        
        # row += 1
        
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
    
    def _toggle_key_visibility(self):
        """Toggle API key visibility."""
        self.show_key = not self.show_key
        if self.show_key:
            self.api_key_entry.configure(show="")
            self.toggle_key_btn.configure(text="🙈")
        else:
            self.api_key_entry.configure(show="•")
            self.toggle_key_btn.configure(text="👁")

    def _toggle_gq_key_visibility(self):
        """Toggle Groq API key visibility."""
        self.show_gq_key = not self.show_gq_key
        if self.show_gq_key:
            self.groq_api_key_entry.configure(show="")
            self.toggle_gq_key_btn.configure(text="🙈")
        else:
            self.groq_api_key_entry.configure(show="•")
            self.toggle_gq_key_btn.configure(text="👁")
            
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
        
        # Batch Size (Fixed)
        # try:
        #     batch_val = int(self.batch_size_entry.get().strip())
        #     self.config.batch_size = batch_val
        # except ValueError:
        #     pass # Keep previous value if invalid

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
            provider_changed or 
            (new_provider == "openrouter" and api_key_changed) or
            (new_provider == "openrouter" and (api_key_changed or or_model_changed)) or
            (new_provider == "openrouter" and (api_key_changed or or_model_changed)) or
            (new_provider == "ollama" and (ollama_url_changed or ollama_model_changed)) or
            (new_provider == "groq" and (gq_api_key_changed or gq_model_changed))
        )
        
        if self.on_save:
            self.on_save({
                "mkvtoolnix_path": self.config.mkvtoolnix_path,
                "remove_old_subs": self.remove_subs_var.get(),
                "ai_settings_changed": ai_settings_changed,
                "provider": new_provider
            })
        
        self._on_close()
    
    
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
            from core.model_manager import get_api_manager
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

    def _select_groq_model(self, model: str):
        self.groq_model_var.set(model)
        self.groq_selected_label.configure(text=model)

    def _select_ollama_model(self, model: str):
        self.ollama_model_var.set(model)
        self.ollama_selected_label.configure(text=model)

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

    def get_remove_subs(self) -> bool:
        """Get remove old subs setting."""
        return self.remove_subs_var.get()

