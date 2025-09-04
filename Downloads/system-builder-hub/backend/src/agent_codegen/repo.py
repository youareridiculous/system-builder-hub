"""
Repository management for codegen agent
"""
import os
import shutil
import tempfile
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from src.agent_codegen.schema import RepoRef
from src.exporter.service import ExportService
from src.vcs.github_service import GitHubService

logger = logging.getLogger(__name__)

class RepoManager:
    """Repository manager for codegen operations"""
    
    def __init__(self):
        self.export_service = ExportService()
        self.github_service = GitHubService()
        self.workspaces_dir = Path('instance/workspaces')
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        
        # Default allow/deny patterns
        self.default_allow = [
            'src/**',
            'templates/**',
            'static/**',
            'tests/**',
            'README.md',
            'docs/**',
            'Dockerfile',
            'requirements.txt',
            'wsgi.py',
            'gunicorn.conf.py',
            '.github/workflows/**'
        ]
        
        self.default_deny = [
            '.env',
            '**/secrets/**',
            '**/*.pem',
            '**/*.key',
            '**/.ssh/**',
            '**/.aws/**',
            '**/terraform.tfstate',
            '**/terraform.tfstate.backup'
        ]
    
    def ensure_workspace(self, repo_ref: RepoRef) -> Path:
        """Ensure workspace exists and is ready"""
        if repo_ref.type == 'local':
            return self._ensure_local_workspace(repo_ref)
        elif repo_ref.type == 'github':
            return self._ensure_github_workspace(repo_ref)
        else:
            raise ValueError(f"Unsupported repo type: {repo_ref.type}")
    
    def _ensure_local_workspace(self, repo_ref: RepoRef) -> Path:
        """Ensure local workspace from export bundle"""
        if not repo_ref.project_id:
            raise ValueError("project_id required for local repo")
        
        workspace_path = self.workspaces_dir / repo_ref.project_id
        
        if workspace_path.exists():
            logger.info(f"Using existing workspace: {workspace_path}")
            return workspace_path
        
        # Create workspace from export bundle
        logger.info(f"Creating workspace from export bundle: {repo_ref.project_id}")
        
        try:
            # Materialize export bundle
            bundle = self.export_service.materialize_build(
                project_id=repo_ref.project_id,
                tenant_id='system',  # Will be overridden by tenant context
                include_runtime=True
            )
            
            # Create workspace directory
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            # Extract bundle files to workspace
            for file_path, content in bundle.files.items():
                file_full_path = workspace_path / file_path
                file_full_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_full_path, 'w') as f:
                    f.write(content)
            
            # Initialize git repository
            self._init_git_repo(workspace_path)
            
            logger.info(f"Workspace created: {workspace_path}")
            return workspace_path
            
        except Exception as e:
            logger.error(f"Error creating workspace: {e}")
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
            raise
    
    def _ensure_github_workspace(self, repo_ref: RepoRef) -> Path:
        """Ensure GitHub workspace"""
        if not repo_ref.owner or not repo_ref.repo:
            raise ValueError("owner and repo required for GitHub repo")
        
        workspace_name = f"{repo_ref.owner}_{repo_ref.repo}"
        workspace_path = self.workspaces_dir / workspace_name
        
        if workspace_path.exists():
            logger.info(f"Using existing GitHub workspace: {workspace_path}")
            return workspace_path
        
        # Clone repository
        logger.info(f"Cloning GitHub repository: {repo_ref.owner}/{repo_ref.repo}")
        
        try:
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            # Clone repository
            clone_url = f"https://github.com/{repo_ref.owner}/{repo_ref.repo}.git"
            branch = repo_ref.branch or "main"
            
            subprocess.run([
                'git', 'clone', '--branch', branch, '--depth', '1',
                clone_url, str(workspace_path)
            ], check=True, capture_output=True)
            
            logger.info(f"GitHub workspace created: {workspace_path}")
            return workspace_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error cloning repository: {e}")
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
            raise
    
    def _init_git_repo(self, workspace_path: Path):
        """Initialize git repository"""
        try:
            subprocess.run(['git', 'init'], cwd=workspace_path, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'SBH Codegen Agent'], 
                         cwd=workspace_path, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'codegen@sbh.local'], 
                         cwd=workspace_path, check=True, capture_output=True)
            subprocess.run(['git', 'add', '.'], cwd=workspace_path, check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit from SBH export'], 
                         cwd=workspace_path, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Error initializing git repo: {e}")
    
    def checkout(self, workspace_path: Path, branch: str) -> bool:
        """Checkout branch"""
        try:
            # Check if branch exists
            result = subprocess.run(['git', 'branch', '--list', branch], 
                                  cwd=workspace_path, capture_output=True, text=True)
            
            if result.stdout.strip():
                # Branch exists, checkout
                subprocess.run(['git', 'checkout', branch], cwd=workspace_path, check=True, capture_output=True)
            else:
                # Create and checkout new branch
                subprocess.run(['git', 'checkout', '-b', branch], cwd=workspace_path, check=True, capture_output=True)
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error checking out branch {branch}: {e}")
            return False
    
    def create_branch(self, workspace_path: Path, branch_name: str) -> bool:
        """Create and checkout new branch"""
        try:
            subprocess.run(['git', 'checkout', '-b', branch_name], cwd=workspace_path, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating branch {branch_name}: {e}")
            return False
    
    def apply_patch(self, workspace_path: Path, diff: 'UnifiedDiff') -> bool:
        """Apply unified diff to workspace"""
        try:
            file_path = workspace_path / diff.file_path
            
            if diff.operation == 'add':
                # Create new file
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write(diff.new_content or '')
            
            elif diff.operation == 'modify':
                # Modify existing file
                if file_path.exists():
                    with open(file_path, 'w') as f:
                        f.write(diff.new_content or '')
                else:
                    logger.warning(f"File not found for modification: {diff.file_path}")
                    return False
            
            elif diff.operation == 'delete':
                # Delete file
                if file_path.exists():
                    file_path.unlink()
                else:
                    logger.warning(f"File not found for deletion: {diff.file_path}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying patch to {diff.file_path}: {e}")
            return False
    
    def run_tests(self, workspace_path: Path) -> Dict[str, Any]:
        """Run tests in workspace"""
        try:
            # Check if pytest is available
            if not (workspace_path / 'requirements.txt').exists():
                return {
                    'passed': 0,
                    'failed': 0,
                    'duration': 0.0,
                    'output': 'No requirements.txt found',
                    'error': None
                }
            
            # Install dependencies
            subprocess.run(['pip', 'install', '-r', 'requirements.txt'], 
                         cwd=workspace_path, check=True, capture_output=True)
            
            # Run tests
            start_time = time.time()
            result = subprocess.run(['python', '-m', 'pytest', '-v'], 
                                  cwd=workspace_path, capture_output=True, text=True)
            duration = time.time() - start_time
            
            # Parse test results
            output_lines = result.stdout.split('\n')
            passed = 0
            failed = 0
            
            for line in output_lines:
                if 'passed' in line and 'failed' in line:
                    # Extract numbers from line like "3 passed, 1 failed"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'passed':
                            passed = int(parts[i-1])
                        elif part == 'failed':
                            failed = int(parts[i-1])
                    break
            
            return {
                'passed': passed,
                'failed': failed,
                'duration': duration,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None
            }
            
        except subprocess.CalledProcessError as e:
            return {
                'passed': 0,
                'failed': 0,
                'duration': 0.0,
                'output': '',
                'error': str(e)
            }
        except Exception as e:
            return {
                'passed': 0,
                'failed': 0,
                'duration': 0.0,
                'output': '',
                'error': str(e)
            }
    
    def run_lint(self, workspace_path: Path) -> Dict[str, Any]:
        """Run linting in workspace"""
        try:
            issues = []
            
            # Try ruff if available
            try:
                result = subprocess.run(['ruff', 'check', '.'], 
                                      cwd=workspace_path, capture_output=True, text=True)
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            issues.append({
                                'tool': 'ruff',
                                'message': line,
                                'severity': 'warning'
                            })
            except FileNotFoundError:
                pass
            
            # Try flake8 if available
            try:
                result = subprocess.run(['flake8', '.'], 
                                      cwd=workspace_path, capture_output=True, text=True)
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            issues.append({
                                'tool': 'flake8',
                                'message': line,
                                'severity': 'warning'
                            })
            except FileNotFoundError:
                pass
            
            return {
                'ok': len(issues) == 0,
                'issues': issues,
                'output': f"Found {len(issues)} linting issues",
                'error': None
            }
            
        except Exception as e:
            return {
                'ok': False,
                'issues': [],
                'output': '',
                'error': str(e)
            }
    
    def commit(self, workspace_path: Path, message: str) -> Optional[str]:
        """Commit changes and return commit SHA"""
        try:
            # Add all changes
            subprocess.run(['git', 'add', '.'], cwd=workspace_path, check=True, capture_output=True)
            
            # Commit
            subprocess.run(['git', 'commit', '-m', message], cwd=workspace_path, check=True, capture_output=True)
            
            # Get commit SHA
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                  cwd=workspace_path, capture_output=True, text=True)
            
            return result.stdout.strip()
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error committing changes: {e}")
            return None
    
    def push(self, workspace_path: Path, branch: str) -> bool:
        """Push branch to remote"""
        try:
            subprocess.run(['git', 'push', 'origin', branch], cwd=workspace_path, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error pushing branch {branch}: {e}")
            return False
    
    def open_pr(self, repo_ref: RepoRef, branch: str, title: str, body: str) -> Optional[str]:
        """Open pull request and return PR URL"""
        if repo_ref.type == 'local':
            # For local repos, return a stub PR URL
            return f"https://github.com/stub/{repo_ref.project_id}/pull/1"
        
        elif repo_ref.type == 'github':
            try:
                # Create PR using GitHub service
                result = self.github_service.create_pr(
                    owner=repo_ref.owner,
                    repo=repo_ref.repo,
                    branch=branch,
                    title=title,
                    body=body
                )
                return result.get('html_url')
            except Exception as e:
                logger.error(f"Error creating PR: {e}")
                return None
        
        return None
    
    def validate_path(self, file_path: str, allow_paths: Optional[List[str]] = None, 
                     deny_globs: Optional[List[str]] = None) -> bool:
        """Validate file path against allow/deny patterns"""
        from fnmatch import fnmatch
        
        # Use default patterns if not provided
        if allow_paths is None:
            allow_paths = self.default_allow
        if deny_globs is None:
            deny_globs = self.default_deny
        
        # Check deny patterns first
        for pattern in deny_globs:
            if fnmatch(file_path, pattern):
                logger.warning(f"File path denied by pattern {pattern}: {file_path}")
                return False
        
        # Check allow patterns
        for pattern in allow_paths:
            if fnmatch(file_path, pattern):
                return True
        
        logger.warning(f"File path not allowed: {file_path}")
        return False
    
    def cleanup_workspace(self, workspace_path: Path):
        """Clean up workspace"""
        try:
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
                logger.info(f"Cleaned up workspace: {workspace_path}")
        except Exception as e:
            logger.error(f"Error cleaning up workspace {workspace_path}: {e}")
