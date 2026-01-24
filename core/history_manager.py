"""
History Manager for Sub-auto
Manages the persistence and retrieval of translation session history.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import threading

@dataclass
class HistoryEntry:
    """Represents a single entry in the translation history."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # File details
    source_file: str = ""
    source_file_name: str = ""
    output_file: str = ""
    
    # Track details
    track_id: int = -1
    source_lang: str = ""
    target_lang: str = ""
    
    # Process details
    model_name: str = ""
    provider: str = ""
    prompt_name: str = ""
    total_lines: int = 0
    lines_translated: int = 0
    
    # Performance
    duration_seconds: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost: Optional[float] = None
    
    # Status
    status: str = "completed"  # completed, cancelled, failed
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryEntry":
        """Create an entry from a dictionary."""
        return cls(**data)


class HistoryManager:
    """
    Manages translation history persistence.
    Saves and loads past sessions from history.json.
    """
    
    HISTORY_FILENAME = "history.json"
    
    def __init__(self, history_dir: Optional[str] = None):
        """
        Initialize HistoryManager.
        
        Args:
            history_dir: Directory to store history file. Defaults to app directory.
        """
        self._lock = threading.RLock()
        
        if history_dir:
            self.history_dir = Path(history_dir)
        else:
            # Use the script's directory
            self.history_dir = Path(__file__).parent.parent
        
        self.history_file = self.history_dir / self.HISTORY_FILENAME
        self.entries: List[HistoryEntry] = []
        self._load()
    
    def _load(self):
        """Load history from file."""
        if not self.history_file.exists():
            self.entries = []
            return
            
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.entries = [HistoryEntry.from_dict(item) for item in data]
                else:
                    self.entries = []
        except Exception as e:
            print(f"Warning: Failed to load history: {e}")
            self.entries = []
            
    def _save(self):
        """Save history to file."""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([item.to_dict() for item in self.entries], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save history: {e}")
            
    def add_entry(self, entry: HistoryEntry):
        """Add a new history entry."""
        with self._lock:
            self.entries.insert(0, entry) # Add to the beginning (newest first)
            # Limit history to 100 entries to prevent file bloating
            if len(self.entries) > 100:
                self.entries = self.entries[:100]
            self._save()
            
    def get_entries(self) -> List[HistoryEntry]:
        """Get all history entries."""
        with self._lock:
            return list(self.entries)
            
    def delete_entry(self, entry_id: str):
        """Delete a history entry by ID."""
        with self._lock:
            self.entries = [e for e in self.entries if e.id != entry_id]
            self._save()
            
    def delete_entries(self, entry_ids: List[str]):
        """Delete multiple history entries."""
        with self._lock:
            id_set = set(entry_ids)
            self.entries = [e for e in self.entries if e.id not in id_set]
            self._save()
            
    def clear_all(self):
        """Clear all history."""
        with self._lock:
            self.entries = []
            self._save()


# Global history manager instance
_history_manager: Optional[HistoryManager] = None

def get_history_manager() -> HistoryManager:
    """Get the global HistoryManager instance."""
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager()
    return _history_manager
