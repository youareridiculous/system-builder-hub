"""
Test codegen guardrails and security
"""
import unittest
from unittest.mock import patch, MagicMock
from src.agent_codegen.repo import RepoManager
from src.agent_codegen.schema import CodegenGoal, RepoRef

class TestCodegenGuardrails(unittest.TestCase):
    """Test codegen guardrails"""
    
    def setUp(self):
        """Set up test environment"""
        self.repo_manager = RepoManager()
    
    def test_default_allow_patterns(self):
        """Test default allow patterns"""
        # Should allow common development files
        self.assertTrue(self.repo_manager.validate_path('src/main.py'))
        self.assertTrue(self.repo_manager.validate_path('templates/index.html'))
        self.assertTrue(self.repo_manager.validate_path('static/css/style.css'))
        self.assertTrue(self.repo_manager.validate_path('tests/test_main.py'))
        self.assertTrue(self.repo_manager.validate_path('README.md'))
        self.assertTrue(self.repo_manager.validate_path('requirements.txt'))
        self.assertTrue(self.repo_manager.validate_path('Dockerfile'))
        self.assertTrue(self.repo_manager.validate_path('.github/workflows/ci.yml'))
    
    def test_default_deny_patterns(self):
        """Test default deny patterns"""
        # Should deny sensitive files
        self.assertFalse(self.repo_manager.validate_path('.env'))
        self.assertFalse(self.repo_manager.validate_path('config/secrets.py'))
        self.assertFalse(self.repo_manager.validate_path('keys/private.pem'))
        self.assertFalse(self.repo_manager.validate_path('auth/api.key'))
        self.assertFalse(self.repo_manager.validate_path('.ssh/id_rsa'))
        self.assertFalse(self.repo_manager.validate_path('.aws/credentials'))
        self.assertFalse(self.repo_manager.validate_path('terraform.tfstate'))
        self.assertFalse(self.repo_manager.validate_path('terraform.tfstate.backup'))
    
    def test_custom_allow_patterns(self):
        """Test custom allow patterns"""
        allow_paths = ['custom/**', 'special.py']
        
        # Should allow custom patterns
        self.assertTrue(self.repo_manager.validate_path('custom/file.py', allow_paths=allow_paths))
        self.assertTrue(self.repo_manager.validate_path('special.py', allow_paths=allow_paths))
        
        # Should deny non-custom patterns
        self.assertFalse(self.repo_manager.validate_path('src/main.py', allow_paths=allow_paths))
    
    def test_custom_deny_patterns(self):
        """Test custom deny patterns"""
        deny_globs = ['**/temp/**', '*.tmp']
        
        # Should deny custom patterns
        self.assertFalse(self.repo_manager.validate_path('temp/file.py', deny_globs=deny_globs))
        self.assertFalse(self.repo_manager.validate_path('src/temp/data.py', deny_globs=deny_globs))
        self.assertFalse(self.repo_manager.validate_path('config.tmp', deny_globs=deny_globs))
        
        # Should allow other patterns
        self.assertTrue(self.repo_manager.validate_path('src/main.py', deny_globs=deny_globs))
    
    def test_combined_patterns(self):
        """Test combined allow and deny patterns"""
        allow_paths = ['src/**', 'tests/**']
        deny_globs = ['**/secrets/**', '*.key']
        
        # Should allow valid paths
        self.assertTrue(self.repo_manager.validate_path('src/main.py', allow_paths, deny_globs))
        self.assertTrue(self.repo_manager.validate_path('tests/test_main.py', allow_paths, deny_globs))
        
        # Should deny sensitive files even in allowed directories
        self.assertFalse(self.repo_manager.validate_path('src/secrets/config.py', allow_paths, deny_globs))
        self.assertFalse(self.repo_manager.validate_path('src/api.key', allow_paths, deny_globs))
        
        # Should deny files not in allowed directories
        self.assertFalse(self.repo_manager.validate_path('other/file.py', allow_paths, deny_globs))
    
    def test_planner_validation(self):
        """Test planner file path validation"""
        from src.agent_codegen.planner import CodegenPlanner
        
        planner = CodegenPlanner()
        
        goal = CodegenGoal(
            repo_ref=RepoRef(type='local', project_id='test-project'),
            goal_text='Test validation',
            allow_paths=['src/**'],
            deny_globs=['**/secrets/**']
        )
        
        # Valid paths
        self.assertTrue(planner._validate_file_path('src/main.py', goal))
        
        # Invalid paths
        self.assertFalse(planner._validate_file_path('src/secrets/config.py', goal))
        self.assertFalse(planner._validate_file_path('other/file.py', goal))
    
    def test_api_validation_error(self):
        """Test API validation error handling"""
        from src.agent_codegen.router import bp
        from flask import Flask
        
        app = Flask(__name__)
        app.register_blueprint(bp)
        client = app.test_client()
        
        # Test with invalid file path
        data = {
            'repo_ref': {
                'type': 'local',
                'project_id': 'test-project'
            },
            'goal_text': 'Add feature',
            'file_paths': ['.env', 'src/secrets.py']  # Invalid paths
        }
        
        with patch('src.agent_codegen.router.RepoManager') as mock_repo_manager:
            mock_manager = MagicMock()
            mock_manager.return_value.validate_path.side_effect = lambda path, allow, deny: path not in ['.env', 'src/secrets.py']
            mock_repo_manager.return_value = mock_manager
            
            response = client.post('/api/agent/codegen/validate', json=data)
            
            # Should return validation results
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])
            
            # Check validation results
            validations = data['data']['file_validations']
            self.assertEqual(len(validations), 2)
            
            # .env should be invalid
            env_validation = next(v for v in validations if v['file_path'] == '.env')
            self.assertFalse(env_validation['valid'])
            
            # src/secrets.py should be invalid
            secrets_validation = next(v for v in validations if v['file_path'] == 'src/secrets.py')
            self.assertFalse(secrets_validation['valid'])

if __name__ == '__main__':
    unittest.main()
