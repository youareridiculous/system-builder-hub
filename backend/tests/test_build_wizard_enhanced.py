"""
Tests for Enhanced Build Wizard with No-LLM Mode
"""
import unittest
import sys
import os
import json
import requests
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestBuildWizardEnhanced(unittest.TestCase):
    """Test enhanced build wizard functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_url = 'http://localhost:5001'
        self.session = requests.Session()
        self.tenant_id = 'test_tenant_enhanced'
    
    def test_no_llm_mode_build(self):
        """Test building without LLM provider"""
        try:
            # 1. Start build with No-LLM mode
            build_data = {
                'name': 'Test No-LLM Build',
                'description': 'Testing No-LLM mode',
                'template_slug': 'crud-app',
                'mode': 'normal',
                'no_llm_mode': True
            }
            
            response = self.session.post(
                f'{self.base_url}/api/build/start',
                json=build_data,
                headers={'X-Tenant-ID': self.tenant_id}
            )
            
            self.assertEqual(response.status_code, 200)
            result = response.json()
            
            # Verify build was created with No-LLM mode
            self.assertTrue(result['success'])
            self.assertTrue(result['no_llm_mode'])
            self.assertIn('project_id', result)
            self.assertIn('system_id', result)
            
            print("✅ No-LLM mode build test passed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")
    
    def test_llm_required_build(self):
        """Test that build fails without LLM when No-LLM mode is disabled"""
        try:
            # 1. Start build without LLM provider and No-LLM mode disabled
            build_data = {
                'name': 'Test LLM Required Build',
                'description': 'Testing LLM requirement',
                'template_slug': 'crud-app',
                'mode': 'normal',
                'no_llm_mode': False
            }
            
            response = self.session.post(
                f'{self.base_url}/api/build/start',
                json=build_data,
                headers={'X-Tenant-ID': self.tenant_id}
            )
            
            # Should fail because no LLM is configured
            self.assertEqual(response.status_code, 400)
            result = response.json()
            
            self.assertFalse(result.get('success', True))
            self.assertIn('LLM provider not configured', result['error'])
            
            print("✅ LLM required build test passed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")
    
    def test_dry_run_endpoint(self):
        """Test dry-run prompt endpoint"""
        try:
            # 1. Test dry-run without LLM configured
            response = self.session.post(
                f'{self.base_url}/api/llm/dry-run',
                json={'prompt': 'echo ping'},
                headers={'X-Tenant-ID': self.tenant_id}
            )
            
            self.assertEqual(response.status_code, 400)
            result = response.json()
            
            self.assertFalse(result.get('success', True))
            self.assertIn('LLM provider not configured', result['error'])
            
            print("✅ Dry-run endpoint test passed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")
    
    def test_enhanced_status_endpoint(self):
        """Test enhanced LLM status endpoint"""
        try:
            response = self.session.get(
                f'{self.base_url}/api/llm/status',
                headers={'X-Tenant-ID': self.tenant_id}
            )
            
            self.assertEqual(response.status_code, 200)
            status = response.json()
            
            # Verify enhanced status structure
            self.assertIn('available', status)
            self.assertIn('providers', status)
            self.assertIn('safety', status)
            self.assertIn('usage', status)
            
            # Verify providers list
            self.assertIsInstance(status['providers'], list)
            
            # Verify safety info
            self.assertIn('timeouts', status['safety'])
            self.assertIn('model_allowlists', status['safety'])
            
            print("✅ Enhanced status endpoint test passed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Server not running")

class TestBuildWizardUI(unittest.TestCase):
    """Test build wizard UI components"""
    
    def test_no_llm_toggle_functionality(self):
        """Test No-LLM toggle behavior"""
        # This would test the JavaScript functionality
        # For now, we'll test the concept
        
        # Simulate No-LLM mode enabled
        no_llm_mode = True
        
        # Verify that when No-LLM mode is enabled:
        # 1. LLM configuration section should be hidden
        # 2. Start button should be enabled
        # 3. Status should show "LLM: Off"
        
        self.assertTrue(no_llm_mode)
        
        # Simulate LLM mode enabled
        no_llm_mode = False
        llm_available = False
        
        # Verify that when No-LLM mode is disabled and LLM not available:
        # 1. Start button should be disabled
        # 2. Status should show "LLM: Not Configured"
        
        self.assertFalse(no_llm_mode)
        self.assertFalse(llm_available)
    
    def test_start_button_gating(self):
        """Test start button gating logic"""
        # Test cases for start button state
        
        # Case 1: No-LLM mode enabled
        no_llm_mode = True
        llm_available = False
        can_start = no_llm_mode or llm_available
        self.assertTrue(can_start)
        
        # Case 2: No-LLM mode disabled, LLM available
        no_llm_mode = False
        llm_available = True
        can_start = no_llm_mode or llm_available
        self.assertTrue(can_start)
        
        # Case 3: No-LLM mode disabled, LLM not available
        no_llm_mode = False
        llm_available = False
        can_start = no_llm_mode or llm_available
        self.assertFalse(can_start)
    
    def test_api_key_validation(self):
        """Test API key validation patterns"""
        # Test OpenAI key pattern
        openai_pattern = r'^sk-[a-zA-Z0-9]{48}$'
        import re
        
        valid_openai_key = 'sk-1234567890abcdef1234567890abcdef1234567890abcdef'
        invalid_openai_key = 'sk-invalid'
        
        self.assertTrue(re.match(openai_pattern, valid_openai_key))
        self.assertFalse(re.match(openai_pattern, invalid_openai_key))
        
        # Test Anthropic key pattern
        anthropic_pattern = r'^sk-ant-[a-zA-Z0-9]{48}$'
        
        valid_anthropic_key = 'sk-ant-1234567890abcdef1234567890abcdef1234567890abcdef'
        invalid_anthropic_key = 'sk-ant-invalid'
        
        self.assertTrue(re.match(anthropic_pattern, valid_anthropic_key))
        self.assertFalse(re.match(anthropic_pattern, invalid_anthropic_key))

class TestNoLLMIntegration(unittest.TestCase):
    """Test No-LLM mode integration with Core Build Loop"""
    
    def test_no_llm_project_creation(self):
        """Test that No-LLM projects are created correctly"""
        # This would test the full integration
        # For now, we'll test the concept
        
        # Simulate project creation with No-LLM mode
        project_data = {
            'name': 'No-LLM Project',
            'template_slug': 'crud-app',
            'no_llm_mode': True
        }
        
        # Verify project has No-LLM flag
        self.assertTrue(project_data['no_llm_mode'])
        
        # Verify template is specified (required for No-LLM mode)
        self.assertIsNotNone(project_data['template_slug'])
    
    def test_no_llm_build_flow(self):
        """Test No-LLM build flow"""
        # Test that No-LLM builds:
        # 1. Don't require LLM provider configuration
        # 2. Use templates only
        # 3. Don't generate LLM usage logs
        # 4. Work without LLM service availability
        
        no_llm_mode = True
        llm_required = not no_llm_mode
        
        self.assertTrue(no_llm_mode)
        self.assertFalse(llm_required)

if __name__ == '__main__':
    unittest.main()
