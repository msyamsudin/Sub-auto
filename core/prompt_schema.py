"""
Prompt Schema for Sub-auto
Defines the data model for translation prompts.
"""

from dataclasses import dataclass
from datetime import datetime
from string import Formatter
from typing import Dict, List, Tuple


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
    ALLOWED_PLACEHOLDERS = {"source_lang", "target_lang", "lines", "context"}
    MAX_LENGTH = 10000  # Maximum prompt length in characters

    def get_placeholder_names(self) -> Tuple[List[str], List[str]]:
        """Return placeholder names and formatter parsing errors."""
        formatter = Formatter()
        names: List[str] = []
        errors: List[str] = []

        try:
            for _, field_name, _, _ in formatter.parse(self.content):
                if field_name is None:
                    continue

                normalized = field_name.strip()
                if not normalized:
                    errors.append("Empty placeholder detected. Use escaped braces '{{' or '}}' for literal braces.")
                    continue

                if normalized != field_name:
                    errors.append(f"Invalid placeholder syntax: {{{field_name}}}")
                    continue

                if any(token in normalized for token in (".", "[", "]", "!", ":")):
                    errors.append(f"Unsupported placeholder syntax: {{{normalized}}}")
                    continue

                names.append(normalized)
        except ValueError as exc:
            errors.append(f"Invalid format string: {exc}")

        return names, errors

    def render(self, values: Dict[str, str]) -> str:
        """Render the prompt with placeholder values."""
        return self.content.format(**values)
    
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
        
        placeholders, placeholder_errors = self.get_placeholder_names()
        errors.extend(placeholder_errors)

        # Check for required placeholders
        placeholder_set = set(placeholders)
        for placeholder in self.ALLOWED_PLACEHOLDERS:
            if placeholder not in placeholder_set:
                errors.append(f"Missing required placeholder: {{{placeholder}}}")

        # Check for unsupported placeholders
        for placeholder in placeholder_set:
            if placeholder not in self.ALLOWED_PLACEHOLDERS:
                errors.append(f"Unknown placeholder: {{{placeholder}}}")

        # Check for output structure guidance
        normalized = self.content.upper()
        if "[NUMBER]" not in normalized and "OUTPUT" not in normalized and "RESPOND WITH" not in normalized and "RETURN FORMAT" not in normalized:
            errors.append("Prompt should describe the expected subtitle output format")

        # Validate renderability with sample data
        if not placeholder_errors:
            try:
                self.render({
                    "source_lang": "English",
                    "target_lang": "Indonesian",
                    "context": "(No previous context)",
                    "lines": "[1] Hello world"
                })
            except KeyError as exc:
                errors.append(f"Unknown placeholder during render: {{{exc.args[0]}}}")
            except ValueError as exc:
                errors.append(f"Invalid format string: {exc}")
        
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
