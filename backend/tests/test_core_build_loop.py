"""
Test Core Build Loop end-to-end
"""
import unittest
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app import app

class TestCoreBuildLoop(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_1_start_build_wizard(self):
        """Test Start a Build wizard"""
        # Test templates endpoint
        response = self.app.get('/api/build/templates')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('templates', data)
        self.assertGreater(len(data['templates']), 0)
        
        # Test build start
        build_data = {
            'name': 'Test Project',
            'description': 'Test project for build loop',
            'template_slug': 'crud-app',
            'mode': 'normal'
        }
        response = self.app.post('/api/build/start', 
                               data=json.dumps(build_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('project_id', data)
        self.assertIn('system_id', data)
        
        return data['project_id']

    def test_2_project_loader(self):
        """Test Project Loader"""
        # Test projects list
        response = self.app.get('/api/projects')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('projects', data)
        
        # Test project rename
        if data['projects']:
            project_id = data['projects'][0]['id']
            rename_data = {'project_id': project_id, 'name': 'Renamed Project'}
            response = self.app.post('/api/project/rename',
                                   data=json.dumps(rename_data),
                                   content_type='application/json')
            self.assertEqual(response.status_code, 200)

    def test_3_visual_builder(self):
        """Test Visual Builder"""
        # Create a project first
        project_id = self.test_1_start_build_wizard()
        
        # Test get builder state
        response = self.app.get(f'/api/builder/state?project_id={project_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('state', data)
        
        # Test save builder state
        save_data = {
            'project_id': project_id,
            'blueprint': {'type': 'test'},
            'canvas': [{'id': 1, 'type': 'rest-api', 'x': 100, 'y': 100}],
            'modules': []
        }
        response = self.app.post('/api/builder/save',
                               data=json.dumps(save_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('version', data)
        
        # Test generate build
        build_data = {'project_id': project_id}
        response = self.app.post('/api/builder/generate-build',
                               data=json.dumps(build_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('build_id', data)
        
        return data['build_id']

    def test_4_guided_session(self):
        """Test Guided Session"""
        # Test guided session commit
        session_id = 'test-session-123'
        commit_data = {'project_id': 'test-project-123'}
        response = self.app.post(f'/api/guided/commit/{session_id}',
                               data=json.dumps(commit_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_5_ui_routes(self):
        """Test UI routes are accessible"""
        routes = [
            '/ui/build',
            '/ui/project-loader', 
            '/ui/visual-builder',
            '/ui/preview'
        ]
        
        for route in routes:
            response = self.app.get(route)
            self.assertIn(response.status_code, [200, 302])  # 200 OK or 302 redirect

    def test_6_feature_router(self):
        """Test feature router redirects"""
        features = [
            'start-build',
            'open-preview',
            'project-loader',
            'visual-builder'
        ]
        
        for feature in features:
            response = self.app.get(f'/ui/feature/{feature}')
            self.assertIn(response.status_code, [200, 302])

if __name__ == '__main__':
    unittest.main()
