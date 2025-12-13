"""
Subtitle Parser for Sub-auto
Handles parsing and writing of SRT/ASS subtitle files using pysubs2.
"""

import pysubs2
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SubtitleLine:
    """Represents a single subtitle line with timing and text."""
    index: int
    start_ms: int
    end_ms: int
    text: str
    style: str = "Default"
    
    @property
    def start_time(self) -> str:
        """Get start time in SRT format (HH:MM:SS,mmm)."""
        return self._ms_to_time(self.start_ms)
    
    @property
    def end_time(self) -> str:
        """Get end time in SRT format (HH:MM:SS,mmm)."""
        return self._ms_to_time(self.end_ms)
    
    @property
    def duration_ms(self) -> int:
        """Get duration in milliseconds."""
        return self.end_ms - self.start_ms
    
    @staticmethod
    def _ms_to_time(ms: int) -> str:
        """Convert milliseconds to time string."""
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        milliseconds = ms % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def clean_text(self) -> str:
        """Get text with formatting tags removed (for translation)."""
        import re
        # Remove ASS styling tags like {\i1}, {\b1}, etc.
        text = re.sub(r'\{\\[^}]+\}', '', self.text)
        # Remove HTML-like tags
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()


class SubtitleParser:
    """Parser for subtitle files (SRT, ASS)."""
    
    def __init__(self):
        self.subs: Optional[pysubs2.SSAFile] = None
        self.file_path: Optional[Path] = None
        self.original_format: str = "srt"
    
    def load(self, file_path: str) -> List[SubtitleLine]:
        """
        Load a subtitle file.
        
        Args:
            file_path: Path to the subtitle file (SRT or ASS)
            
        Returns:
            List of SubtitleLine objects
        """
        self.file_path = Path(file_path)
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {file_path}")
        
        # Determine format from extension
        ext = self.file_path.suffix.lower()
        if ext in ['.ass', '.ssa']:
            self.original_format = "ass"
        else:
            self.original_format = "srt"
        
        # Load with pysubs2
        try:
            self.subs = pysubs2.load(str(self.file_path))
        except Exception as e:
            raise RuntimeError(f"Failed to parse subtitle file: {e}")
        
        return self._convert_to_lines()
    
    def _convert_to_lines(self) -> List[SubtitleLine]:
        """Convert pysubs2 events to SubtitleLine objects."""
        if self.subs is None:
            return []
        
        lines = []
        for i, event in enumerate(self.subs):
            if event.type == "Dialogue":
                line = SubtitleLine(
                    index=i,
                    start_ms=event.start,
                    end_ms=event.end,
                    text=event.text,
                    style=event.style
                )
                lines.append(line)
        
        return lines
    
    def get_text_blocks(self, batch_size: int = 25) -> List[List[SubtitleLine]]:
        """
        Get subtitle lines grouped into batches for translation.
        
        Args:
            batch_size: Number of lines per batch
            
        Returns:
            List of batches, each containing SubtitleLine objects
        """
        if self.subs is None:
            return []
        
        lines = self._convert_to_lines()
        batches = []
        
        for i in range(0, len(lines), batch_size):
            batch = lines[i:i + batch_size]
            batches.append(batch)
        
        return batches
    
    def apply_translations(
        self, 
        translations: List[Tuple[int, str]]
    ) -> None:
        """
        Apply translated text to subtitle events.
        
        Args:
            translations: List of (index, translated_text) tuples
        """
        if self.subs is None:
            raise RuntimeError("No subtitle file loaded")
        
        # Create a mapping of index to translated text
        trans_map = {idx: text for idx, text in translations}
        
        # Apply translations
        dialogue_index = 0
        for event in self.subs:
            if event.type == "Dialogue":
                if dialogue_index in trans_map:
                    # Preserve any leading formatting tags
                    original_text = event.text
                    translated = trans_map[dialogue_index]
                    
                    # Try to preserve ASS formatting tags at the start
                    import re
                    leading_tags = re.match(r'^(\{\\[^}]+\})+', original_text)
                    if leading_tags:
                        event.text = leading_tags.group(0) + translated
                    else:
                        event.text = translated
                
                dialogue_index += 1
    
    def save(
        self, 
        output_path: str, 
        format: Optional[str] = None
    ) -> str:
        """
        Save subtitle to file.
        
        Args:
            output_path: Path for the output file
            format: Output format ('srt' or 'ass'). If None, uses original format.
            
        Returns:
            Path to the saved file
        """
        if self.subs is None:
            raise RuntimeError("No subtitle file loaded")
        
        output_path = Path(output_path)
        
        # Determine format
        if format is None:
            format = self.original_format
        
        # Ensure correct extension
        if format == "ass" and not output_path.suffix.lower() in ['.ass', '.ssa']:
            output_path = output_path.with_suffix('.ass')
        elif format == "srt" and output_path.suffix.lower() != '.srt':
            output_path = output_path.with_suffix('.srt')
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save
        try:
            self.subs.save(str(output_path))
            return str(output_path)
        except Exception as e:
            raise RuntimeError(f"Failed to save subtitle: {e}")
    
    def get_preview(self, num_lines: int = 5) -> List[str]:
        """
        Get a preview of the subtitle content.
        
        Args:
            num_lines: Number of lines to preview
            
        Returns:
            List of preview text strings
        """
        if self.subs is None:
            return []
        
        lines = self._convert_to_lines()
        preview = []
        
        for line in lines[:num_lines]:
            time_str = f"[{line.start_time} --> {line.end_time}]"
            preview.append(f"{time_str}\n{line.text}")
        
        return preview
    
    @property
    def line_count(self) -> int:
        """Get total number of dialogue lines."""
        if self.subs is None:
            return 0
        return sum(1 for event in self.subs if event.type == "Dialogue")
    
    @property
    def duration_str(self) -> str:
        """Get total duration as string."""
        if self.subs is None or len(self.subs) == 0:
            return "00:00:00"
        
        last_event = max(self.subs, key=lambda e: e.end)
        ms = last_event.end
        
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
