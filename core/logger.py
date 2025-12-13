"""
Logger module for Sub-auto.
Provides a singleton logger for centralized application logging.
"""

from typing import Optional, List, Callable
from datetime import datetime
import threading
from pathlib import Path


class Logger:
    """Singleton Logger class."""
    
    _instance = None
    
    LEVEL_INFO = "INFO"
    LEVEL_WARNING = "WARNING"
    LEVEL_ERROR = "ERROR"
    LEVEL_DEBUG = "DEBUG"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.callbacks: List[Callable[[str, str, str], None]] = []
        self._lock = threading.Lock()
        self.log_history: List[str] = []
        self._initialized = True
    
    def add_callback(self, callback: Callable[[str, str, str], None]):
        """
        Add a callback function to receive log updates.
        Callback signature: (timestamp, level, message)
        """
        with self._lock:
            self.callbacks.append(callback)
            
    def _emit(self, level: str, message: str):
        """Emit log to all callbacks."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_log = f"[{timestamp}] [{level}] {message}"
        
        # Store in history
        with self._lock:
            self.log_history.append(formatted_log)
            # Keep only last 1000 logs
            if len(self.log_history) > 1000:
                self.log_history.pop(0)
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(timestamp, level, message)
            except Exception as e:
                print(f"Error in log callback: {e}")
                
        # Also print to console
        print(formatted_log)
    
    def info(self, message: str):
        self._emit(self.LEVEL_INFO, message)
        
    def warning(self, message: str):
        self._emit(self.LEVEL_WARNING, message)
        
    def error(self, message: str):
        self._emit(self.LEVEL_ERROR, message)
        
    def debug(self, message: str):
        self._emit(self.LEVEL_DEBUG, message)
        
    def save_to_file(self, filepath: str):
        """Save log history to a file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                with self._lock:
                    f.write("\n".join(self.log_history))
        except Exception as e:
            self.error(f"Failed to save log to file: {e}")
            
    def clear(self):
        """Clear log history."""
        with self._lock:
            self.log_history.clear()


# Global accessor
def get_logger() -> Logger:
    return Logger()
