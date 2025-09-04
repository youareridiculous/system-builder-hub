"""
Export API tests
"""
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from src.app import create_app
from src.exporter.service import ExportService
from src.vcs.github_service import GitHubService

class TestExportAPI(unittest.TestCase):
    """Test export API endpoints"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['FEATURE_EXPORT'] = True
        self.app.config['FEATURE_EXPORT_GITHUB'] = True
        self.client = self.app.test_client()
    
    def test_plan_returns_manifest_and_diff(self):
        """Test plan endpoint returns manifest"""
        with self.app.app_context():
            with patch.object(ExportService, 'materialize_build') as mock_materialize:
                # Mock bundle
                mock_bundle = MagicMock()
                mock_bundle.manifest.to_dict.return_value = {
                    'project_id': 'test-project',
                    'files': [],
                    'total_size': 0
                }
                mock_bundle.manifest.files = []
                mock_bundle.manifest.total_size = 0
                mock_materialize.return_value = mock_bundle
                
                response = self.client.post('/api/export/plan', json={
                    'project_id': 'test-project',
                    'include_runtime': True
                })
                
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertTrue(data['success'])
                self.assertIn('manifest', data['data'])
    
    def test_archive_streams_zip_download(self):
        """Test archive endpoint streams ZIP download"""
        with self.app.app_context():
            with patch.object(ExportService, 'materialize_build') as mock_materialize:
                with patch.object(ExportService, 'zip_bundle') as mock_zip:
                    # Mock bundle and ZIP
                    mock_bundle = MagicMock()
                    mock_bundle.manifest.files = []
                    mock_bundle.manifest.total_size = 0
                    mock_materialize.return_value = mock_bundle
                    
                    mock_zip_buffer = MagicMock()
                    mock_zip_buffer.getbuffer.return_value.nbytes = 1000
                    mock_zip.return_value = mock_zip_buffer
                    
                    response = self.client.post('/api/export/archive', json={
                        'project_id': 'test-project',
                        'include_runtime': True
                    })
                    
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.mimetype, 'application/zip')
    
    def test_github_sync_dry_run_ok(self):
        """Test GitHub sync dry run"""
        with self.app.app_context():
            with patch.object(ExportService, 'materialize_build') as mock_materialize:
                # Mock bundle
                mock_bundle = MagicMock()
                mock_bundle.manifest.files = []
                mock_bundle.manifest.total_size = 0
                mock_materialize.return_value = mock_bundle
                
                response = self.client.post('/api/export/github/sync', json={
                    'project_id': 'test-project',
                    'owner': 'testuser',
                    'repo': 'testrepo',
                    'branch': 'test-branch',
                    'dry_run': True
                })
                
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertTrue(data['success'])
                self.assertTrue(data['data']['dry_run'])
    
    def test_github_sync_replace_all_ok(self):
        """Test GitHub sync replace all mode"""
        with self.app.app_context():
            with patch.object(ExportService, 'materialize_build') as mock_materialize:
                with patch.object(GitHubService, 'sync_branch') as mock_sync:
                    # Mock bundle
                    mock_bundle = MagicMock()
                    mock_bundle.manifest.files = []
                    mock_bundle.manifest.total_size = 0
                    mock_materialize.return_value = mock_bundle
                    
                    # Mock GitHub sync result
                    mock_sync.return_value = {
                        'repo_url': 'https://github.com/testuser/testrepo',
                        'branch': 'test-branch',
                        'commit_sha': 'abc123',
                        'pr_url': None
                    }
                    
                    response = self.client.post('/api/export/github/sync', json={
                        'project_id': 'test-project',
                        'owner': 'testuser',
                        'repo': 'testrepo',
                        'branch': 'test-branch',
                        'sync_mode': 'replace_all',
                        'dry_run': False
                    })
                    
                    self.assertEqual(response.status_code, 200)
                    data = response.get_json()
                    self.assertTrue(data['success'])
                    self.assertFalse(data['data']['dry_run'])
    
    def test_rbac_enforced(self):
        """Test RBAC enforcement"""
        # Test without authentication
        response = self.client.post('/api/export/plan', json={
            'project_id': 'test-project'
        })
        
        # Should redirect to login or return 401
        self.assertIn(response.status_code, [401, 302])
    
    def test_feature_flag_respected(self):
        """Test feature flags are respected"""
        # Test with export disabled
        with patch.dict('os.environ', {'FEATURE_EXPORT': 'false'}):
            response = self.client.post('/api/export/plan', json={
                'project_id': 'test-project'
            })
            
            # Should return 404 when feature is disabled
            self.assertEqual(response.status_code, 404)
    
    def test_validation_errors(self):
        """Test validation error handling"""
        # Test missing project_id
        response = self.client.post('/api/export/plan', json={})
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('project_id', data['error'])
    
    def test_github_sync_validation(self):
        """Test GitHub sync validation"""
        # Test missing required fields
        response = self.client.post('/api/export/github/sync', json={
            'project_id': 'test-project'
        })
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_github_sync_disabled(self):
        """Test GitHub sync when disabled"""
        with patch.dict('os.environ', {'FEATURE_EXPORT_GITHUB': 'false'}):
            response = self.client.post('/api/export/github/sync', json={
                'project_id': 'test-project',
                'owner': 'testuser',
                'repo': 'testrepo',
                'branch': 'test-branch'
            })
            
            self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()
