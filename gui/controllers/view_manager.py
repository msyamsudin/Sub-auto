from typing import Optional, Callable
import customtkinter as ctk
from gui.state.app_state import AppState

class ViewManager:
    """Manager for application overlays and dialogs."""
    
    def __init__(self, root: ctk.CTk, state: AppState):
        self.root = root
        self.state = state
        
        self.settings_view = None
        self.history_view = None
        self.summary_view = None
        
        # Callbacks for UI sync
        self.on_overlay_opened = None
        self.on_overlay_closed = None

    def set_callbacks(self, on_open: Callable, on_close: Callable):
        self.on_overlay_opened = on_open
        self.on_overlay_closed = on_close

    def open_settings(self, config, on_save: Callable, SettingsDialogClass):
        """Open settings overlay."""
        if self.settings_view:
            return
            
        self.settings_view = SettingsDialogClass(
            self.root,
            config,
            on_save=on_save,
            on_close=self.close_settings
        )
        
        # Setup layout
        self.settings_view.grid(row=1, column=0, rowspan=2, sticky="nsew")
        self.settings_view.lift()
        
        if self.on_overlay_opened:
            self.on_overlay_opened("settings")
            
        return self.settings_view

    def close_settings(self):
        """Close settings overlay."""
        if self.settings_view:
            self.settings_view.destroy()
            self.settings_view = None
            
        if self.on_overlay_closed:
            self.on_overlay_closed("settings")

    def open_history(self, HistoryViewClass):
        """Open history overlay."""
        if self.history_view:
            return
            
        self.history_view = HistoryViewClass(
            self.root,
            on_close=self.close_history
        )
        
        self.history_view.grid(row=1, column=0, rowspan=2, sticky="nsew")
        self.history_view.lift()
        
        if self.on_overlay_opened:
            self.on_overlay_opened("history")
            
        return self.history_view

    def close_history(self):
        """Close history overlay."""
        if self.history_view:
            self.history_view.destroy()
            self.history_view = None
            
        if self.on_overlay_closed:
            self.on_overlay_closed("history")

    def open_summary(self, summary_data: dict, on_close: Callable, SummaryWindowClass):
        """Open summary overlay."""
        if self.summary_view:
            self.summary_view.destroy()
            
        self.summary_view = SummaryWindowClass(
            self.root,
            **summary_data,
            on_open_folder=lambda: self._open_folder(summary_data.get("output_path")),
            on_close=on_close
        )
        self.summary_view.grid(row=1, column=0, rowspan=2, sticky="nsew")
        self.summary_view.lift()
        return self.summary_view

    def close_summary(self):
        """Close summary overlay."""
        if self.summary_view:
            self.summary_view.destroy()
            self.summary_view = None

    def _open_folder(self, path: Optional[str]):
        """Helper to open folder in OS explorer."""
        if path:
            import os
            from pathlib import Path
            os.startfile(Path(path).parent)
