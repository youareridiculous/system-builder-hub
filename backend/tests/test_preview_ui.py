"""
Test Preview UI endpoints
"""
import unittest
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestPreviewUI(unittest.TestCase):
    """Test preview UI endpoints"""
    
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
    
    def test_preview_direct_page(self):
        """Test that GET /ui/hello-page returns 200"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                response = client.get('/ui/hello-page')
                
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Hello World", response.data)
                self.assertIn(b"Hello World", response.data)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_preview_by_project(self):
        """Test that generate for project -> GET /preview/<pid> returns 200"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-preview-123'
                
                # First generate a build
                generate_response = client.post('/api/builder/generate-build',
                                              json={'project_id': project_id})
                self.assertEqual(generate_response.status_code, 200)
                
                # Then check the preview page
                preview_response = client.get(f'/preview/{project_id}')
                self.assertEqual(preview_response.status_code, 200)
                self.assertIn(b'Preview Index', preview_response.data)
                self.assertIn(project_id.encode(), preview_response.data)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_preview_missing(self):
        """Test that missing page returns 404 JSON with available pages"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                response = client.get('/ui/nonexistent-page')
                
                self.assertEqual(response.status_code, 404)
                data = json.loads(response.data)
                
                self.assertIn('error', data)
                self.assertIn('available_templates', data)
                self.assertIsInstance(data['available_templates'], list)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_preview_index(self):
        """Test that /preview returns index page"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                response = client.get('/preview')
                
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Preview Index', response.data)
                
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    def test_builder_generate_returns_correct_preview_urls(self):
        """Test that builder generate returns correct preview URLs"""
        try:
            from app import create_app
            app = create_app()
            
            with app.test_client() as client:
                project_id = 'test-project-urls-123'
                
                response = client.post('/api/builder/generate-build',
                                     json={'project_id': project_id})
                
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                
                # Should have both preview URLs
                self.assertIn('preview_url', data)
                self.assertIn('preview_url_project', data)
                
                # Check format
                self.assertTrue(data['preview_url'].startswith('/ui/'))
                self.assertEqual(data['preview_url_project'], f'/preview/{project_id}')
                
        except Exception as e:
            self.fail(f"Test failed: {e}")

if __name__ == '__main__':
    unittest.main()
