"""
LLM provider tests
"""
import unittest
from unittest.mock import patch, MagicMock
from src.llm.providers import LLMProviderManager, OpenAIProvider, AnthropicProvider, LocalStubProvider
from src.llm.schema import LLMRequest, LLMMessage

class TestLLMProviders(unittest.TestCase):
    """Test LLM providers"""
    
    def setUp(self):
        """Set up test environment"""
        self.provider_manager = LLMProviderManager()
    
    def test_local_stub_provider_always_configured(self):
        """Test local stub provider is always configured"""
        provider = LocalStubProvider()
        self.assertTrue(provider.is_configured())
    
    def test_local_stub_provider_completion(self):
        """Test local stub provider completion"""
        provider = LocalStubProvider()
        request = LLMRequest(
            model='stub-model',
            messages=[
                LLMMessage(role='user', content='Hello, world!')
            ]
        )
        
        response = provider.complete(request)
        
        self.assertIsNotNone(response)
        self.assertIsInstance(response.text, str)
        self.assertIn('Hello, world!', response.text)
        self.assertIsNotNone(response.usage)
    
    def test_local_stub_provider_json_mode(self):
        """Test local stub provider with JSON mode"""
        provider = LocalStubProvider()
        request = LLMRequest(
            model='stub-model',
            messages=[
                LLMMessage(role='user', content='Generate JSON')
            ],
            json_mode=True
        )
        
        response = provider.complete(request)
        
        self.assertIsNotNone(response)
        self.assertIsInstance(response.text, str)
        # Should contain JSON structure
        self.assertIn('"response"', response.text)
    
    def test_provider_manager_get_provider(self):
        """Test provider manager get provider"""
        # Test with valid provider
        provider = self.provider_manager.get_provider('local-stub')
        self.assertIsInstance(provider, LocalStubProvider)
        
        # Test with invalid provider (should fallback to local-stub)
        provider = self.provider_manager.get_provider('invalid-provider')
        self.assertIsInstance(provider, LocalStubProvider)
    
    def test_provider_manager_get_all_providers(self):
        """Test provider manager get all providers"""
        providers = self.provider_manager.get_all_providers()
        
        self.assertIsInstance(providers, list)
        self.assertGreater(len(providers), 0)
        
        # Check that all providers have required fields
        for provider_info in providers:
            self.assertIn('name', provider_info.to_dict())
            self.assertIn('configured', provider_info.to_dict())
            self.assertIn('ok', provider_info.to_dict())
    
    def test_provider_manager_test_providers(self):
        """Test provider manager test providers"""
        results = self.provider_manager.test_providers()
        
        self.assertIsInstance(results, dict)
        self.assertIn('local-stub', results)
        
        # Local stub should be configured and ok
        stub_result = results['local-stub']
        self.assertTrue(stub_result['configured'])
        self.assertTrue(stub_result['ok'])
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_openai_provider_configured(self):
        """Test OpenAI provider configuration"""
        provider = OpenAIProvider()
        self.assertTrue(provider.is_configured())
    
    @patch.dict('os.environ', {})
    def test_openai_provider_not_configured(self):
        """Test OpenAI provider not configured"""
        provider = OpenAIProvider()
        self.assertFalse(provider.is_configured())
    
    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'})
    def test_anthropic_provider_configured(self):
        """Test Anthropic provider configuration"""
        provider = AnthropicProvider()
        self.assertTrue(provider.is_configured())
    
    @patch.dict('os.environ', {})
    def test_anthropic_provider_not_configured(self):
        """Test Anthropic provider not configured"""
        provider = AnthropicProvider()
        self.assertFalse(provider.is_configured())

if __name__ == '__main__':
    unittest.main()
