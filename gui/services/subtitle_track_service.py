from typing import List, Optional, Callable
from core.mkv_handler import MKVHandler, SubtitleTrack
from gui.state.app_state import AppState
from gui.styles import COLORS

class SubtitleTrackService:
    """Service for managing subtitle tracks from MKV files."""
    
    def __init__(self, mkv_handler: MKVHandler, state: AppState):
        self.mkv_handler = mkv_handler
        self.state = state
        self.language_mapping = {} # Will be set by app
        
    def set_language_mapping(self, mapping: dict):
        self.language_mapping = mapping

    def load_tracks(self, file_path: str) -> List[SubtitleTrack]:
        """Load and filter subtitle tracks from MKV."""
        if not self.mkv_handler or not file_path:
            return []
            
        tracks = self.mkv_handler.get_subtitle_tracks(file_path)
        # Filter for supported formats
        filtered = [t for t in tracks if t.file_extension in ['.srt', '.ass']]
        self.state.subtitle_tracks = filtered
        self.state.selected_track_id = None
        return filtered

    def handle_track_selection(self, track_id: int, is_selected: bool, track_items: list) -> Optional[int]:
        """Handle logic for track selection/deselection."""
        if is_selected:
            if self.state.selected_track_id == track_id:
                return track_id
            
            # Deselect others
            for item in track_items:
                if item.track_id != track_id:
                    item.deselect()
            
            self.state.selected_track_id = track_id
            return track_id
        else:
            if self.state.selected_track_id == track_id:
                self.state.selected_track_id = None
            return None

    def get_track_language_name(self, track_id: int) -> Optional[str]:
        """Get human-readable language name for a track."""
        track = next((t for t in self.state.subtitle_tracks if t.track_id == track_id), None)
        if track and track.language:
            lang_code = track.language.lower()
            return self.language_mapping.get(lang_code)
        return None
