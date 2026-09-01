"""
Overlay mixin for the main application window.
Manages the settings/history overlays and their save callbacks.
Combined into SubAutoApp via mixins.
"""

from ..settings import SettingsDialog
from ..history_view import HistoryView
from core.translator import get_api_manager


class OverlayMixin:
    """Settings and history overlay management."""

    def _open_settings(self):
        """Open settings view."""
        self.view_manager.open_settings(
            self.config,
            self._on_settings_save,
            SettingsDialog,
            on_active_prompt_change=self._on_active_prompt_changed
        )
        
    def _on_active_prompt_changed(self, prompt_name: str):
        """Handle active prompt change notification."""
        self.title_bar.set_active_prompt(prompt_name)
        
    def _on_overlay_opened(self, view_type: str):
        """Callback when an overlay is opened."""
        if hasattr(self, 'footer'):
            self.footer.grid_remove()
        
        if view_type == "settings" and self.view_manager.settings_view:
            self.view_manager.settings_view.remove_subs_var.set(self.app_state.remove_old_subs)

    def _on_overlay_closed(self, view_type: str):
        """Callback when an overlay is closed."""
        if hasattr(self, 'footer'):
            self.footer.grid()

    def _open_history(self):
        """Open history view."""
        self.view_manager.open_history(HistoryView)
    
    def _on_settings_save(self, settings: dict):
        """Handle settings save."""
        self.remove_old_subs = settings.get("remove_old_subs", True)
        self._init_mkv_handler()  # Reinitialize with new path
        
        # Sync API validation state
        manager = get_api_manager()
        self.app_state.api_validated = manager.is_configured
        self.app_state.selected_model = manager.selected_model
        
        # If AI settings changed, handle validation sync
        if settings.get("ai_settings_changed", False):
            if not manager.is_configured:
                # Check if we should auto-connect
                if self.config.provider == "ollama" or \
                   (self.config.provider == "openrouter" and self.config.openrouter_api_key) or \
                   (self.config.provider == "groq" and self.config.groq_api_key):
                    # Show connecting status first
                    self.app_state.is_validating = True
                    self.title_bar.set_api_status(False, connecting=True)
                    self._validate_api()
                else:
                    self.toast.info("AI settings updated. Please reconnect.")
            else:
                self.toast.success("Settings updated")
        else:
            self.toast.success("Settings saved")
            
        # Always refresh UI states to ensure title bar and step info are in sync
        self._update_step_states()
