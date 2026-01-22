"""
Prompt Manager for Sub-auto
Business logic layer for managing translation prompts.
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime

from .prompt_schema import Prompt, PromptMetadata
from .prompt_repository import PromptRepository
from .logger import get_logger


class PromptManager:
    """Manager for translation prompts with validation and fallback."""
    
    # Default prompts (immutable)
    DEFAULT_PROMPTS = {
        "Standard": """You are a professional subtitle translator. Translate the following subtitle lines from {source_lang} to {target_lang}.

CRITICAL RULES:
1. Use natural, spoken language suitable for subtitles
2. Prioritize meaning, tone, and emotion over literal translation
3. Do not force-translate commonly used loanwords
4. Keep names, proper nouns unchanged
5. Preserve formatting markers like \\N exactly
6. If a line is already in the target language or is a non-dialogue cue, keep it as-is
7. Keep translations concise and subtitle-friendly

CONTEXT:
{context}

TRANSLATE:
{lines}

OUTPUT:
[NUMBER] translated text""",
        
        "Anime": """You are a professional anime subtitle translator.
Translate the following subtitle lines from {source_lang} to {target_lang}.

CRITICAL RULES:
1. Use natural, spoken language suitable for anime subtitles
2. Prioritize meaning, tone, and emotion over literal translation
3. Do not force-translate commonly used loanwords
4. Keep names, proper nouns, and Japanese honorifics (-san, -kun, -chan, -sama, -senpai, etc.) unchanged
5. Preserve formatting markers like \\N exactly
6. If a line is already in the target language or is a non-dialogue cue, keep it as-is
7. Keep translations concise and subtitle-friendly
8. Preserve Japanese terms commonly used in anime culture (e.g., "bento", "manga", "sensei" when referring to teacher)
9. For attack names/technique names in action anime, keep original Japanese
10. Maintain character speech patterns (formal/informal, masculine/feminine speech)

CONTEXT:
{context}

TRANSLATE:
{lines}

OUTPUT:
[NUMBER] translated text""",
        
        "Formal": """You are a professional translator specializing in formal content. Translate the following subtitle lines from {source_lang} to {target_lang}.

CRITICAL RULES:
1. Use formal, professional language
2. Maintain accuracy and precision
3. Preserve technical terms and proper nouns
4. Keep formatting markers like \\N exactly
5. Use complete sentences with proper grammar
6. Avoid colloquialisms and slang
7. Maintain respectful tone throughout

CONTEXT:
{context}

TRANSLATE:
{lines}

OUTPUT:
[NUMBER] translated text"""
    }
    
    def __init__(self, repository: Optional[PromptRepository] = None):
        """
        Initialize the PromptManager.
        
        Args:
            repository: Optional PromptRepository instance. If None, creates default.
        """
        self.logger = get_logger()
        self.repository = repository or PromptRepository()
        
        # Ensure defaults exist
        self._ensure_defaults()
    
    def _ensure_defaults(self):
        """Ensure default prompts exist in the repository."""
        now = datetime.now()
        
        for name, content in self.DEFAULT_PROMPTS.items():
            if not self.repository.exists(name):
                prompt = Prompt(
                    name=name,
                    version="1.0.0",
                    active=(name == "Standard"),  # Standard is active by default
                    locked=True,
                    content=content,
                    metadata=PromptMetadata(
                        description=f"{name} translation prompt",
                        author="System",
                        created_at=now,
                        updated_at=now
                    )
                )
                self.repository.save(prompt)
                self.logger.info(f"Created default prompt: {name}")
    
    def get_active_prompt(self) -> str:
        """
        Get the active prompt content with fallback.
        
        Returns:
            The active prompt content string.
        """
        # Try to get active prompt
        active = self.repository.get_active()
        
        if active:
            # Validate before returning
            is_valid, errors = active.validate()
            if is_valid:
                return active.content
            else:
                self.logger.warning(f"Active prompt '{active.name}' is invalid: {errors}")
                self.logger.warning("Falling back to default 'Standard' prompt")
        
        # Fallback to Standard prompt
        standard = self.repository.get("Standard")
        if standard:
            return standard.content
        
        # Ultimate fallback: return hardcoded Standard prompt
        self.logger.error("Failed to load any prompt from repository, using hardcoded fallback")
        return self.DEFAULT_PROMPTS["Standard"]
    
    def validate_prompt(self, content: str) -> Tuple[bool, List[str]]:
        """
        Validate a prompt content string.
        
        Args:
            content: The prompt content to validate.
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        # Create a temporary prompt for validation
        temp_prompt = Prompt(
            name="temp",
            version="1.0.0",
            active=False,
            locked=False,
            content=content,
            metadata=PromptMetadata(
                description="Temporary",
                author="User",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        )
        
        return temp_prompt.validate()
    
    def get_all_prompts(self) -> Dict[str, Prompt]:
        """
        Get all prompts.
        
        Returns:
            Dictionary mapping prompt names to Prompt objects.
        """
        return self.repository.load_all()
    
    def save_prompt(self, prompt: Prompt) -> Tuple[bool, str]:
        """
        Save a prompt after validation.
        
        Args:
            prompt: The prompt to save.
            
        Returns:
            Tuple of (success, message)
        """
        # Validate
        is_valid, errors = prompt.validate()
        if not is_valid:
            error_msg = "; ".join(errors)
            self.logger.warning(f"Failed to save prompt '{prompt.name}': {error_msg}")
            return False, error_msg
        
        # Check if locked
        existing = self.repository.get(prompt.name)
        if existing and existing.locked and not prompt.locked:
            return False, "Cannot modify locked prompt"
        
        # Save
        try:
            self.repository.save(prompt)
            return True, "Prompt saved successfully"
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Failed to save prompt: {error_msg}")
            return False, f"Save failed: {error_msg}"
    
    def delete_prompt(self, name: str) -> Tuple[bool, str]:
        """
        Delete a prompt.
        
        Args:
            name: Name of the prompt to delete.
            
        Returns:
            Tuple of (success, message)
        """
        if name in self.DEFAULT_PROMPTS:
            return False, "Cannot delete default prompt"
        
        success = self.repository.delete(name)
        if success:
            return True, "Prompt deleted successfully"
        else:
            return False, "Failed to delete prompt (not found or locked)"
    
    def set_active(self, name: str) -> Tuple[bool, str]:
        """
        Set a prompt as active.
        
        Args:
            name: Name of the prompt to activate.
            
        Returns:
            Tuple of (success, message)
        """
        # Validate the prompt before activating
        prompt = self.repository.get(name)
        if not prompt:
            return False, "Prompt not found"
        
        is_valid, errors = prompt.validate()
        if not is_valid:
            error_msg = "; ".join(errors)
            return False, f"Cannot activate invalid prompt: {error_msg}"
        
        success = self.repository.set_active(name)
        if success:
            return True, f"Activated prompt: {name}"
        else:
            return False, "Failed to activate prompt"
    
    def duplicate_prompt(self, source_name: str, new_name: str) -> Tuple[bool, str]:
        """
        Duplicate a prompt.
        
        Args:
            source_name: Name of the prompt to duplicate.
            new_name: Name for the new prompt.
            
        Returns:
            Tuple of (success, message)
        """
        # Check if source exists
        source = self.repository.get(source_name)
        if not source:
            return False, "Source prompt not found"
        
        # Check if new name already exists
        if self.repository.exists(new_name):
            return False, "A prompt with this name already exists"
        
        # Create duplicate
        now = datetime.now()
        new_prompt = Prompt(
            name=new_name,
            version="1.0.0",
            active=False,
            locked=False,  # Duplicates are never locked
            content=source.content,
            metadata=PromptMetadata(
                description=f"Duplicate of {source_name}",
                author="User",
                created_at=now,
                updated_at=now
            )
        )
        
        try:
            self.repository.save(new_prompt)
            return True, f"Created duplicate: {new_name}"
        except Exception as e:
            return False, f"Failed to duplicate: {str(e)}"
    
    def reset_defaults(self) -> Tuple[bool, str]:
        """
        Reset all default prompts to their original content.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            now = datetime.now()
            
            for name, content in self.DEFAULT_PROMPTS.items():
                existing = self.repository.get(name)
                
                prompt = Prompt(
                    name=name,
                    version="1.0.0",
                    active=existing.active if existing else (name == "Standard"),
                    locked=True,
                    content=content,
                    metadata=PromptMetadata(
                        description=f"{name} translation prompt",
                        author="System",
                        created_at=existing.metadata.created_at if existing else now,
                        updated_at=now
                    )
                )
                
                self.repository.save(prompt)
            
            self.logger.info("Reset all default prompts")
            return True, "Default prompts reset successfully"
        
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Failed to reset defaults: {error_msg}")
            return False, f"Reset failed: {error_msg}"
