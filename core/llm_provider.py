"""
LLM Provider Abstraction
Handles communication with different LLM providers (Gemini, OLLAMA).
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Generator
from dataclasses import dataclass
import json
import urllib.request
import urllib.error
from .logger import get_logger

@dataclass
class ModelInfo:
    """Information about an available model."""
    name: str
    display_name: str
    provider: str
    description: str = ""
    input_token_limit: int = 0
    output_token_limit: int = 0
    prompt_price: float = 0.0  # Price per 1M tokens for prompt
    completion_price: float = 0.0  # Price per 1M tokens for completion

    @property
    def short_name(self) -> str:
        """Get short name for display."""
        # Clean up model names
        name = self.name.replace("models/", "")
        return name
    
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost in USD based on token usage."""
        # Prices are typically per 1M tokens
        prompt_cost = (prompt_tokens / 1_000_000) * self.prompt_price
        completion_cost = (completion_tokens / 1_000_000) * self.completion_price
        return prompt_cost + completion_cost

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self):
        self.logger = get_logger()

    @abstractmethod
    def validate_connection(self) -> tuple[bool, str]:
        """Validate connection/API key."""
        pass

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """List available models."""
        pass

    @abstractmethod
    def generate_content(self, model_name: str, prompt: str) -> str:
        """Generate content from the model."""
        pass

class OpenRouterProvider(LLMProvider):
    """Provider for OpenRouter API."""
    
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to OpenRouter."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/sub-auto", # Required by OpenRouter
            "X-Title": "Sub-auto" # Required by OpenRouter
        }
        
        body = json.dumps(data).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        
        try:
            # Set explicit timeout of 60 seconds
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"OpenRouter API error ({e.code}): {error_body}")
        except Exception as e:
            raise RuntimeError(f"Request failed: {str(e)}")

    def validate_connection(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "API key is not set"
        
        try:
            # Try to list models to validate key
            self._request("GET", "/models")
            return True, "Connected to OpenRouter"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def list_models(self) -> List[ModelInfo]:
        models = []
        try:
            data = self._request("GET", "/models")
            for m in data.get("data", []):
                # Only include commonly used models to avoid spam, or include all?
                # OpenRouter has MANY models. Let's include them but maybe filter later if needed.
                # For now, we take them all.
                
                # Extract pricing info - OpenRouter returns price per token as string
                pricing = m.get("pricing", {})
                try:
                    # Prices are returned as strings like "0.0000001" per token
                    # Convert to per 1M tokens for easier calculation
                    prompt_price_per_token = float(pricing.get('prompt', '0'))
                    completion_price_per_token = float(pricing.get('completion', '0'))
                    prompt_price = prompt_price_per_token * 1_000_000  # Per 1M tokens
                    completion_price = completion_price_per_token * 1_000_000
                except (ValueError, TypeError):
                    prompt_price = 0.0
                    completion_price = 0.0
                
                models.append(ModelInfo(
                    name=m.get("id"),
                    display_name=m.get("name", m.get("id")),
                    provider="OpenRouter",
                    description=m.get("description", "")[:100] + "...",
                    input_token_limit=m.get("context_length", 0),
                    output_token_limit=m.get("top_provider", {}).get("max_completion_tokens", 0),
                    prompt_price=prompt_price,
                    completion_price=completion_price
                ))
        except Exception as e:
            self.logger.error(f"Failed to list OpenRouter models: {e}")
        
        # Sort by name
        return sorted(models, key=lambda x: x.name)

    def generate_content(self, model_name: str, prompt: str) -> str:
        import time
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3 # Lower temperature for translation
        }
        
        try:
            start_time = time.time()
            result = self._request("POST", "/chat/completions", data)
            elapsed = time.time() - start_time
            self.logger.info(f"OpenRouter API response time: {elapsed:.2f}s (model: {model_name})")
            
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            result_error = result.get('error', {})
            if result_error:
                 raise RuntimeError(f"API Error: {result_error.get('message', 'Unknown error')}")
            return ""
        except Exception as e:
            raise RuntimeError(f"OpenRouter generation failed: {str(e)}")

class OllamaProvider(LLMProvider):
    """Provider for local OLLAMA instance."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        super().__init__()
        self.base_url = base_url.rstrip('/')

    def _get_opener(self):
        """Get url opener that bypasses proxies."""
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        return opener

    def validate_connection(self) -> tuple[bool, str]:
        try:
            # Check version endpoint
            opener = self._get_opener()
            with opener.open(f"{self.base_url}/api/version", timeout=2) as response:
                if response.status == 200:
                    return True, "Connected to OLLAMA"
                return False, f"OLLAMA returned status {response.status}"
        except urllib.error.URLError as e:
            return False, f"Could not connect to OLLAMA at {self.base_url}: {e.reason}"
        except Exception as e:
            return False, f"OLLAMA connection failed: {str(e)}"

    def list_models(self) -> List[ModelInfo]:
        models = []
        try:
            opener = self._get_opener()
            with opener.open(f"{self.base_url}/api/tags", timeout=5) as response:
                if response.status != 200:
                    raise RuntimeError(f"OLLAMA returned status {response.status}")
                    
                data = json.loads(response.read().decode())
                
                for m in data.get("models", []):
                    name = m.get("name", "unknown")
                    # Parse details
                    details = m.get("details", {})
                    param_size = details.get("parameter_size", "")
                    quant = details.get("quantization_level", "")
                    
                    desc = f"{param_size} {quant}" if param_size else ""
                    
                    models.append(ModelInfo(
                        name=name,
                        display_name=name,
                        provider="OLLAMA",
                        description=desc
                    ))
        except urllib.error.URLError as e:
            raise RuntimeError(f"Connection failed: {e.reason}")
        except json.JSONDecodeError:
            raise RuntimeError("Invalid response from OLLAMA")
        except Exception as e:
            raise RuntimeError(f"Failed to list models: {str(e)}")
            
        return sorted(models, key=lambda x: x.name)

    def generate_content(self, model_name: str, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        data = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            opener = self._get_opener()
            with opener.open(req) as response:
                result = json.loads(response.read().decode())
                return result.get("response", "")
        except Exception as e:
            raise RuntimeError(f"OLLAMA generation failed: {str(e)}")
