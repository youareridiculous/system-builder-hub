"""
Test codegen apply functionality for local repos
"""
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.agent_codegen.executor import CodegenExecutor
from src.agent_codegen.schema import (
    CodegenGoal, RepoRef, ProposedChange, UnifiedDiff, RiskLevel
)

class TestCodegenApplyLocal(unittest.TestCase):
    """Test codegen apply for local repos"""
    
    def setUp(self):
        """Set up test environment"""
        self.executor = CodegenExecutor()
        self.sample_repo_path = Path('tests/fixtures/sample_repo')
    
    def test_execute_dry_run(self):
        """Test dry run execution"""
        goal = CodegenGoal(
            repo_ref=RepoRef(type='local', project_id='test-project'),
            goal_text='Add a new API endpoint',
            branch_base='main',
            dry_run=True
        )
        
        plan = ProposedChange(
            summary='Add user management endpoint',
            diffs=[
                UnifiedDiff(
                    file_path='app.py',
                    operation='modify',
                    diff_content='test diff',
                    new_content='new content'
                )
            ],
            risk=RiskLevel.LOW,
            files_touched=['app.py'],
            tests_touched=[]
        )
        
        with patch.object(self.executor.repo_manager, 'ensure_workspace') as mock_workspace:
            mock_workspace.return_value = self.sample_repo_path
            
            result = self.executor._execute_dry_run(goal, plan, self.sample_repo_path, 'test-branch')
            
            self.assertEqual(result.status.value, 'dry_run')
            self.assertIsNone(result.commit_sha)
            self.assertIsNone(result.pr_url)
            self.assertEqual(result.tests.passed, 1)  # Default dry run assumption
            self.assertEqual(result.tests.failed, 0)
    
    def test_generate_branch_name(self):
        """Test branch name generation"""
        goal = CodegenGoal(
            repo_ref=RepoRef(type='local', project_id='test-project'),
            goal_text='Add user management API endpoint'
        )
        
        branch_name = self.executor._generate_branch_name(goal)
        
        self.assertIn('sbh/codegen-', branch_name)
        self.assertIn('add-user-management-api-endpoint', branch_name)
        self.assertIn('-', branch_name)  # Should have timestamp
    
    def test_generate_pr_body(self):
        """Test PR body generation"""
        plan = ProposedChange(
            summary='Add user management endpoint',
            diffs=[
                UnifiedDiff(
                    file_path='app.py',
                    operation='modify',
                    diff_content='test diff',
                    new_content='new content'
                )
            ],
            risk=RiskLevel.LOW,
            files_touched=['app.py'],
            tests_touched=[]
        )
        
        from src.agent_codegen.schema import TestResult, LintResult
        
        test_result = TestResult(
            passed=3,
            failed=0,
            duration=1.5,
            output='All tests passed'
        )
        
        lint_result = LintResult(
            ok=True,
            issues=[],
            output='All checks passed'
        )
        
        pr_body = self.executor._generate_pr_body(plan, test_result, lint_result)
        
        self.assertIn('## Summary', pr_body)
        self.assertIn('Add user management endpoint', pr_body)
        self.assertIn('## Files Changed', pr_body)
        self.assertIn('app.py', pr_body)
        self.assertIn('## Risk Assessment', pr_body)
        self.assertIn('LOW', pr_body)
        self.assertIn('## Test Results', pr_body)
        self.assertIn('3', pr_body)  # Passed tests
        self.assertIn('## Lint Results', pr_body)
        self.assertIn('All checks passed', pr_body)
    
    def test_run_tests(self):
        """Test test execution"""
        with patch.object(self.executor.repo_manager, 'run_tests') as mock_run_tests:
            mock_run_tests.return_value = {
                'passed': 2,
                'failed': 1,
                'duration': 1.2,
                'output': 'Test output',
                'error': None
            }
            
            result = self.executor._run_tests(self.sample_repo_path)
            
            self.assertEqual(result.passed, 2)
            self.assertEqual(result.failed, 1)
            self.assertEqual(result.duration, 1.2)
            self.assertEqual(result.output, 'Test output')
            self.assertIsNone(result.error)
    
    def test_run_lint(self):
        """Test lint execution"""
        with patch.object(self.executor.repo_manager, 'run_lint') as mock_run_lint:
            mock_run_lint.return_value = {
                'ok': False,
                'issues': [
                    {'tool': 'flake8', 'message': 'E501 line too long', 'severity': 'warning'}
                ],
                'output': 'Found 1 linting issue',
                'error': None
            }
            
            result = self.executor._run_lint(self.sample_repo_path)
            
            self.assertFalse(result.ok)
            self.assertEqual(len(result.issues), 1)
            self.assertEqual(result.issues[0]['message'], 'E501 line too long')
            self.assertEqual(result.output, 'Found 1 linting issue')
    
    def test_execute_plan_integration(self):
        """Test full plan execution integration"""
        goal = CodegenGoal(
            repo_ref=RepoRef(type='local', project_id='test-project'),
            goal_text='Add a new API endpoint',
            branch_base='main',
            dry_run=True
        )
        
        plan = ProposedChange(
            summary='Add user management endpoint',
            diffs=[
                UnifiedDiff(
                    file_path='app.py',
                    operation='modify',
                    diff_content='test diff',
                    new_content='new content'
                )
            ],
            risk=RiskLevel.LOW,
            files_touched=['app.py'],
            tests_touched=[]
        )
        
        with patch.object(self.executor.repo_manager, 'ensure_workspace') as mock_workspace:
            mock_workspace.return_value = self.sample_repo_path
            
            with patch.object(self.executor, '_execute_dry_run') as mock_dry_run:
                mock_dry_run.return_value = MagicMock(
                    status=MagicMock(value='dry_run'),
                    commit_sha=None,
                    tests=MagicMock(passed=1, failed=0),
                    lint=MagicMock(ok=True),
                    pr_url=None,
                    logs_url=None
                )
                
                result = self.executor.execute_plan(goal, plan, 'test-tenant', 'test-user')
                
                self.assertEqual(result.status.value, 'dry_run')
                self.assertIsNone(result.commit_sha)
                self.assertIsNone(result.pr_url)

if __name__ == '__main__':
    unittest.main()
