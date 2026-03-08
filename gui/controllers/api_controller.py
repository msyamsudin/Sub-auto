import threading
from typing import Callable, Optional, List
from core.translator import get_api_manager
from core.config_manager import ConfigManager
from gui.state.app_state import AppState
from gui.styles import COLORS

class APIController:
    """Controller for managing AI provider connections and model fetching."""
    
    def __init__(self, state: AppState, config: ConfigManager, title_bar: any, toast: any):
        self.state = state
        self.config = config
        self.title_bar = title_bar
        self.toast = toast
        self.model_dropdown = None
        self.model_status = None
        self.validate_btn = None
        self.after_func = None # App's .after() method for thread-safe UI updates
        
    def set_ui_elements(self, dropdown, status, validate_btn, title_bar, after_func):
        self.model_dropdown = dropdown
        self.model_status = status
        self.validate_btn = validate_btn
        self.title_bar = title_bar
        self.after_func = after_func

    def sync_api_state(self):
        """Sync API connection state and model selection."""
        manager = get_api_manager()
        if manager.is_configured:
            self.state.api_validated = True
            self.state.selected_model = manager.selected_model

        if self.state.api_validated:
            display_names = manager.get_model_display_names()
            if display_names and self.model_dropdown:
                self.model_dropdown.configure(values=display_names, state="normal")
                info = manager.get_selected_model_info()
                if info:
                    self.model_dropdown.set(info.short_name)
            
            if self.model_status:
                self.model_status.configure(text="✓ Connected", text_color=COLORS["success"])
            if self.validate_btn:
                self.validate_btn.grid_forget()
        else:
            if self.model_dropdown:
                self.model_dropdown.configure(state="disabled")
            if not self.state.is_validating and self.model_status:
                self.model_status.configure(text="⚠ Not connected", text_color=COLORS["text_muted"])
                if self.model_dropdown:
                    self.model_dropdown.set("Not connected")

        # Update title bar API status
        if not self.state.is_validating:
            display_model = self.state.selected_model
            info = manager.get_selected_model_info()
            if info:
                display_model = info.short_name
            self.title_bar.set_api_status(self.state.api_validated, display_model or "")

    def validate_api(self):
        """Validate AI provider connection in background."""
        if self.validate_btn:
            self.validate_btn.configure(state="disabled", text="...")
        if self.model_status:
            self.model_status.configure(text="Connecting & fetching models...", text_color=COLORS["text_secondary"])
        if self.model_dropdown:
            self.model_dropdown.configure(state="disabled")
        
        self.title_bar.set_api_status(False, connecting=True)
        self.state.is_validating = True
        
        thread = threading.Thread(target=self._do_validate, daemon=True)
        thread.start()

    def _do_validate(self):
        """Internal validation thread worker."""
        try:
            manager = get_api_manager()
            result = manager.validate_connection()
            if self.after_func:
                self.after_func(0, lambda: self._on_validate_result(result))
        except Exception as e:
            if self.after_func:
                self.after_func(0, lambda e=e: self._on_validate_error(str(e)))

    def _on_validate_result(self, result):
        self.state.is_validating = False
        if self.validate_btn:
            self.validate_btn.configure(state="normal", text="Connect")
        
        if result.is_valid:
            self.state.api_validated = True
            models = [m.short_name for m in result.available_models]
            
            if models and self.model_dropdown:
                self.model_dropdown.configure(values=models, state="normal")
                
                configured_model = self._get_configured_model()
                if configured_model and configured_model in models:
                     self.state.selected_model = configured_model
                     self.model_dropdown.set(configured_model)
                else:
                    self._set_default_model(models)
            
            if self.model_status:
                self.model_status.configure(text="✓ Connected", text_color=COLORS["success"])
            if self.validate_btn:
                self.validate_btn.grid_forget()
            self.toast.success("API connected successfully")
        else:
            self.state.api_validated = False
            if self.model_dropdown:
                self.model_dropdown.configure(state="disabled")
            if self.model_status:
                self.model_status.configure(text=result.message, text_color=COLORS["error"])
            if self.validate_btn:
                self.validate_btn.configure(text="Retry")
                # Grid logic should ideally be handled by view or passed in
                # For now keeping it simple
            self.toast.error(result.message)
        
        self.sync_api_state()

    def _on_validate_error(self, error: str):
        self.state.is_validating = False
        self.state.api_validated = False
        if self.validate_btn:
            self.validate_btn.configure(state="normal", text="Connect")
        if self.model_dropdown:
            self.model_dropdown.configure(state="disabled")
        if self.model_status:
            self.model_status.configure(text="Connection failed", text_color=COLORS["error"])
        self.toast.error(f"Validation failed: {error}")
        self.sync_api_state()

    def _get_configured_model(self) -> Optional[str]:
        if self.config.provider == "ollama":
            return self.config.ollama_model
        elif self.config.provider == "openrouter":
            return self.config.openrouter_model
        elif self.config.provider == "groq":
            return self.config.groq_model
        return None

    def _set_default_model(self, models: List[str]):
        for model in models:
            if "flash" in model.lower():
                self.state.selected_model = model
                self.model_dropdown.set(model)
                break
        else:
            self.state.selected_model = models[0]
            self.model_dropdown.set(models[0])
