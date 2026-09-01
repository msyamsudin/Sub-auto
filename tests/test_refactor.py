
import unittest
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.retry_handler import NetworkRetryHandler, RetryConfig
from core.model_manager import ModelManager, APIValidationResult
from core.translator import Translator, TokenUsage

class TestRefactoring(unittest.TestCase):
    def test_imports_and_classes(self):
        """Test that all classes can be imported and instantiated correctly."""
        
        # Test RetryHandler
        retry_config = RetryConfig(max_retries=3)
        retry_handler = NetworkRetryHandler(retry_config)
        self.assertEqual(retry_handler.config.max_retries, 3)
        self.assertIsNotNone(retry_handler)
        print("✅ NetworkRetryHandler initialized successfully")
        
        # Test ModelManager
        model_manager = ModelManager()
        self.assertIsNotNone(model_manager)
        print("✅ ModelManager initialized successfully")
        
        # Test Translator
        translator = Translator(model_manager=model_manager, retry_config=retry_config)
        self.assertIsNotNone(translator)
        self.assertIsInstance(translator.retry_handler, NetworkRetryHandler)
        self.assertIsInstance(translator.model_manager, ModelManager)
        print("✅ Translator initialized successfully with refactored components")

if __name__ == '__main__':
    unittest.main()
