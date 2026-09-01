"""
File/track selection mixin for the main application window.
Handles MKV selection, subtitle track loading, external subtitles, track
selection, and model changes. Combined into SubAutoApp via mixins.
"""

from pathlib import Path
from tkinter import filedialog

from ..styles import COLORS
from core.subtitle_parser import SubtitleParser


class FileSelectionMixin:
    """MKV file and subtitle track selection flow."""

    def _on_file_selected(self, file_path: str):
        """Handle file selection."""
        self.app_state.current_file = file_path
        self.app_state.external_subtitle_path = None
        self._load_subtitle_tracks()
        self._update_step_states()
        
        # Auto-advance to Step 2
        self._on_step_change(2)

    
    def _load_subtitle_tracks(self):
        """Load subtitle tracks from the selected MKV file."""
        if not self.app_state.current_file or not self.mkv_handler:
            return
            
        try:
            filtered_tracks = self.subtitle_service.load_tracks(self.app_state.current_file)
            
            # Update View
            view = self.step_frames[1]
            view.update_tracks(
                tracks=filtered_tracks,
                selected_id=None,
                on_track_select=self._on_track_select
            )
            
            if not filtered_tracks:
                 view.no_tracks_label.configure(text="No supported subtitle tracks found", text_color=COLORS["warning"])
                 view.no_tracks_label.grid()
                 view.show_external_subtitle_option(True, self.app_state.external_subtitle_path)
                 return

            view.show_external_subtitle_option(False)
            
            # Auto-select first track
            if self.track_items:
                self.track_items[0].select()
                
        except Exception as e:
            view = self.step_frames[1]
            view.set_model_status(f"Error: {str(e)}", COLORS["error"])
            view.no_tracks_label.configure(
                text=f"Error: {str(e)}",
                text_color=COLORS["error"]
            )
            view.no_tracks_label.grid()
            self.toast.error(f"Failed to load tracks: {str(e)}")

    def _select_external_subtitle(self):
        """Select and validate an external text subtitle as the translation source."""
        initial_dir = Path(self.app_state.current_file).parent if self.app_state.current_file else None
        subtitle_path = filedialog.askopenfilename(
            title="Select External Subtitle",
            initialdir=str(initial_dir) if initial_dir else None,
            filetypes=[
                ("Supported subtitles", "*.srt *.ass *.ssa"),
                ("SubRip subtitle", "*.srt"),
                ("Advanced SubStation Alpha", "*.ass *.ssa")
            ]
        )
        if not subtitle_path:
            return

        try:
            lines = SubtitleParser().load(subtitle_path)
            if not lines:
                raise ValueError("The subtitle file contains no subtitle entries")
        except Exception as e:
            self.toast.error(f"Invalid subtitle file: {e}")
            return

        self.app_state.external_subtitle_path = subtitle_path
        self.app_state.selected_track_id = -1
        self.step_frames[1].show_external_subtitle_option(True, Path(subtitle_path).name)
        self.toast.success(f"External subtitle selected: {Path(subtitle_path).name}")
        self._update_step_states()
    
    def _on_track_select(self, track_id: int, is_selected: bool):
        """Handle track selection."""
        new_track_id = self.subtitle_service.handle_track_selection(track_id, is_selected, self.track_items)
        if new_track_id is None and not is_selected:
             pass # Track was deselected
            
        # Update source language based on track info
        if self.app_state.selected_track_id is not None:
            lang_name = self.subtitle_service.get_track_language_name(self.app_state.selected_track_id)
            if lang_name:
                # Ensure the option exists in the dropdown
                current_options = self.source_lang_row.input.cget("values")
                if lang_name not in current_options:
                    new_options = list(current_options)
                    # Insert before "Auto-detect" if it exists, otherwise append
                    if "Auto-detect" in new_options:
                        new_options.insert(new_options.index("Auto-detect"), lang_name)
                    else:
                        new_options.append(lang_name)
                    self.source_lang_row.input.configure(values=new_options)
                
                self.source_lang_row.set_value(lang_name)
                self.logger.info(f"🌐 Auto-selected source language: {lang_name} (from track {self.app_state.selected_track_id})")

        self._update_step_states()
    
    def _on_model_change(self, model: str):
        """Handle model selection change."""
        self.app_state.selected_model = model
        self._update_step_states()
    
    def _select_track_by_id(self, track_id: int):
        """Select track by ID."""
        for item in self.track_items:
            if item.track_id == track_id:
                item.select()
                self.app_state.selected_track_id = track_id
                self._update_step_states()
                break
