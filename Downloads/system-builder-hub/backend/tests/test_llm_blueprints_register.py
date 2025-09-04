"""
Test LLM blueprint registration
"""
import unittest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestLLMBlueprintRegistration(unittest.TestCase):
    """Test that LLM blueprints register correctly"""
    
    def test_llm_blueprints_import(self):
        """Test that LLM blueprints can be imported"""
        try:
            from llm_config_api import llm_config_bp
            from llm_status_api import bp as llm_status_bp
            from llm_dry_run_api import llm_dry_run_bp
            print("✅ All LLM blueprints imported successfully")
        except Exception as e:
            self.fail(f"Failed to import LLM blueprints: {e}")
    
    def test_llm_blueprints_have_routes(self):
        """Test that LLM blueprints have the expected routes"""
        from llm_config_api import llm_config_bp
        from llm_status_api import bp as llm_status_bp
        from llm_dry_run_api import llm_dry_run_bp
        
        # Check that blueprints have routes
        self.assertTrue(len(llm_config_bp.deferred_functions) > 0)
        self.assertTrue(len(llm_status_bp.deferred_functions) > 0)
        self.assertTrue(len(llm_dry_run_bp.deferred_functions) > 0)
    
    def test_app_registration_in_dev(self):
        """Test that LLM blueprints register in development"""
        os.environ['FLASK_ENV'] = 'development'
        
        try:
            from app import create_app
            app = create_app()
            
            # Check that LLM routes are registered
            llm_routes = [rule.rule for rule in app.url_map.iter_rules() if rule.rule.startswith("/api/llm")]
            print(f"✅ Found LLM routes: {llm_routes}")
            
            # Should have at least some LLM routes
            self.assertGreater(len(llm_routes), 0)
            
        except Exception as e:
            self.fail(f"Failed to register LLM blueprints in development: {e}")

if __name__ == '__main__':
    unittest.main()
