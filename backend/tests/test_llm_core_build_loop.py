"""
Integration Tests for LLM Core Build Loop Integration
Tests the complete flow from provider config to build execution
"""
import unittest
import sys
import os
import json
import requests
import time
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestLLMCoreBuildLoopIntegration(unittest.TestCase):
    """Integration tests for LLM Core Build Loop"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_url = 'http://localhost:5001'
        self.session = requests.Session()
        self.tenant_id = 'test_tenant'
    
    def test_complete_llm_flow(self):
        """Test complete LLM flow: config -> test -> build"""
        try:
            # 1. Check initial status
            response = self.session.get(f'{self.base_url}/api/llm/provider/status')
            self.assertEqual(response.status_code, 200)
            initial_status = response.json()
            print(f"Initial status: {initial_status}")
            
            # 2. Configure LLM provider
            config_data = {
                'provider': 'openai',
                'api_key': 'test-key-12345',
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
            
            # 3. Test connection
            response = self.session.post(
                f'{self.base_url}/api/llm/test',
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            test_result = response.json()
            print(f"Test result: {test_result}")
            
            # 4. Check updated status
            response = self.session.get(f'{self.base_url}/api/llm/provider/status')
            self.assertEqual(response.status_code, 200)
            updated_status = response.json()
            print(f"Updated status: {updated_status}")
            
            # 5. Start a build (should use configured LLM)
            build_data = {
                'name': 'Test LLM Build',
                'description': 'Testing LLM integration',
                'template_slug': 'crud-app'
            }
            
            response = self.session.post(
                f'{self.base_url}/api/build/start',
                json=build_data,
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            build_result = response.json()
            print(f"Build result: {build_result}")
            
            # Assertions
            self.assertTrue(config_result['success'])
            self.assertIn('config_id', config_result)
            self.assertEqual(config_result['provider'], 'openai')
            
            # Note: Test will fail without real API key, but we can verify the flow
            print("✅ Complete LLM flow test completed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")
    
    def test_llm_persistence(self):
        """Test that LLM config persists across requests"""
        try:
            # 1. Configure provider
            config_data = {
                'provider': 'anthropic',
                'api_key': 'test-key-persist',
                'default_model': 'claude-3-sonnet-20240229'
            }
            
            response = self.session.post(
                f'{self.base_url}/api/llm/provider/configure',
                json=config_data,
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            
            # 2. Check status immediately
            response = self.session.get(
                f'{self.base_url}/api/llm/provider/status',
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            status1 = response.json()
            
            # 3. Wait and check status again
            time.sleep(1)
            response = self.session.get(
                f'{self.base_url}/api/llm/provider/status',
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            status2 = response.json()
            
            # 4. Verify persistence
            self.assertEqual(status1['provider'], status2['provider'])
            self.assertEqual(status1['model'], status2['model'])
            self.assertEqual(status1['available'], status2['available'])
            
            print("✅ LLM persistence test passed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")
    
    def test_llm_usage_logging(self):
        """Test that LLM usage is logged"""
        try:
            # 1. Configure provider
            config_data = {
                'provider': 'groq',
                'api_key': 'test-key-usage',
                'default_model': 'llama2-70b-4096'
            }
            
            response = self.session.post(
                f'{self.base_url}/api/llm/provider/configure',
                json=config_data,
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            
            # 2. Test connection (should log usage)
            response = self.session.post(
                f'{self.base_url}/api/llm/test',
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            
            # 3. Get usage stats
            response = self.session.get(
                f'{self.base_url}/api/llm/usage/stats',
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            stats = response.json()
            
            # 4. Verify usage logging
            self.assertIn('total_calls', stats)
            self.assertIn('successful_calls', stats)
            self.assertIn('provider_breakdown', stats)
            
            print(f"✅ Usage logging test passed: {stats['total_calls']} calls logged")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")
    
    def test_llm_startup_validation(self):
        """Test LLM startup validation"""
        try:
            # 1. Configure a provider
            config_data = {
                'provider': 'openai',
                'api_key': 'test-key-startup',
                'default_model': 'gpt-3.5-turbo'
            }
            
            response = self.session.post(
                f'{self.base_url}/api/llm/provider/configure',
                json=config_data,
                headers={'X-Tenant-ID': self.tenant_id}
            )
            self.assertEqual(response.status_code, 200)
            
            # 2. Check health endpoint for validation info
            response = self.session.get(f'{self.base_url}/healthz')
            self.assertEqual(response.status_code, 200)
            health = response.json()
            
            # 3. Verify health includes LLM info
            self.assertIn('status', health)
            self.assertEqual(health['status'], 'healthy')
            
            print("✅ Startup validation test passed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")

class TestLLMServiceIntegration(unittest.TestCase):
    """Test LLM service integration with Core Build Loop"""
    
    def test_llm_service_availability(self):
        """Test LLM service availability check"""
        from src.llm_core import LLMService
        
        # Test without configuration
        service = LLMService('test_tenant_no_config')
        self.assertFalse(service.is_available())
        
        # Test with environment variables
        with patch.dict(os.environ, {
            'LLM_PROVIDER': 'openai',
            'LLM_API_KEY': 'test-key',
            'LLM_DEFAULT_MODEL': 'gpt-3.5-turbo'
        }):
            service = LLMService('test_tenant_env')
            self.assertTrue(service.is_available())
    
    def test_llm_completion_generation(self):
        """Test LLM completion generation"""
        from src.llm_core import LLMService
        
        # Mock LLM service for testing
        with patch.dict(os.environ, {
            'LLM_PROVIDER': 'openai',
            'LLM_API_KEY': 'test-key',
            'LLM_DEFAULT_MODEL': 'gpt-3.5-turbo'
        }):
            service = LLMService('test_tenant')
            
            # Test completion generation (will fail without real API key, but tests the flow)
            result = service.generate_completion("Test prompt", max_tokens=10)
            
            # Should return error due to invalid API key, but structure should be correct
            self.assertIn('success', result)
            self.assertIn('error', result)
            self.assertIn('content', result)
    
    def test_llm_stub_functionality(self):
        """Test LLM stub functionality for no-LLM mode"""
        from src.llm_core import LLMStub
        
        # Test guided questions
        questions = LLMStub.guided_questions()
        self.assertIsInstance(questions, list)
        self.assertGreater(len(questions), 0)
        
        # Test blueprint expansion
        template = {'type': 'api', 'entities': []}
        expanded = LLMStub.expand_blueprint(template)
        self.assertIn('notes', expanded)
        self.assertTrue(expanded['stubbed'])

if __name__ == '__main__':
    unittest.main()
