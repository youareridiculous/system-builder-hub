"""
Integration Tests for LLM Connection Validation
Tests the complete flow from UI to backend
"""
import unittest
import sys
import os
import json
import requests
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestLLMIntegration(unittest.TestCase):
    """Integration tests for LLM connection validation"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_url = 'http://localhost:5001'
        self.session = requests.Session()
    
    def test_llm_status_endpoint(self):
        """Test LLM status endpoint"""
        try:
            response = self.session.get(f'{self.base_url}/api/llm/provider/status')
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn('available', data)
            self.assertIn('provider', data)
            self.assertIn('model', data)
            
            print(f"✅ LLM Status: {data}")
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")
    
    def test_llm_test_endpoint(self):
        """Test LLM test endpoint"""
        try:
            # Test without API key (should fail gracefully)
            response = self.session.post(f'{self.base_url}/api/llm/test')
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn('ok', data)
            self.assertFalse(data['ok'])  # Should fail without API key
            
            print(f"✅ LLM Test (no key): {data}")
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")
    
    def test_llm_configure_endpoint(self):
        """Test LLM configuration endpoint"""
        try:
            # Test configuration with invalid data
            response = self.session.post(
                f'{self.base_url}/api/llm/provider/configure',
                json={'provider': 'openai', 'api_key': ''}
            )
            self.assertEqual(response.status_code, 400)
            
            data = response.json()
            self.assertIn('error', data)
            self.assertIn('API key required', data['error'])
            
            print(f"✅ LLM Configure (invalid): {data}")
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")
    
    def test_templates_endpoint(self):
        """Test templates endpoint"""
        try:
            response = self.session.get(f'{self.base_url}/api/build/templates')
            self.assertEqual(response.status_code, 200)
            
            templates = response.json()
            self.assertIsInstance(templates, list)
            self.assertGreater(len(templates), 0)
            
            # Check template structure
            for template in templates:
                self.assertIn('slug', template)
                self.assertIn('name', template)
                self.assertIn('description', template)
            
            print(f"✅ Templates loaded: {len(templates)} templates")
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")
    
    def test_build_start_endpoint(self):
        """Test build start endpoint"""
        try:
            # Test with valid project data
            response = self.session.post(
                f'{self.base_url}/api/build/start',
                json={'name': 'Test Project', 'description': 'Test description'}
            )
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn('project_id', data)
            self.assertIn('system_id', data)
            
            print(f"✅ Build Start: {data}")
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")
    
    def test_health_endpoint(self):
        """Test health endpoint"""
        try:
            response = self.session.get(f'{self.base_url}/healthz')
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn('status', data)
            self.assertEqual(data['status'], 'healthy')
            self.assertIn('mode', data)
            
            print(f"✅ Health Check: {data}")
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")

class TestLLMConnectionFlow(unittest.TestCase):
    """Test complete LLM connection flow"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_url = 'http://localhost:5001'
        self.session = requests.Session()
    
    def test_complete_llm_flow(self):
        """Test complete LLM connection flow"""
        try:
            # 1. Check initial status
            response = self.session.get(f'{self.base_url}/api/llm/provider/status')
            initial_status = response.json()
            print(f"Initial status: {initial_status}")
            
            # 2. Test connection without API key
            response = self.session.post(f'{self.base_url}/api/llm/test')
            test_result = response.json()
            print(f"Test result: {test_result}")
            
            # 3. Try to configure with empty API key
            response = self.session.post(
                f'{self.base_url}/api/llm/provider/configure',
                json={'provider': 'openai', 'api_key': '', 'default_model': 'gpt-3.5-turbo'}
            )
            config_result = response.json()
            print(f"Config result: {config_result}")
            
            # 4. Check final status
            response = self.session.get(f'{self.base_url}/api/llm/provider/status')
            final_status = response.json()
            print(f"Final status: {final_status}")
            
            # Assertions
            self.assertFalse(initial_status['available'])
            self.assertFalse(test_result['ok'])
            self.assertEqual(config_result.get('error'), 'Provider and API key required')
            self.assertFalse(final_status['available'])
            
            print("✅ Complete LLM flow test passed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")

if __name__ == '__main__':
    unittest.main()
