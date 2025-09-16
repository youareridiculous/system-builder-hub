"""
Test codegen planning functionality
"""
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.agent_codegen.planner import CodegenPlanner
from src.agent_codegen.schema import CodegenGoal, RepoRef

class TestCodegenPlan(unittest.TestCase):
    """Test codegen planning"""
    
    def setUp(self):
        """Set up test environment"""
        self.planner = CodegenPlanner()
        self.sample_repo_path = Path('tests/fixtures/sample_repo')
    
    def test_analyze_repository(self):
        """Test repository analysis"""
        repo_context = self.planner._analyze_repository(self.sample_repo_path)
        
        self.assertIn('files', repo_context)
        self.assertIn('main_files', repo_context)
        self.assertIn('test_files', repo_context)
        self.assertIn('config_files', repo_context)
        
        # Check that we found the expected files
        file_paths = [f['path'] for f in repo_context['files']]
        self.assertIn('app.py', file_paths)
        self.assertIn('test_app.py', file_paths)
        self.assertIn('requirements.txt', file_paths)
        self.assertIn('README.md', file_paths)
    
    def test_generate_default_plan(self):
        """Test default plan generation"""
        goal = CodegenGoal(
            repo_ref=RepoRef(type='local', project_id='test-project'),
            goal_text='Add a new API endpoint',
            branch_base='main'
        )
        
        repo_context = {
            'files': [{'path': 'app.py', 'size': 100, 'extension': '.py'}],
            'main_files': ['app.py', 'README.md'],
            'test_files': ['test_app.py'],
            'config_files': ['requirements.txt']
        }
        
        plan = self.planner._generate_default_plan(goal, repo_context)
        
        self.assertIn('summary', plan)
        self.assertIn('diffs', plan)
        self.assertIn('risk', plan)
        self.assertIn('files_touched', plan)
        self.assertIn('tests_touched', plan)
        
        # Should have at least one diff
        self.assertGreater(len(plan['diffs']), 0)
    
    def test_validate_file_path(self):
        """Test file path validation"""
        goal = CodegenGoal(
            repo_ref=RepoRef(type='local', project_id='test-project'),
            goal_text='Test validation',
            allow_paths=['src/**', 'app.py'],
            deny_globs=['.env', '**/secrets/**']
        )
        
        # Valid paths
        self.assertTrue(self.planner._validate_file_path('app.py', goal))
        self.assertTrue(self.planner._validate_file_path('src/main.py', goal))
        
        # Invalid paths
        self.assertFalse(self.planner._validate_file_path('.env', goal))
        self.assertFalse(self.planner._validate_file_path('config/secrets.py', goal))
        self.assertFalse(self.planner._validate_file_path('other.py', goal))
    
    def test_validate_plan(self):
        """Test plan validation"""
        goal = CodegenGoal(
            repo_ref=RepoRef(type='local', project_id='test-project'),
            goal_text='Test validation',
            allow_paths=['app.py', 'README.md']
        )
        
        plan_data = {
            'summary': 'Test plan',
            'risk': 'low',
            'diffs': [
                {
                    'file_path': 'app.py',
                    'operation': 'modify',
                    'diff_content': 'test diff',
                    'new_content': 'new content'
                },
                {
                    'file_path': 'README.md',
                    'operation': 'modify',
                    'diff_content': 'test diff',
                    'new_content': 'new content'
                }
            ],
            'files_touched': ['app.py', 'README.md'],
            'tests_touched': []
        }
        
        plan = self.planner._validate_plan(plan_data, goal)
        
        self.assertEqual(plan.summary, 'Test plan')
        self.assertEqual(plan.risk.value, 'low')
        self.assertEqual(len(plan.diffs), 2)
        self.assertEqual(len(plan.files_touched), 2)
    
    def test_plan_changes_integration(self):
        """Test full planning integration"""
        goal = CodegenGoal(
            repo_ref=RepoRef(type='local', project_id='test-project'),
            goal_text='Add a new API endpoint for user management',
            branch_base='main'
        )
        
        with patch.object(self.planner, '_generate_plan_with_llm') as mock_llm:
            mock_llm.return_value = {
                'summary': 'Add user management endpoint',
                'risk': 'low',
                'diffs': [
                    {
                        'file_path': 'app.py',
                        'operation': 'modify',
                        'diff_content': 'test diff',
                        'new_content': 'new content'
                    }
                ],
                'files_touched': ['app.py'],
                'tests_touched': []
            }
            
            plan = self.planner.plan_changes(goal, self.sample_repo_path)
            
            self.assertEqual(plan.summary, 'Add user management endpoint')
            self.assertEqual(plan.risk.value, 'low')
            self.assertEqual(len(plan.diffs), 1)
            self.assertEqual(plan.diffs[0].file_path, 'app.py')

if __name__ == '__main__':
    unittest.main()
