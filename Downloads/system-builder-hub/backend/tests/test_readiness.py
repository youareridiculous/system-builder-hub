"""
Test readiness endpoint with new LLM-optional semantics
"""
import unittest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestReadiness(unittest.TestCase):
    """Test readiness endpoint with new semantics"""
    
    def setUp(self):
        """Set up test environment"""
        self.old_env = os.environ.copy()
        os.environ.clear()
        os.environ['FLASK_ENV'] = 'development'
        os.environ['LLM_SECRET_KEY'] = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.old_env)
    
    def test_readiness_no_llm_configured_returns_200(self):
        """Test readiness when no LLM is configured - should return 200"""
        try:
            from app import create_app
            app = create_app()
            app.config.update({"FEATURE_LLM_API": True, "OPENAI_API_KEY": None})
            
            with app.test_client() as client:
                response = client.get("/readiness")
                self.assertEqual(response.status_code, 200)
                
                data = response.get_json()
                self.assertIn("db", data)
                self.assertTrue(data["db"])
                self.assertIn("migrations_applied", data)
                self.assertIn("llm", data)
                
                llm = data["llm"]
                self.assertFalse(llm["configured"])
                self.assertFalse(llm["ok"])
                self.assertIn(llm["details"], ["not_configured", "disabled"])
                
        except Exception as e:
            self.fail(f"Readiness test failed: {e}")
    
    def test_readiness_llm_disabled_reports_disabled(self):
        """Test readiness when LLM is disabled via feature flag"""
        try:
            from app import create_app
            app = create_app()
            app.config.update({"FEATURE_LLM_API": False})
            
            with app.test_client() as client:
                response = client.get("/readiness")
                self.assertEqual(response.status_code, 200)
                
                data = response.get_json()
                self.assertTrue(data["db"])
                self.assertEqual(data["llm"]["details"], "disabled")
                self.assertFalse(data["llm"]["configured"])
                self.assertFalse(data["llm"]["ok"])
                
        except Exception as e:
            self.fail(f"Readiness test failed: {e}")
    
    def test_llm_status_always_200(self):
        """Test that LLM status endpoint always returns 200"""
        try:
            from app import create_app
            app = create_app()
            app.config.update({"FEATURE_LLM_API": True, "OPENAI_API_KEY": None})
            
            with app.test_client() as client:
                response = client.get("/api/llm/status")
                self.assertEqual(response.status_code, 200)
                
                data = response.get_json()
                self.assertIn("configured", data)
                self.assertFalse(data["configured"])
                self.assertIn("providers", data)
                self.assertIsInstance(data["providers"], list)
                
        except Exception as e:
            self.fail(f"LLM status test failed: {e}")
    
    def test_llm_status_disabled_feature(self):
        """Test LLM status when feature is disabled"""
        try:
            from app import create_app
            app = create_app()
            app.config.update({"FEATURE_LLM_API": False})
            
            with app.test_client() as client:
                response = client.get("/api/llm/status")
                self.assertEqual(response.status_code, 200)
                
                data = response.get_json()
                self.assertFalse(data["configured"])
                self.assertEqual(data["details"], "disabled")
                self.assertEqual(len(data["providers"]), 0)
                
        except Exception as e:
            self.fail(f"LLM status disabled test failed: {e}")
    
    def test_readiness_db_failure_returns_503(self):
        """Test readiness when database is not accessible"""
        try:
            from app import create_app
            app = create_app()
            # Set an invalid database path
            app.config.update({"DATABASE": "/nonexistent/path/app.db"})
            
            with app.test_client() as client:
                response = client.get("/readiness")
                self.assertEqual(response.status_code, 503)
                
                data = response.get_json()
                self.assertFalse(data["db"])
                
        except Exception as e:
            self.fail(f"Readiness DB failure test failed: {e}")

if __name__ == '__main__':
    unittest.main()
