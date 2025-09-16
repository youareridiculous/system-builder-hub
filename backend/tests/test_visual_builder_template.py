"""
Test Visual Builder Template
"""
import unittest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestVisualBuilderTemplate(unittest.TestCase):
    """Test visual builder template functionality"""
    
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
    
    def test_visual_builder_template_exists(self):
        """Test that GET /ui/visual-builder returns 200"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                response = client.get('/ui/visual-builder')
                
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'builder-app', response.data)
                self.assertIn(b'Visual Builder', response.data)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_visual_builder_with_project(self):
        """Test that GET /ui/visual-builder?project=<uuid> returns 200 and contains project ID"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-123'
                response = client.get(f'/ui/visual-builder?project={project_id}')
                
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'builder-app', response.data)
                self.assertIn(project_id.encode(), response.data)
                self.assertIn(b'window.SBH_PROJECT_ID', response.data)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_visual_builder_template_structure(self):
        """Test that template contains required elements"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                response = client.get('/ui/visual-builder')
                html = response.data.decode('utf-8')
                
                # Check for required elements
                self.assertIn('btn-save', html)
                self.assertIn('btn-generate', html)
                self.assertIn('btn-open-preview', html)
                self.assertIn('canvas', html)
                self.assertIn('palette', html)
                self.assertIn('props', html)
                
                # Check for script and CSS includes
                self.assertIn('visual_builder.js', html)
                self.assertIn('visual_builder.css', html)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")

if __name__ == '__main__':
    unittest.main()
