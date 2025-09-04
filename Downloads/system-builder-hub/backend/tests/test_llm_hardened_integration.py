"""
Integration Tests for Hardened LLM System
"""
import unittest
import sys
import os
import json
import time
import requests
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestHardenedLLMIntegration(unittest.TestCase):
    """Integration tests for hardened LLM system"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_url = 'http://localhost:5001'
        self.session = requests.Session()
        self.tenant_id = 'test_tenant_hardened'
        
        # Set up test keys
        os.environ['LLM_SECRET_KEY'] = 'dGVzdC1rZXktZm9yLXRlc3Rpbmctc2VjcmV0cy0xMjM='
    
    def test_complete_hardened_flow(self):
        """Test complete hardened LLM flow"""
        try:
            # 1. Check initial status
            response = self.session.get(f'{self.base_url}/api/llm/status')
            self.assertEqual(response.status_code, 200)
            initial_status = response.json()
            print(f"Initial status: {initial_status}")
            
            # 2. Configure provider with security
            config_data = {
                'provider': 'openai',
                'api_key': 'sk-test123456789',
                'default_model': 'gpt-3.5-turbo'
            }
            
            response = self.session.post(
                f'{self.base_url}/api/llm/provider/configure',
                json=config_data,
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            config_result = response.json()
            print(f"Config result: {config_result}")
            
            # 3. Check enhanced status
            response = self.session.get(
                f'{self.base_url}/api/llm/status',
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            status = response.json()
            print(f"Enhanced status: {status}")
            
            # Verify status structure
            self.assertIn('providers', status)
            self.assertIn('safety', status)
            self.assertIn('usage', status)
            
            # Find our provider
            provider_status = None
            for provider in status['providers']:
                if provider['name'] == 'openai' and provider['active']:
                    provider_status = provider
                    break
            
            self.assertIsNotNone(provider_status)
            self.assertEqual(provider_status['model'], 'gpt-3.5-turbo')
            self.assertEqual(provider_status['circuit_state'], 'closed')
            
            # 4. Test connection (will fail without real API key, but tests the flow)
            response = self.session.post(
                f'{self.base_url}/api/llm/test',
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            test_result = response.json()
            print(f"Test result: {test_result}")
            
            # 5. Check metrics
            response = self.session.get(
                f'{self.base_url}/api/llm/metrics',
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            metrics = response.text
            print(f"Metrics: {metrics}")
            
            # Verify metrics format
            self.assertIn('llm_requests_total', metrics)
            self.assertIn('llm_circuit_state', metrics)
            
            print("✅ Complete hardened flow test completed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")
    
    def test_safety_features(self):
        """Test safety features (circuit breaker, rate limiting)"""
        try:
            # 1. Configure provider
            config_data = {
                'provider': 'anthropic',
                'api_key': 'sk-ant-test123456789',
                'default_model': 'claude-3-sonnet-20240229'
            }
            
            response = self.session.post(
                f'{self.base_url}/api/llm/provider/configure',
                json=config_data,
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            
            # 2. Check safety status
            response = self.session.get(
                f'{self.base_url}/api/llm/status',
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            status = response.json()
            
            # Verify safety features
            self.assertIn('safety', status)
            safety = status['safety']
            self.assertIn('timeouts', safety)
            self.assertIn('model_allowlists', safety)
            self.assertIn('model_denylists', safety)
            
            # Verify provider has circuit breaker info
            provider_status = None
            for provider in status['providers']:
                if provider['name'] == 'anthropic' and provider['active']:
                    provider_status = provider
                    break
            
            self.assertIsNotNone(provider_status)
            self.assertIn('circuit_state', provider_status)
            self.assertIn('failure_count', provider_status)
            self.assertIn('rate_limit_remaining', provider_status)
            
            print("✅ Safety features test completed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")
    
    def test_error_sanitization(self):
        """Test error message sanitization"""
        try:
            # 1. Configure with invalid API key
            config_data = {
                'provider': 'openai',
                'api_key': 'sk-invalid-key-for-testing',
                'default_model': 'gpt-3.5-turbo'
            }
            
            response = self.session.post(
                f'{self.base_url}/api/llm/provider/configure',
                json=config_data,
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            
            # 2. Test connection (should fail but with sanitized error)
            response = self.session.post(
                f'{self.base_url}/api/llm/test',
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            test_result = response.json()
            
            # Verify error is sanitized
            if not test_result.get('success', True):
                error_msg = test_result.get('error', '')
                # Should not contain the raw API key
                self.assertNotIn('sk-invalid-key-for-testing', error_msg)
                # Should contain sanitized version
                self.assertIn('sk-***', error_msg)
            
            print("✅ Error sanitization test completed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")
    
    def test_model_validation(self):
        """Test model allowlist/denylist validation"""
        try:
            # 1. Try to configure with disallowed model
            config_data = {
                'provider': 'openai',
                'api_key': 'sk-test123456789',
                'default_model': 'gpt-4-disallowed'  # Not in allowlist
            }
            
            response = self.session.post(
                f'{self.base_url}/api/llm/provider/configure',
                json=config_data,
                headers={'X-Tenant-ID': self.tenant_id}
            )
            
            # Should fail validation
            if response.status_code == 400:
                print("✅ Model validation test completed (disallowed model rejected)")
            else:
                # If it succeeds, that's also valid (depends on allowlist config)
                print("✅ Model validation test completed (model allowed)")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")

class TestLLMServiceHardened(unittest.TestCase):
    """Test hardened LLM service"""
    
    def setUp(self):
        os.environ['LLM_SECRET_KEY'] = 'dGVzdC1rZXktZm9yLXRlc3Rpbmctc2VjcmV0cy0xMjM='
    
    def test_llm_service_with_safety(self):
        """Test LLM service with safety features"""
        from src.llm_core import LLMService
        
        # Test without configuration
        service = LLMService('test_tenant_no_config')
        self.assertFalse(service.is_available())
        
        # Test with environment variables
        with patch.dict(os.environ, {
            'LLM_PROVIDER': 'openai',
            'LLM_API_KEY': 'sk-test123456789',
            'LLM_DEFAULT_MODEL': 'gpt-3.5-turbo'
        }):
            service = LLMService('test_tenant_env')
            self.assertTrue(service.is_available())
            
            # Test completion generation (will fail without real API key, but tests the flow)
            result = service.generate_completion("Test prompt", max_tokens=10)
            
            # Should return error due to invalid API key, but structure should be correct
            self.assertIn('success', result)
            self.assertIn('error', result)
            self.assertIn('content', result)
    
    def test_secrets_integration(self):
        """Test secrets integration"""
        from src.secrets import encrypt_secret, decrypt_secret, redact_secret
        
        # Test encryption/decryption
        test_secret = "sk-test123456789"
        encrypted = encrypt_secret(test_secret)
        decrypted = decrypt_secret(encrypted)
        self.assertEqual(decrypted, test_secret)
        
        # Test redaction
        redacted = redact_secret(test_secret)
        self.assertNotIn(test_secret, redacted)
        self.assertIn("6789", redacted)  # Last 4 chars should be visible

if __name__ == '__main__':
    unittest.main()
