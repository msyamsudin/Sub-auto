"""
Settings Dialog for Sub-auto
Modal dialog for application settings.
"""

import customtkinter as ctk
from tkinter import filedialog
from typing import Optional, Callable

from .styles import COLORS, FONTS, SPACING, RADIUS, get_button_style, get_input_style, get_label_style, get_option_menu_style
from .components import CustomTitleBar


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
        # 2. Content (Scrollable)
        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(
            side="top", 
            fill="both", 
            expand=True, 
            padx=SPACING["md"], 
            pady=(0, SPACING["sm"])
        )
        content.grid_columnconfigure(1, weight=1)

        # 3. Footer (Bottom)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(
            side="bottom", 
            fill="x", 
            padx=SPACING["md"], 
            pady=SPACING["md"]
        )
        
        # === Populate Content ===
        row = 0
        
        # API Configuration Section
        api_header = ctk.CTkLabel(
            content, 
            text="🔑 AI Provider Configuration",
            font=(FONTS["family"], FONTS["subheading_size"], "bold"),
            text_color=COLORS["text_primary"]
        )
        api_header.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, SPACING["sm"]))
        row += 1
        
        # Provider Selection
        label_provider = ctk.CTkLabel(content, text="Provider:", **get_label_style("body"))
        label_provider.grid(row=row, column=0, sticky="w", pady=(0, SPACING["sm"]))
        
        # Wrap dropdown in bordered frame
        provider_wrapper = ctk.CTkFrame(
            content,
            fg_color=COLORS["bg_dark"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=RADIUS["md"]
        )
        provider_wrapper.grid(row=row, column=1, sticky="w", pady=(0, SPACING["sm"]), padx=(SPACING["md"], 0))
        
        self.provider_var = ctk.StringVar(value=self.config.provider)
        provider_menu = ctk.CTkOptionMenu(
            provider_wrapper,
            values=["openrouter", "ollama", "groq"],
            variable=self.provider_var,
            command=self._on_provider_change,
            **get_option_menu_style()
        )
        provider_menu.pack(padx=1, pady=1)
        row += 1
        
        # --- OpenRouter Settings Frame ---
        self.openrouter_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.openrouter_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        self.openrouter_frame.grid_columnconfigure(1, weight=1)
        
        gem_row = 0
        label_api = ctk.CTkLabel(self.openrouter_frame, text="OpenRouter Key:", **get_label_style("body"))
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
            text="⟳",
            width=35,
            command=self._validate_openrouter,
            **get_button_style("secondary")
        )
        self.validate_btn.grid(row=0, column=2, padx=(SPACING["sm"], 0))
        
        gem_row += 1
        self.or_status_label = ctk.CTkLabel(
            self.openrouter_frame,
            text="",
            font=(FONTS["family"], FONTS["small_size"], "bold"),
            text_color=COLORS["text_muted"]
        )
        self.or_status_label.grid(row=gem_row, column=1, sticky="w", padx=(SPACING["md"], 0), pady=(0, SPACING["sm"]))
        
        gem_row += 1
        label_model = ctk.CTkLabel(self.openrouter_frame, text="Model:", **get_label_style("body"))
        label_model.grid(row=gem_row, column=0, sticky="nw", pady=(0, SPACING["sm"]))
        
        self.or_model_var = ctk.StringVar(value=self.config.get("openrouter_model", "google/gemini-2.0-flash-exp:free"))
        self.or_available_models = [] # Store models here
        self.or_model_list_expanded = False  # Track list state
        
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
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        self.or_selected_label.pack(side="left", fill="x", expand=True)
        
        self.or_expand_btn = ctk.CTkButton(
            self.or_selected_frame,
            text="▼",
            width=30,
            height=24,
            fg_color="transparent",
            hover_color=COLORS["bg_light"],
            text_color=COLORS["text_secondary"],
            command=self._toggle_model_list
        )
        self.or_expand_btn.pack(side="right")
        
        # Expandable section (hidden by default)
        self.or_expand_section = ctk.CTkFrame(self.or_model_container, fg_color="transparent")
        
        # Search entry
        self.or_model_search = ctk.CTkEntry(
            self.or_expand_section,
            placeholder_text="🔍 Search models...",
            fg_color=COLORS["bg_medium"],
            border_width=0,
            height=30
        )
        self.or_model_search.pack(fill="x", padx=SPACING["xs"], pady=(0, SPACING["xs"]))
        self.or_model_search.bind("<KeyRelease>", self._on_model_search)
        self.or_model_search.bind("<FocusIn>", lambda e: self._expand_model_list())
        
        # Model list (scrollable)
        self.or_model_list = ctk.CTkScrollableFrame(
            self.or_expand_section,
            fg_color="transparent",
            height=120
        )
        self.or_model_list.pack(fill="both", expand=True, padx=SPACING["xs"], pady=(0, SPACING["xs"]))
        
        # Initial message
        self.or_model_placeholder = ctk.CTkLabel(
            self.or_model_list,
            text="Connect to load models",
            **get_label_style("muted")
        )
        self.or_model_placeholder.pack(pady=SPACING["md"])
        
        gem_row += 1
        api_hint = ctk.CTkLabel(
            self.openrouter_frame,
            text="Get a key from: https://openrouter.ai/keys",
            **get_label_style("muted")
        )
        api_hint.grid(row=gem_row, column=0, columnspan=2, sticky="w", pady=(0, SPACING["lg"]))

        # --- Groq Settings Frame ---
        self.groq_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.groq_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        self.groq_frame.grid_columnconfigure(1, weight=1)

        gq_row = 0
        label_gq_api = ctk.CTkLabel(self.groq_frame, text="Groq API Key:", **get_label_style("body"))
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
            text="⟳",
            width=35,
            command=self._validate_groq,
            **get_button_style("secondary")
        )
        self.validate_gq_btn.grid(row=0, column=2, padx=(SPACING["sm"], 0))

        gq_row += 1
        self.groq_status_label = ctk.CTkLabel(
            self.groq_frame,
            text="",
            font=(FONTS["family"], FONTS["small_size"], "bold"),
            text_color=COLORS["text_muted"]
        )
        self.groq_status_label.grid(row=gq_row, column=1, sticky="w", padx=(SPACING["md"], 0), pady=(0, SPACING["sm"]))

        gq_row += 1
        label_gq_model = ctk.CTkLabel(self.groq_frame, text="Model:", **get_label_style("body"))
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
        self.groq_model_menu = ctk.CTkOptionMenu(
            groq_model_wrapper,
            variable=self.groq_model_var,
            values=[self.config.groq_model] if self.config.groq_model else ["llama3-70b-8192"],
            **get_option_menu_style()
        )
        self.groq_model_menu.pack(fill="x", padx=1, pady=1)

        gq_row += 1
        gq_hint = ctk.CTkLabel(
            self.groq_frame,
            text="Get a key from: https://console.groq.com/keys",
            **get_label_style("muted")
        )
        gq_hint.grid(row=gq_row, column=0, columnspan=2, sticky="w", pady=(0, SPACING["lg"]))
        
        # --- OLLAMA Settings Frame ---
        self.ollama_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.ollama_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        self.ollama_frame.grid_columnconfigure(1, weight=1)
        
        ol_row = 0
        label_url = ctk.CTkLabel(self.ollama_frame, text="Base URL:", **get_label_style("body"))
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
            text="⟳",
            width=35,
            command=self._refresh_ollama_models,
            **get_button_style("secondary")
        )
        self.refresh_btn.grid(row=0, column=1)

        self.ollama_status_label = ctk.CTkLabel(
            url_container,
            text="",
            font=(FONTS["family"], FONTS["small_size"], "bold"),
            text_color=COLORS["text_muted"]
        )
        self.ollama_status_label.grid(row=0, column=2, padx=(SPACING["sm"], 0))
            
        ol_row += 1
        label_model = ctk.CTkLabel(self.ollama_frame, text="Model:", **get_label_style("body"))
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
        self.ollama_model_menu = ctk.CTkOptionMenu(
            ollama_model_wrapper,
            variable=self.ollama_model_var,
            values=[self.config.ollama_model] if self.config.ollama_model else ["llama3.2"],
            **get_option_menu_style()
        )
        self.ollama_model_menu.pack(fill="x", padx=1, pady=1)
        
        # Auto-populate models if available
        self._try_populate_ollama_models()
            
        # Increment main row after frames
        row += 1
        
        # Separator
        sep1 = ctk.CTkFrame(content, fg_color=COLORS["border"], height=1)
        sep1.grid(row=row, column=0, columnspan=2, sticky="ew", pady=SPACING["md"])
        row += 1
        
        # Application Settings Section
        app_header = ctk.CTkLabel(
            content, 
            text="📁 Application Settings",
            font=(FONTS["family"], FONTS["subheading_size"], "bold"),
            text_color=COLORS["text_primary"]
        )
        app_header.grid(row=row, column=0, columnspan=2, sticky="w", pady=(SPACING["sm"], SPACING["sm"]))
        row += 1
        
        # MKVToolnix Path
        label1 = ctk.CTkLabel(content, text="MKVToolnix Path:", **get_label_style("body"))
        label1.grid(row=row, column=0, sticky="w", pady=(0, SPACING["sm"]))
        
        row += 1
        path_frame = ctk.CTkFrame(content, fg_color="transparent")
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
        
        # === Populate Footer ===
        save_btn = ctk.CTkButton(
            footer,
            text="Save",
            width=100,
            command=self._save_settings,
            **get_button_style("primary")
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
                self.ollama_model_menu.configure(values=models)
                if self.config.ollama_model in models:
                    self.ollama_model_var.set(self.config.ollama_model)
                elif models:
                    self.ollama_model_var.set(models[0])
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
            # Import locally to avoid circulars if any
            from core.translator import validate_and_save_api_key
            result = validate_and_save_api_key(api_key)
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
            self.or_status_label.configure(text="● Online", text_color=COLORS["success"])
            self._show_toast("Connected to OpenRouter", "success")
            
            # Update models
            if result.available_models:
                self.or_available_models = [m.name for m in result.available_models]
                
                # Update current selection if invalid
                current = self.or_model_var.get()
                if current not in self.or_available_models and self.or_available_models:
                     self.or_model_var.set(self.or_available_models[0])
                     self.or_selected_label.configure(text=self.or_available_models[0])
                else:
                     self.or_selected_label.configure(text=current)
                
                # Expand and populate the model list
                self._expand_model_list()
        else:
            self.or_status_label.configure(text="● Invalid Key", text_color=COLORS["error"])
            self._show_toast(result.message if result else "Validation failed", "error")

    def _on_model_search(self, event):
        """Filter models based on search text."""
        query = self.or_model_search.get().lower()
        filtered = [m for m in self.or_available_models if query in m.lower()]
        self._populate_model_list(filtered)
        
        # Scroll to top
        try:
            self.or_model_list._parent_canvas.yview_moveto(0)
        except Exception:
            pass

    def _populate_model_list(self, models, max_display=50):
        """Populate the inline model list with buttons (optimized)."""
        # Cancel any pending batch loading
        if hasattr(self, '_model_load_job') and self._model_load_job:
            self.after_cancel(self._model_load_job)
            self._model_load_job = None
        
        # Clear existing
        for widget in self.or_model_list.winfo_children():
            widget.destroy()
        
        if not models:
            lbl = ctk.CTkLabel(
                self.or_model_list, 
                text="No models found", 
                **get_label_style("muted")
            )
            lbl.pack(pady=SPACING["md"])
            return
        
        current_model = self.or_model_var.get()
        
        # Limit models to prevent lag (show first N + message)
        display_models = models[:max_display]
        remaining = len(models) - max_display
        
        # Create buttons in batches to avoid freezing
        self._pending_models = list(display_models)
        self._current_model_for_list = current_model
        self._remaining_count = remaining
        self._create_model_buttons_batch()
    
    def _create_model_buttons_batch(self, batch_size=15):
        """Create model buttons in small batches to prevent UI freeze."""
        if not hasattr(self, '_pending_models') or not self._pending_models:
            # Done loading, show remaining count if any
            if hasattr(self, '_remaining_count') and self._remaining_count > 0:
                more_label = ctk.CTkLabel(
                    self.or_model_list,
                    text=f"+ {self._remaining_count} more (use search to filter)",
                    **get_label_style("muted")
                )
                more_label.pack(pady=SPACING["sm"])
            return
        
        # Process a batch
        batch = self._pending_models[:batch_size]
        self._pending_models = self._pending_models[batch_size:]
        current_model = self._current_model_for_list
        
        for model in batch:
            is_selected = model == current_model
            
            btn = ctk.CTkButton(
                self.or_model_list,
                text=model,
                anchor="w",
                fg_color=COLORS["primary"] if is_selected else COLORS["bg_light"],
                text_color=COLORS["bg_dark"] if is_selected else COLORS["text_primary"],
                hover_color=COLORS["primary_hover"] if is_selected else COLORS["border"],
                height=28,
                corner_radius=RADIUS["sm"],
                command=lambda m=model: self._select_model(m)
            )
            btn.pack(fill="x", pady=1, padx=2)
        
        # Schedule next batch
        if self._pending_models:
            self._model_load_job = self.after(5, self._create_model_buttons_batch)

    def _select_model(self, model: str):
        """Handle model selection from inline list."""
        self.or_model_var.set(model)
        self.or_selected_label.configure(text=model)
        
        # Clear search and collapse the list
        self.or_model_search.delete(0, "end")
        self._collapse_model_list()

    def _toggle_model_list(self):
        """Toggle model list expand/collapse."""
        if self.or_model_list_expanded:
            self._collapse_model_list()
        else:
            self._expand_model_list()

    def _expand_model_list(self):
        """Expand the model list."""
        if self.or_model_list_expanded:
            return
        
        self.or_model_list_expanded = True
        self.or_expand_btn.configure(text="▲")
        self.or_expand_section.pack(fill="both", expand=True)
        
        # Populate list if models available
        if self.or_available_models:
            self._populate_model_list(self.or_available_models)

    def _collapse_model_list(self):
        """Collapse the model list."""
        if not self.or_model_list_expanded:
            return
        
        self.or_model_list_expanded = False
        self.or_expand_btn.configure(text="▼")
        self.or_expand_section.pack_forget()

    def _on_ollama_refresh_result(self, success, result, silent):
        """Handle refresh result."""
        if not self.winfo_exists():
            return
            
        self.refresh_btn.configure(state="normal")
        
        if success:
            models = result
            if models:
                self.ollama_model_menu.configure(values=models)
                self.ollama_model_var.set(models[0])
                if not silent:
                    self._show_toast("OLLAMA Connected", "success")
            else:
                if not silent:
                    self._show_toast("Connected but no models found", "warning")
            self.ollama_status_label.configure(text="● Online", text_color=COLORS["success"])
        else:
            if not silent:
                self._show_toast(f"Connection failed: {result}", "error")
            self.ollama_status_label.configure(text="● Offline", text_color=COLORS["error"])

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
                self.groq_model_menu.configure(values=models)
                # If current model not in list, select first
                if self.groq_model_var.get() not in models:
                    self.groq_model_var.set(models[0])
                
                self._show_toast("Groq Connected", "success")
            self.groq_status_label.configure(text="● Online", text_color=COLORS["success"])
        else:
            self.groq_status_label.configure(text="● Error", text_color=COLORS["error"])
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

