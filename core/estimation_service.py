"""
Token Estimation Service for Sub-auto
Extracts subtitles and estimates API token usage.
"""

import threading
import tempfile
from pathlib import Path
from typing import Callable, Optional, Tuple

from .mkv_handler import MKVHandler
from .subtitle_parser import SubtitleParser
from .logger import get_logger

logger = get_logger()

class EstimationService:
    """Service to estimate token usage for a subtitle track."""
    
    def __init__(self, mkv_handler: MKVHandler):
        self.mkv_handler = mkv_handler
        self._cache = {}
        self._pending = set()
        
    def estimate_tokens_async(
        self,
        mkv_path: str,
        track_id: int,
        on_result: Callable[[int, int], None],
        on_error: Callable[[Exception], None]
    ) -> bool:
        """
        Start token estimation in a background thread.
        Returns True if started, False if already cached or pending.
        Calls on_result(total_chars, line_count) when done.
        """
        cache_key = f"{mkv_path}:{track_id}"
        
        # Check cache
        if cache_key in self._cache:
            total_chars, line_count = self._cache[cache_key]
            # Call synchronously if cached
            on_result(total_chars, line_count)
            return False
            
        # Check if already pending
        if cache_key in self._pending:
            return False
            
        self._pending.add(cache_key)
        
        def _do_estimate():
            try:
                suffix = ".srt.tmp"
                try:
                    tracks = self.mkv_handler.get_subtitle_tracks(mkv_path)
                    track = next((t for t in tracks if t.track_id == track_id), None)
                    if track:
                        suffix = track.file_extension + ".tmp"
                except Exception:
                    pass
                    
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    temp_output = tmp.name
                    
                extracted_path = self.mkv_handler.extract_subtitle(
                    mkv_path,
                    track_id,
                    output_path=temp_output
                )
                
                parser = SubtitleParser()
                lines = parser.load(extracted_path)
                
                # Clean up extracted file
                try:
                    Path(extracted_path).unlink()
                except Exception:
                    pass
                    
                total_chars = sum(len(line.text) for line in lines)
                line_count = len(lines)
                
                self._cache[cache_key] = (total_chars, line_count)
                on_result(total_chars, line_count)
                
            except Exception as e:
                logger.error(f"Estimation failed: {e}")
                on_error(e)
            finally:
                if cache_key in self._pending:
                    self._pending.remove(cache_key)
                    
        # the thread shouldn't keep the app alive
        thread = threading.Thread(target=_do_estimate, daemon=True)
        thread.start()
        
        return True
        
    def calculate_tokens(self, total_chars: int, line_count: int) -> int:
        """Calculate estimated tokens."""
        # Estimate tokens (rough: 4 chars per token)
        estimated_prompt_tokens = (total_chars // 4) + (line_count * 50)  # Text + prompt overhead
        estimated_completion_tokens = total_chars // 4  # Similar output size
        return estimated_prompt_tokens + estimated_completion_tokens

