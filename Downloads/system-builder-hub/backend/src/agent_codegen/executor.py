"""
Codegen executor for applying changes and running tests
"""
import os
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from src.agent_codegen.schema import (
    CodegenGoal, ProposedChange, ExecutionResult, 
    TestResult, LintResult, ExecutionStatus
)
from src.agent_codegen.repo import RepoManager
from src.analytics.service import AnalyticsService

logger = logging.getLogger(__name__)

class CodegenExecutor:
    """Codegen executor for applying changes and running tests"""
    
    def __init__(self):
        self.repo_manager = RepoManager()
        self.analytics = AnalyticsService()
        self.fail_on_tests = os.environ.get('CODEGEN_FAIL_ON_TESTS', 'true').lower() == 'true'
    
    def execute_plan(self, goal: CodegenGoal, plan: ProposedChange, 
                    tenant_id: str, user_id: Optional[str] = None) -> ExecutionResult:
        """Execute codegen plan"""
        start_time = time.time()
        
        try:
            # Track execution start
            self.analytics.track(
                tenant_id=tenant_id,
                event='codegen.apply.start',
                user_id=user_id,
                source='codegen',
                props={
                    'goal_text': goal.goal_text,
                    'files_count': len(plan.files_touched),
                    'risk': plan.risk.value,
                    'dry_run': goal.dry_run
                }
            )
            
            # Ensure workspace
            workspace_path = self.repo_manager.ensure_workspace(goal.repo_ref)
            
            # Generate branch name
            branch_name = self._generate_branch_name(goal)
            
            if goal.dry_run:
                # Dry run - simulate execution
                result = self._execute_dry_run(goal, plan, workspace_path, branch_name)
            else:
                # Real execution
                result = self._execute_real(goal, plan, workspace_path, branch_name)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            # Track execution completion
            self.analytics.track(
                tenant_id=tenant_id,
                event='codegen.apply.complete',
                user_id=user_id,
                source='codegen',
                props={
                    'goal_text': goal.goal_text,
                    'status': result.status.value,
                    'files_count': len(plan.files_touched),
                    'tests_passed': result.tests.passed,
                    'tests_failed': result.tests.failed,
                    'lint_ok': result.lint.ok,
                    'execution_time': execution_time
                }
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Track execution failure
            self.analytics.track(
                tenant_id=tenant_id,
                event='codegen.apply.failed',
                user_id=user_id,
                source='codegen',
                props={
                    'goal_text': goal.goal_text,
                    'error': str(e),
                    'execution_time': execution_time
                }
            )
            
            logger.error(f"Error executing plan: {e}")
            raise
    
    def _generate_branch_name(self, goal: CodegenGoal) -> str:
        """Generate branch name for changes"""
        import re
        
        # Create slug from goal text
        slug = re.sub(r'[^a-zA-Z0-9]', '-', goal.goal_text.lower())
        slug = re.sub(r'-+', '-', slug).strip('-')
        slug = slug[:50]  # Limit length
        
        timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        return f"sbh/codegen-{slug}-{timestamp}"
    
    def _execute_dry_run(self, goal: CodegenGoal, plan: ProposedChange, 
                        workspace_path: Path, branch_name: str) -> ExecutionResult:
        """Execute dry run (no actual changes)"""
        try:
            # Validate all file paths
            for diff in plan.diffs:
                if not self.repo_manager.validate_path(
                    diff.file_path, 
                    goal.allow_paths, 
                    goal.deny_globs
                ):
                    raise ValueError(f"Invalid file path: {diff.file_path}")
            
            # Simulate test results
            test_result = TestResult(
                passed=len(plan.tests_touched) + 1,  # Assume existing tests pass
                failed=0,
                duration=0.1,
                output="Dry run - tests not executed"
            )
            
            # Simulate lint results
            lint_result = LintResult(
                ok=True,
                issues=[],
                output="Dry run - lint not executed"
            )
            
            return ExecutionResult(
                branch=branch_name,
                commit_sha=None,
                tests=test_result,
                lint=lint_result,
                status=ExecutionStatus.DRY_RUN,
                pr_url=None,
                logs_url=None
            )
            
        except Exception as e:
            logger.error(f"Error in dry run: {e}")
            raise
    
    def _execute_real(self, goal: CodegenGoal, plan: ProposedChange, 
                     workspace_path: Path, branch_name: str) -> ExecutionResult:
        """Execute real changes"""
        try:
            # Checkout base branch
            if not self.repo_manager.checkout(workspace_path, goal.branch_base):
                raise Exception(f"Failed to checkout base branch: {goal.branch_base}")
            
            # Create new branch
            if not self.repo_manager.create_branch(workspace_path, branch_name):
                raise Exception(f"Failed to create branch: {branch_name}")
            
            # Apply patches
            applied_files = []
            for diff in plan.diffs:
                if not self.repo_manager.validate_path(
                    diff.file_path, 
                    goal.allow_paths, 
                    goal.deny_globs
                ):
                    raise ValueError(f"Invalid file path: {diff.file_path}")
                
                if self.repo_manager.apply_patch(workspace_path, diff):
                    applied_files.append(diff.file_path)
                else:
                    raise Exception(f"Failed to apply patch to: {diff.file_path}")
            
            # Run tests
            test_result = self._run_tests(workspace_path)
            
            # Run linting
            lint_result = self._run_lint(workspace_path)
            
            # Check if tests failed and rollback is required
            if test_result.failed > 0 and self.fail_on_tests:
                # Rollback changes
                logger.warning("Tests failed, rolling back changes")
                
                # Reset to base branch
                self.repo_manager.checkout(workspace_path, goal.branch_base)
                
                return ExecutionResult(
                    branch=branch_name,
                    commit_sha=None,
                    tests=test_result,
                    lint=lint_result,
                    status=ExecutionStatus.ROLLED_BACK,
                    pr_url=None,
                    logs_url=None,
                    error="Tests failed, changes rolled back"
                )
            
            # Commit changes
            commit_message = f"Codegen: {plan.summary}\n\nFiles: {', '.join(applied_files)}"
            commit_sha = self.repo_manager.commit(workspace_path, commit_message)
            
            # Push branch
            push_success = self.repo_manager.push(workspace_path, branch_name)
            
            # Create pull request
            pr_url = None
            if push_success:
                pr_title = f"Codegen: {plan.summary}"
                pr_body = self._generate_pr_body(plan, test_result, lint_result)
                pr_url = self.repo_manager.open_pr(goal.repo_ref, branch_name, pr_title, pr_body)
            
            return ExecutionResult(
                branch=branch_name,
                commit_sha=commit_sha,
                tests=test_result,
                lint=lint_result,
                status=ExecutionStatus.APPLIED,
                pr_url=pr_url,
                logs_url=None
            )
            
        except Exception as e:
            logger.error(f"Error in real execution: {e}")
            
            # Try to rollback
            try:
                self.repo_manager.checkout(workspace_path, goal.branch_base)
            except Exception as rollback_error:
                logger.error(f"Error rolling back: {rollback_error}")
            
            raise
    
    def _run_tests(self, workspace_path: Path) -> TestResult:
        """Run tests in workspace"""
        try:
            test_data = self.repo_manager.run_tests(workspace_path)
            
            return TestResult(
                passed=test_data['passed'],
                failed=test_data['failed'],
                duration=test_data['duration'],
                output=test_data['output'],
                error=test_data['error']
            )
            
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return TestResult(
                passed=0,
                failed=0,
                duration=0.0,
                output="",
                error=str(e)
            )
    
    def _run_lint(self, workspace_path: Path) -> LintResult:
        """Run linting in workspace"""
        try:
            lint_data = self.repo_manager.run_lint(workspace_path)
            
            return LintResult(
                ok=lint_data['ok'],
                issues=lint_data['issues'],
                output=lint_data['output'],
                error=lint_data['error']
            )
            
        except Exception as e:
            logger.error(f"Error running lint: {e}")
            return LintResult(
                ok=False,
                issues=[],
                output="",
                error=str(e)
            )
    
    def _generate_pr_body(self, plan: ProposedChange, test_result: TestResult, 
                         lint_result: LintResult) -> str:
        """Generate pull request body"""
        body_parts = []
        
        # Summary
        body_parts.append(f"## Summary\n{plan.summary}\n")
        
        # Files changed
        body_parts.append(f"## Files Changed\n")
        for file_path in plan.files_touched:
            body_parts.append(f"- `{file_path}`")
        body_parts.append("")
        
        # Risk assessment
        body_parts.append(f"## Risk Assessment\nRisk Level: **{plan.risk.value.upper()}**\n")
        
        # Test results
        body_parts.append("## Test Results\n")
        if test_result.error:
            body_parts.append(f"❌ **Error**: {test_result.error}\n")
        else:
            body_parts.append(f"✅ **Passed**: {test_result.passed}\n")
            if test_result.failed > 0:
                body_parts.append(f"❌ **Failed**: {test_result.failed}\n")
            body_parts.append(f"⏱️ **Duration**: {test_result.duration:.2f}s\n")
        body_parts.append("")
        
        # Lint results
        body_parts.append("## Lint Results\n")
        if lint_result.error:
            body_parts.append(f"❌ **Error**: {lint_result.error}\n")
        elif lint_result.ok:
            body_parts.append("✅ **All checks passed**\n")
        else:
            body_parts.append(f"⚠️ **Issues found**: {len(lint_result.issues)}\n")
            for issue in lint_result.issues[:5]:  # Show first 5 issues
                body_parts.append(f"- {issue['message']}")
        body_parts.append("")
        
        # Generated by
        body_parts.append("---\n*Generated by SBH Codegen Agent*")
        
        return "\n".join(body_parts)
    
    def cleanup_workspace(self, workspace_path: Path):
        """Clean up workspace"""
        self.repo_manager.cleanup_workspace(workspace_path)
