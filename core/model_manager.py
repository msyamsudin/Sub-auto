"""
Model Manager for Sub-auto
Manages LLM providers, model selection, and API validation.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from .config_manager import get_config
from .llm_provider import LLMProvider, OpenRouterProvider, OllamaProvider, GroqProvider, ModelInfo


@dataclass
class APIValidationResult:
    """Result of API key validation."""
    is_valid: bool
    message: str
    available_models: List[ModelInfo] = field(default_factory=list)


class ModelManager:
    """Manages LLM providers and model selection."""
    
    def __init__(self):
        self.provider_name: str = "openrouter"
        self.provider: Optional[LLMProvider] = None
        self.is_configured = False
        self.available_models: List[ModelInfo] = []
        self.selected_model: Optional[str] = None
        self.config = get_config()
    
    def configure(self, provider_name: Optional[str] = None):
        """Configure the active provider."""
        self.provider_name = provider_name or self.config.provider
        
        if self.provider_name == "openrouter":
            self.provider = OpenRouterProvider(self.config.openrouter_api_key)
        elif self.provider_name == "ollama":
            self.provider = OllamaProvider(
                base_url=self.config.ollama_base_url
            )
        elif self.provider_name == "groq":
            self.provider = GroqProvider(self.config.groq_api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider_name}")

    def validate_connection(self, provider_name: Optional[str] = None) -> APIValidationResult:
        """
        Validate provider connection and retrieve available models.
        
        Args:
            provider_name: Optional provider to validate. If None, uses current config.

        Returns:
            APIValidationResult with validation status and available models
        """
        self.configure(provider_name=provider_name)  # Re-configure to ensure latest settings
        
        if not self.provider:
            return APIValidationResult(False, "Provider not initialized")
            
        is_valid, message = self.provider.validate_connection()
        
        if not is_valid:
            return APIValidationResult(False, message)
            
        try:
            models = self.provider.list_models()
            
            if not models:
                return APIValidationResult(
                    is_valid=False,
                    message="Connection valid but no models found"
                )
            
            # Store state
            self.is_configured = True
            self.available_models = models
            
            # Auto-select model
            self._auto_select_model()
            
            return APIValidationResult(
                is_valid=True,
                message=f"Connected! Found {len(models)} models.",
                available_models=models
            )
            
        except Exception as e:
            return APIValidationResult(False, f"Validation error: {str(e)}")
    
    def _auto_select_model(self):
        """Auto-select the best default model or use user's saved preference."""
        # First, check if user has a saved model preference in config
        if self.provider_name == "openrouter":
            saved_model = self.config.openrouter_model
            if saved_model:
                # Try to find and select the saved model
                for model in self.available_models:
                    if model.name == saved_model:
                        self.selected_model = model.name
                        return
            
            # Fallback to preferred free models
            preferred_models = [
                "google/gemini-2.0-flash-exp:free",
                "meta-llama/llama-3-8b-instruct:free",
                "huggingfaceh4/zephyr-7b-beta:free",
                "mistralai/mistral-7b-instruct:free",
                "openai/gpt-3.5-turbo"
            ]
        elif self.provider_name == "ollama":
            preferred_models = [
                self.config.ollama_model,
                "llama3",
                "mistral",
                "gemma"
            ]
        elif self.provider_name == "groq":
            preferred_models = [
                self.config.groq_model,
                "llama3-70b-8192",
                "llama3-8b-8192"
            ]
        else:
            preferred_models = []
        
        for preferred in preferred_models:
            for model in self.available_models:
                if preferred.lower() in model.name.lower():
                    self.selected_model = model.name
                    return
        
        # Fallback
        if self.available_models:
            self.selected_model = self.available_models[0].name
    
    def select_model(self, model_name: str) -> bool:
        """Select a model by name."""
        # Try exact match
        for model in self.available_models:
            if model.name == model_name or model.short_name == model_name:
                self.selected_model = model.name
                return True
        
        # Try partial match (case-insensitive)
        for model in self.available_models:
            if model_name.lower() in model.name.lower():
                self.selected_model = model.name
                return True
                
        return False
    
    def get_model_display_names(self) -> List[str]:
        """Get list of model display names."""
        return [model.short_name for model in self.available_models]
    
    def get_selected_model_info(self) -> Optional[ModelInfo]:
        """Get the ModelInfo for the currently selected model."""
        if not self.selected_model:
            return None
        
        for model in self.available_models:
            if model.name == self.selected_model or model.short_name == self.selected_model:
                return model
        
        return None


# Global API manager instance
_model_manager: Optional[ModelManager] = None


def get_api_manager() -> ModelManager:
    """Get the global ModelManager instance."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager


def validate_and_save_api_key(api_key: str) -> APIValidationResult:
    """Validate API key (legacy bridge)."""
    # This is slightly broken in new design as validation depends on provider
    # But usually this is called when user enters OpenRouter key
    manager = get_api_manager()
    manager.config.openrouter_api_key = api_key
    manager.config.provider = "openrouter"
    return manager.validate_connection()
