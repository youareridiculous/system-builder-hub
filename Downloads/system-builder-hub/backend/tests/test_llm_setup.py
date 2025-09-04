"""
Test LLM Provider Setup and Fallbacks
"""
import unittest
import os
import sys
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestLLMSetup(unittest.TestCase):
    """Test LLM setup and fallback functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Clear any existing LLM config
        if 'LLM_API_KEY' in os.environ:
            del os.environ['LLM_API_KEY']
        if 'LLM_PROVIDER' in os.environ:
            del os.environ['LLM_PROVIDER']
    
    def test_llm_availability_no_config(self):
        """Test LLM availability when no config is present"""
        from llm_core import LLMAvailability
        
        status = LLMAvailability.get_status()
        
        self.assertFalse(status['available'])
        self.assertIsNone(status['provider'])
        self.assertIsNone(status['model'])
        self.assertIn('api_key', status['missing'])
        self.assertIsNotNone(status['setup_hint'])
    
    def test_llm_config_creation(self):
        """Test LLM config creation"""
        from llm_core import LLMConfig
        
        config = LLMConfig('openai', 'test-key', 'gpt-3.5-turbo')
        
        self.assertTrue(config.is_configured())
        self.assertEqual(config.provider, 'openai')
        self.assertEqual(config.default_model, 'gpt-3.5-turbo')
    
    def test_llm_stub_questions(self):
        """Test LLM stub questions"""
        from llm_core import LLMStub
        
        questions = LLMStub.guided_questions()
        
        self.assertIsInstance(questions, list)
        self.assertGreater(len(questions), 0)
        self.assertTrue(all(isinstance(q, str) for q in questions))
    
    def test_llm_stub_blueprint_expansion(self):
        """Test LLM stub blueprint expansion"""
        from llm_core import LLMStub
        
        template = {
            'type': 'api',
            'entities': []
        }
        
        expanded = LLMStub.expand_blueprint(template)
        
        self.assertIn('notes', expanded)
        self.assertTrue(expanded['stubbed'])
        self.assertIsInstance(expanded['notes'], list)
    
    def test_llm_config_api_import(self):
        """Test LLM config API imports"""
        try:
            from llm_config_api import llm_config_bp
            self.assertIsNotNone(llm_config_bp)
        except ImportError as e:
            self.fail(f"Failed to import llm_config_api: {e}")
    
    def test_llm_metrics(self):
        """Test LLM metrics functionality"""
        from llm_metrics import LLMMetrics
        
        metrics = LLMMetrics()
        
        # Test recording
        metrics.record_setup_attempt('openai', True)
        metrics.record_llm_call('openai', 'gpt-3.5-turbo', 'guided', True)
        metrics.record_unavailable()
        metrics.record_test_latency(100)
        
        # Test retrieval
        data = metrics.get_metrics()
        
        self.assertEqual(data['setup_attempts_total'], 1)
        self.assertEqual(data['llm_calls_total'], 1)
        self.assertEqual(data['unavailable_total'], 1)
        self.assertEqual(data['test_latency_avg_ms'], 100)
    
    def test_llm_mode_detection(self):
        """Test LLM mode detection"""
        from llm_core import LLMAvailability
        
        # Test noop mode (no config)
        status = LLMAvailability.get_status()
        mode = 'noop' if not status['available'] else 'live'
        self.assertEqual(mode, 'noop')
        
        # Test live mode (with config)
        os.environ['LLM_API_KEY'] = 'test-key'
        os.environ['LLM_PROVIDER'] = 'openai'
        
        status = LLMAvailability.get_status()
        mode = 'noop' if not status['available'] else 'live'
        self.assertEqual(mode, 'live')

class TestLLMIntegration(unittest.TestCase):
    """Test LLM integration with Core Build Loop"""
    
    def test_guided_session_without_llm(self):
        """Test guided session behavior without LLM"""
        from llm_core import LLMAvailability
        
        # Ensure no LLM config
        if 'LLM_API_KEY' in os.environ:
            del os.environ['LLM_API_KEY']
        
        status = LLMAvailability.get_status()
        
        # Should return 409 with setup hint
        self.assertFalse(status['available'])
        self.assertIn('setup_hint', status)
        self.assertIn('required_keys', status)
    
    def test_template_build_without_llm(self):
        """Test template build works without LLM"""
        from templates_catalog import TEMPLATES
        
        # Template builds should work without LLM
        self.assertGreater(len(TEMPLATES), 0)
        
        for template in TEMPLATES:
            hasattr(template, 'slug')
            hasattr(template, 'name')
            hasattr(template, 'blueprint')

if __name__ == '__main__':
    unittest.main()
