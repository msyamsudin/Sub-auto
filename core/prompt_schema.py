"""
Prompt Schema for Sub-auto
Defines the data model for translation prompts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple, Optional


@dataclass
class PromptMetadata:
    """Metadata for a prompt."""
    description: str
    author: str
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "description": self.description,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PromptMetadata":
        """Create from dictionary."""
        return cls(
            description=data.get("description", ""),
            author=data.get("author", "Unknown"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        )


@dataclass
class Prompt:
    """A translation prompt template."""
    name: str
    version: str
    active: bool
    locked: bool
    content: str
    metadata: PromptMetadata
    
    # Validation constants
    REQUIRED_PLACEHOLDERS = ["{source_lang}", "{target_lang}", "{lines}", "{context}"]
    MAX_LENGTH = 10000  # Maximum prompt length in characters
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the prompt structure and content.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check if content is empty
        if not self.content or not self.content.strip():
            errors.append("Prompt content cannot be empty")
        
        # Check length
        if len(self.content) > self.MAX_LENGTH:
            errors.append(f"Prompt exceeds maximum length of {self.MAX_LENGTH} characters")
        
        # Check for required placeholders
        for placeholder in self.REQUIRED_PLACEHOLDERS:
            if placeholder not in self.content:
                errors.append(f"Missing required placeholder: {placeholder}")
        
        # Check for basic output instruction
        if "OUTPUT" not in self.content.upper():
            errors.append("Prompt should contain output format instructions")
        
        # Check for forbidden patterns (potential injection attempts)
        forbidden_patterns = [
            "```python",  # Code execution attempts
            "import os",
            "import sys",
            "exec(",
            "eval(",
        ]
        
        for pattern in forbidden_patterns:
            if pattern in self.content:
                errors.append(f"Forbidden pattern detected: {pattern}")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "active": self.active,
            "locked": self.locked,
            "content": self.content,
            "metadata": self.metadata.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Prompt":
        """Create from dictionary."""
        return cls(
            name=data.get("name", "Unnamed"),
            version=data.get("version", "1.0.0"),
            active=data.get("active", False),
            locked=data.get("locked", False),
            content=data.get("content", ""),
            metadata=PromptMetadata.from_dict(data.get("metadata", {}))
        )
