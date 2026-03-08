from dataclasses import dataclass, field
from typing import Optional, List, Set, Any, Dict
from core.mkv_handler import SubtitleTrack
from core.translator import Translator

@dataclass
class AppState:
    """Central data container for SubAutoApp state."""
    current_file: Optional[str] = None
    subtitle_tracks: List[SubtitleTrack] = field(default_factory=list)
    selected_track_id: Optional[int] = None
    api_validated: bool = False
    selected_model: Optional[str] = None
    is_processing: bool = False
    is_paused: bool = False
    should_cancel: bool = False
    last_summary_data: Optional[Dict[str, Any]] = None
    current_anime_title: Optional[str] = None
    remove_old_subs: bool = True
    is_validating: bool = False
    pending_resume: bool = False
    active_translator: Optional[Translator] = None
    pending_estimates: Set[Any] = field(default_factory=set)
    subtitle_cache: Dict[str, Any] = field(default_factory=dict)
    
    # Payload for review step
    merge_payload: Optional[Dict[str, Any]] = None
