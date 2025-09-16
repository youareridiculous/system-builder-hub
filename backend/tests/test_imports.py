"""
Import test to catch SyntaxError/IndentationError in CI
"""
import unittest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestImports(unittest.TestCase):
    """Test that all modules can be imported without syntax errors"""
    
    def test_core_imports(self):
        """Test core module imports"""
        try:
            import app
            import config
            import sbh_secrets
            import llm_core
            import llm_config_api
            import llm_status_api
            import llm_dry_run_api
            import ui_guided
            import ui_build
            import ui_project_loader
            import ui_visual_builder
            print("✅ All core modules imported successfully")
        except Exception as e:
            self.fail(f"Failed to import core modules: {e}")
    
    def test_blueprint_imports(self):
        """Test blueprint imports"""
        try:
            from llm_config_api import llm_config_bp
            from llm_status_api import bp as llm_status_bp
            from llm_dry_run_api import llm_dry_run_bp
            from ui_guided import ui_guided_bp
            from ui_build import ui_build_bp
            from ui_project_loader import ui_project_loader_bp
            from ui_visual_builder import ui_visual_builder_bp
            print("✅ All blueprints imported successfully")
        except Exception as e:
            self.fail(f"Failed to import blueprints: {e}")
    
    def test_app_creation(self):
        """Test app creation"""
        try:
            from app import create_app
            app = create_app()
            self.assertIsNotNone(app)
            print("✅ App creation successful")
        except Exception as e:
            self.fail(f"Failed to create app: {e}")

if __name__ == '__main__':
    unittest.main()
