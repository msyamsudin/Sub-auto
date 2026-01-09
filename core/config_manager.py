"""
Configuration Manager for Sub-auto
Handles loading, saving, and validating application settings.
"""

import json
import os
from pathlib import Path
from typing import Optional


class ConfigManager:
    """Manages application configuration stored in JSON file."""
    
    DEFAULT_CONFIG = {
        "mkvtoolnix_path": "C:\\Program Files\\MKVToolNix",
        "openrouter_api_key": "",
        "provider": "openrouter",  # "openrouter", "ollama", "groq"
        "ollama_base_url": "http://localhost:11434",
        "ollama_model": "llama3",
        "groq_api_key": "",
        "groq_model": "llama3-70b-8192",
        "default_output_dir": "",
        "default_source_lang": "English",
        "default_target_lang": "Indonesian",
        "output_mode": "new_file",  # "new_file", "replace_backup", "ask"
        "default_target_lang": "Indonesian",
        "output_mode": "new_file",  # "new_file", "replace_backup", "ask"
        "batch_size": 25,
        "fallback_model": ""  # Model to use for fallback (e.g. "openai/gpt-3.5-turbo")
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize ConfigManager.
        
        Args:
            config_path: Path to config file. If None, uses default location.
        """
        if config_path is None:
            # Default to config.json in the same directory as this script
            self.config_path = Path(__file__).parent.parent / "config.json"
        else:
            self.config_path = Path(config_path)
        
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from file, creating default if not exists."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # Merge with defaults to ensure all keys exist
                config = self.DEFAULT_CONFIG.copy()
                config.update(loaded_config)
                return config
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}. Using defaults.")
                return self.DEFAULT_CONFIG.copy()
        else:
            # Create default config file
            self._save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()
    
    def _save_config(self, config: dict) -> bool:
        """Save configuration to file."""
        try:
            # Ensure parent directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Error saving config: {e}")
            return False
    
    def save(self) -> bool:
        """Save current configuration to file."""
        return self._save_config(self.config)
    
    def get(self, key: str, default=None):
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value) -> None:
        """Set a configuration value (does not auto-save)."""
        self.config[key] = value
    
    @property
    def mkvtoolnix_path(self) -> str:
        """Get MKVToolnix installation path."""
        return self.config.get("mkvtoolnix_path", "")
    
    @mkvtoolnix_path.setter
    def mkvtoolnix_path(self, value: str) -> None:
        self.config["mkvtoolnix_path"] = value
    
    @property
    def openrouter_api_key(self) -> str:
        """Get OpenRouter API key."""
        return self.config.get("openrouter_api_key", "")
    
    @openrouter_api_key.setter
    def openrouter_api_key(self, value: str) -> None:
        self.config["openrouter_api_key"] = value

    @property
    def openrouter_model(self) -> str:
        """Get OpenRouter model."""
        return self.config.get("openrouter_model", "google/gemini-2.0-flash-exp:free")

    @openrouter_model.setter
    def openrouter_model(self, value: str) -> None:
        self.config["openrouter_model"] = value
    
    @property
    def provider(self) -> str:
        """Get selected provider (openrouter/ollama)."""
        return self.config.get("provider", "openrouter")
    
    @provider.setter
    def provider(self, value: str) -> None:
        if value in ["openrouter", "ollama", "groq"]:
            self.config["provider"] = value
            
    @property
    def ollama_base_url(self) -> str:
        """Get OLLAMA base URL."""
        return self.config.get("ollama_base_url", "http://localhost:11434")
    
    @ollama_base_url.setter
    def ollama_base_url(self, value: str) -> None:
        self.config["ollama_base_url"] = value
        
    @property
    def ollama_model(self) -> str:
        """Get OLLAMA model name."""
        return self.config.get("ollama_model", "llama3")
    
    @ollama_model.setter
    def ollama_model(self, value: str) -> None:
        self.config["ollama_model"] = value

    @property
    def groq_api_key(self) -> str:
        """Get Groq API key."""
        return self.config.get("groq_api_key", "")

    @groq_api_key.setter
    def groq_api_key(self, value: str) -> None:
        self.config["groq_api_key"] = value

    @property
    def groq_model(self) -> str:
        """Get Groq model."""
        return self.config.get("groq_model", "llama3-70b-8192")

    @groq_model.setter
    def groq_model(self, value: str) -> None:
        self.config["groq_model"] = value
    
    @property
    def default_output_dir(self) -> str:
        """Get default output directory."""
        return self.config.get("default_output_dir", "")
    
    @default_output_dir.setter
    def default_output_dir(self, value: str) -> None:
        self.config["default_output_dir"] = value
    
    @property
    def batch_size(self) -> int:
        """Get translation batch size (Fixed at 25)."""
        return 25
    
    @batch_size.setter
    def batch_size(self, value: int) -> None:
        pass # Batch size is now fixed

    @property
    def fallback_model(self) -> str:
        """Get fallback model name."""
        return self.config.get("fallback_model", "")

    @fallback_model.setter
    def fallback_model(self, value: str) -> None:
        self.config["fallback_model"] = value
    
    def validate_mkvtoolnix(self) -> tuple[bool, str]:
        """
        Validate MKVToolnix installation.
        
        Returns:
            Tuple of (is_valid, message)
        """
        path = Path(self.mkvtoolnix_path)
        
        if not path.exists():
            return False, f"MKVToolnix path does not exist: {path}"
        
        mkvmerge = path / "mkvmerge.exe"
        mkvextract = path / "mkvextract.exe"
        
        if not mkvmerge.exists():
            return False, f"mkvmerge.exe not found in: {path}"
        
        if not mkvextract.exists():
            return False, f"mkvextract.exe not found in: {path}"
        
        return True, "MKVToolnix installation validated successfully"
    
    def validate_api_key(self) -> tuple[bool, str]:
        """
        Basic validation of API key format.
        
        Returns:
            Tuple of (is_valid, message)
        """
        key = self.openrouter_api_key
        
        if not key:
            return False, "API key is not set"
        
        if len(key) < 20:
            return False, "API key appears to be too short"
        
        return True, "API key format looks valid"


# Singleton instance for easy access
_config_instance: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Get the global ConfigManager instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance
