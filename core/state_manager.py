"""
State Manager for Sub-auto
Handles saving and loading translation progress for pause/resume functionality.
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import hashlib


@dataclass
class TranslationState:
    """Represents the saved state of a translation session."""
    
    # File identification
    source_file: str                          # Path to source MKV file
    source_file_hash: str                     # Hash of first 1MB for verification
    track_id: int                             # Selected subtitle track
    
    # Translation settings
    source_lang: str
    target_lang: str
    model_name: str
    
    # Progress tracking
    total_lines: int
    completed_translations: List[Tuple[int, str]]  # (index, translated_text)
    current_batch_index: int
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Token tracking
    prompt_tokens_used: int = 0
    completion_tokens_used: int = 0
    
    @property
    def progress_percent(self) -> float:
        """Get progress as percentage."""
        if self.total_lines == 0:
            return 0.0
        return (len(self.completed_translations) / self.total_lines) * 100
    
    @property
    def lines_remaining(self) -> int:
        """Get number of lines remaining."""
        return self.total_lines - len(self.completed_translations)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source_file": self.source_file,
            "source_file_hash": self.source_file_hash,
            "track_id": self.track_id,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "model_name": self.model_name,
            "total_lines": self.total_lines,
            "completed_translations": self.completed_translations,
            "current_batch_index": self.current_batch_index,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "prompt_tokens_used": self.prompt_tokens_used,
            "completion_tokens_used": self.completion_tokens_used
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranslationState":
        """Create from dictionary."""
        return cls(
            source_file=data["source_file"],
            source_file_hash=data["source_file_hash"],
            track_id=data["track_id"],
            source_lang=data["source_lang"],
            target_lang=data["target_lang"],
            model_name=data["model_name"],
            total_lines=data["total_lines"],
            completed_translations=[tuple(t) for t in data["completed_translations"]],
            current_batch_index=data["current_batch_index"],
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            prompt_tokens_used=data.get("prompt_tokens_used", 0),
            completion_tokens_used=data.get("completion_tokens_used", 0)
        )


import threading

class StateManager:
    """
    Manages translation state persistence.
    Saves progress to allow pause/resume and recovery from crashes.
    """
    
    STATE_FILENAME = "translation_state.json"
    
    def __init__(self, state_dir: Optional[str] = None):
        """
        Initialize StateManager.
        
        Args:
            state_dir: Directory to store state files. Defaults to app directory.
        """
        self._lock = threading.RLock()
        
        if state_dir:
            self.state_dir = Path(state_dir)
        else:
            # Use the script's directory
            self.state_dir = Path(__file__).parent.parent
        
        self.state_file = self.state_dir / self.STATE_FILENAME
        self.current_state: Optional[TranslationState] = None
    
    @staticmethod
    def calculate_file_hash(file_path: str, size: int = 1024 * 1024) -> str:
        """
        Calculate hash of first N bytes of a file for identification.
        
        Args:
            file_path: Path to the file
            size: Number of bytes to hash (default 1MB)
            
        Returns:
            MD5 hash string
        """
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                data = f.read(size)
                hasher.update(data)
            return hasher.hexdigest()
        except Exception:
            return ""
    
    def create_state(
        self,
        source_file: str,
        track_id: int,
        total_lines: int,
        source_lang: str,
        target_lang: str,
        model_name: str
    ) -> TranslationState:
        """
        Create a new translation state.
        
        Args:
            source_file: Path to source MKV file
            track_id: Selected subtitle track ID
            total_lines: Total number of lines to translate
            source_lang: Source language
            target_lang: Target language
            model_name: Model being used
            
        Returns:
            New TranslationState object
        """
        file_hash = self.calculate_file_hash(source_file)
        
        with self._lock:
            self.current_state = TranslationState(
                source_file=source_file,
                source_file_hash=file_hash,
                track_id=track_id,
                source_lang=source_lang,
                target_lang=target_lang,
                model_name=model_name,
                total_lines=total_lines,
                completed_translations=[],
                current_batch_index=0
            )
            
            self.save()
            return self.current_state
    
    def update_progress(
        self,
        new_translations: List[Tuple[int, str]],
        batch_index: int,
        prompt_tokens: int = 0,
        completion_tokens: int = 0
    ):
        """
        Update state with new translation progress.
        
        Args:
            new_translations: Newly translated lines
            batch_index: Current batch index
            prompt_tokens: Tokens used in this update
            completion_tokens: Completion tokens used
        """
        with self._lock:
            if not self.current_state:
                return
            
            # Add new translations
            existing_indices = {t[0] for t in self.current_state.completed_translations}
            for translation in new_translations:
                if translation[0] not in existing_indices:
                    self.current_state.completed_translations.append(translation)
            
            self.current_state.current_batch_index = batch_index
            self.current_state.updated_at = datetime.now().isoformat()
            self.current_state.prompt_tokens_used += prompt_tokens
            self.current_state.completion_tokens_used += completion_tokens
            
            self.save()
    
    def save(self):
        """Save current state to file."""
        with self._lock:
            if not self.current_state:
                return
            
            try:
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(self.current_state.to_dict(), f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Warning: Failed to save state: {e}")
    
    def load(self) -> Optional[TranslationState]:
        """
        Load state from file.
        
        Returns:
            TranslationState if found, None otherwise
        """
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.current_state = TranslationState.from_dict(data)
                return self.current_state
        except Exception as e:
            print(f"Warning: Failed to load state: {e}")
            return None
    
    def has_resumable_state(self, source_file: Optional[str] = None) -> bool:
        """
        Check if there's a resumable state.
        
        Args:
            source_file: Optional file path to check against
            
        Returns:
            True if resumable state exists
        """
        state = self.load()
        if not state:
            return False
        
        # Check if there's actual progress
        if len(state.completed_translations) == 0:
            self.current_state = None  # Clear invalid state
            return False
        
        # If source file specified, verify it matches
        if source_file:
            if state.source_file != source_file:
                self.current_state = None  # Clear invalid state
                return False
            # Verify file hash
            current_hash = self.calculate_file_hash(source_file)
            if current_hash and state.source_file_hash != current_hash:
                self.current_state = None  # Clear invalid state
                return False
        
        # Check if source file still exists
        if not Path(state.source_file).exists():
            self.current_state = None  # Clear invalid state
            return False
        
        return True
    
    def get_state_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of the current saved state.
        
        Returns:
            Summary dict or None if no state
        """
        state = self.load()
        if not state:
            return None
        
        return {
            "source_file": Path(state.source_file).name,
            "track_id": state.track_id,
            "progress_percent": state.progress_percent,
            "lines_completed": len(state.completed_translations),
            "lines_remaining": state.lines_remaining,
            "total_lines": state.total_lines,
            "source_lang": state.source_lang,
            "target_lang": state.target_lang,
            "model_name": state.model_name,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
            "tokens_used": state.prompt_tokens_used + state.completion_tokens_used
        }
    
    def clear(self):
        """Clear the saved state (call after successful completion)."""
        self.current_state = None
        if self.state_file.exists():
            try:
                os.remove(self.state_file)
            except Exception as e:
                print(f"Warning: Failed to clear state: {e}")
    
    def get_completed_indices(self) -> set:
        """Get set of already completed line indices."""
        if not self.current_state:
            return set()
        return {t[0] for t in self.current_state.completed_translations}
    
    def get_completed_translations(self) -> List[Tuple[int, str]]:
        """Get list of completed translations."""
        if not self.current_state:
            return []
        return self.current_state.completed_translations.copy()


# Global state manager instance
_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get the global StateManager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
