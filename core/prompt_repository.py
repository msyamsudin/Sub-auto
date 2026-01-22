"""
Prompt Repository for Sub-auto
Handles persistence of prompts to/from JSON storage.
"""

import json
import os
from typing import Dict, Optional, List
from pathlib import Path

from .prompt_schema import Prompt, PromptMetadata
from .logger import get_logger
from datetime import datetime


class PromptRepository:
    """Repository for managing prompt persistence."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the repository.
        
        Args:
            storage_path: Path to prompts.json file. If None, uses default location.
        """
        self.logger = get_logger()
        
        if storage_path is None:
            # Default to config directory
            config_dir = Path.home() / ".sub-auto"
            config_dir.mkdir(exist_ok=True)
            storage_path = str(config_dir / "prompts.json")
        
        self.storage_path = storage_path
        self._prompts: Dict[str, Prompt] = {}
        self._load_from_disk()
    
    def _load_from_disk(self):
        """Load prompts from disk."""
        if not os.path.exists(self.storage_path):
            self.logger.info(f"Prompts file not found at {self.storage_path}, will create on first save")
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load prompts
            for prompt_data in data.get("prompts", []):
                try:
                    prompt = Prompt.from_dict(prompt_data)
                    self._prompts[prompt.name] = prompt
                except Exception as e:
                    self.logger.error(f"Failed to load prompt: {e}")
            
            self.logger.info(f"Loaded {len(self._prompts)} prompts from {self.storage_path}")
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse prompts file: {e}")
            self.logger.warning("Prompts file is corrupted, starting with empty repository")
        except Exception as e:
            self.logger.error(f"Failed to load prompts: {e}")
    
    def _save_to_disk(self):
        """Save prompts to disk."""
        try:
            data = {
                "version": "1.0.0",
                "prompts": [prompt.to_dict() for prompt in self._prompts.values()]
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            # Write to temp file first, then rename (atomic operation)
            temp_path = self.storage_path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            os.replace(temp_path, self.storage_path)
            
            self.logger.info(f"Saved {len(self._prompts)} prompts to {self.storage_path}")
        
        except Exception as e:
            self.logger.error(f"Failed to save prompts: {e}")
            raise
    
    def load_all(self) -> Dict[str, Prompt]:
        """
        Load all prompts.
        
        Returns:
            Dictionary mapping prompt names to Prompt objects.
        """
        return self._prompts.copy()
    
    def save(self, prompt: Prompt):
        """
        Save a prompt.
        
        Args:
            prompt: The prompt to save.
        """
        # Update timestamp
        prompt.metadata.updated_at = datetime.now()
        
        # Add to in-memory cache
        self._prompts[prompt.name] = prompt
        
        # Persist to disk
        self._save_to_disk()
        
        self.logger.info(f"Saved prompt: {prompt.name}")
    
    def delete(self, name: str) -> bool:
        """
        Delete a prompt.
        
        Args:
            name: Name of the prompt to delete.
            
        Returns:
            True if deleted, False if not found or locked.
        """
        if name not in self._prompts:
            self.logger.warning(f"Prompt not found: {name}")
            return False
        
        prompt = self._prompts[name]
        if prompt.locked:
            self.logger.warning(f"Cannot delete locked prompt: {name}")
            return False
        
        del self._prompts[name]
        self._save_to_disk()
        
        self.logger.info(f"Deleted prompt: {name}")
        return True
    
    def get_active(self) -> Optional[Prompt]:
        """
        Get the currently active prompt.
        
        Returns:
            The active prompt, or None if no active prompt is set.
        """
        for prompt in self._prompts.values():
            if prompt.active:
                return prompt
        return None
    
    def set_active(self, name: str) -> bool:
        """
        Set a prompt as active.
        
        Args:
            name: Name of the prompt to activate.
            
        Returns:
            True if successful, False if prompt not found.
        """
        if name not in self._prompts:
            self.logger.warning(f"Prompt not found: {name}")
            return False
        
        # Deactivate all prompts
        for prompt in self._prompts.values():
            prompt.active = False
        
        # Activate the selected prompt
        self._prompts[name].active = True
        
        self._save_to_disk()
        
        self.logger.info(f"Set active prompt: {name}")
        return True
    
    def get(self, name: str) -> Optional[Prompt]:
        """
        Get a specific prompt by name.
        
        Args:
            name: Name of the prompt.
            
        Returns:
            The prompt, or None if not found.
        """
        return self._prompts.get(name)
    
    def exists(self, name: str) -> bool:
        """
        Check if a prompt exists.
        
        Args:
            name: Name of the prompt.
            
        Returns:
            True if exists, False otherwise.
        """
        return name in self._prompts
