"""
GitHub service for repository management and sync
"""
import os
import re
import logging
import requests
from typing import Dict, List, Any, Optional, Tuple
from src.exporter.models import ExportBundle
from src.analytics.service import AnalyticsService

logger = logging.getLogger(__name__)

class GitHubService:
    """GitHub service for repository management and sync"""
    
    def __init__(self):
        self.analytics = AnalyticsService()
        self.base_url = "https://api.github.com"
        self.token = self._get_github_token()
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'SBH-Export/1.0'
        })
        
        # Rate limiting
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = 0
    
    def _get_github_token(self) -> str:
        """Get GitHub token from environment or SSM"""
        # Try environment first
        token = os.environ.get('GITHUB_TOKEN')
        if token:
            return token
        
        # Try GitHub App credentials
        app_id = os.environ.get('GITHUB_APP_ID')
        installation_id = os.environ.get('GITHUB_INSTALLATION_ID')
        
        if app_id and installation_id:
            # This would generate a token from GitHub App
            # For now, return a placeholder
            logger.warning("GitHub App token generation not implemented")
            return ""
        
        # Try SSM for tenant-specific tokens
        try:
            from src.secrets import get_secret
            tenant_id = os.environ.get('TENANT_ID')
            if tenant_id:
                token = get_secret(f'github_token_{tenant_id}')
                if token:
                    return token
        except ImportError:
            pass
        
        raise ValueError("No GitHub token available")
    
    def _mask_token(self, token: str) -> str:
        """Mask token for logging (show last 4 chars)"""
        if len(token) <= 4:
            return '*' * len(token)
        return '*' * (len(token) - 4) + token[-4:]
    
    def _validate_repo_name(self, owner: str, repo: str) -> bool:
        """Validate repository name"""
        pattern = r'^[A-Za-z0-9._/-]{1,200}$'
        return bool(re.match(pattern, owner)) and bool(re.match(pattern, repo))
    
    def _validate_branch_name(self, branch: str) -> bool:
        """Validate branch name"""
        pattern = r'^[A-Za-z0-9._/-]{1,200}$'
        return bool(re.match(pattern, branch))
    
    def _check_rate_limit(self):
        """Check and handle rate limiting"""
        if self.rate_limit_remaining <= 0:
            import time
            wait_time = max(0, self.rate_limit_reset - time.time())
            if wait_time > 0:
                logger.warning(f"Rate limit exceeded, waiting {wait_time} seconds")
                time.sleep(wait_time)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make GitHub API request with rate limiting and error handling"""
        try:
            self._check_rate_limit()
            
            url = f"{self.base_url}{endpoint}"
            response = self.session.request(method, url, **kwargs)
            
            # Update rate limit info
            self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 5000))
            self.rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))
            
            if response.status_code == 403 and 'rate limit' in response.text.lower():
                logger.warning("Rate limit exceeded")
                raise Exception("GitHub rate limit exceeded")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API request failed: {e}")
            raise Exception(f"GitHub API error: {str(e)}")
    
    def ensure_repo(self, owner: str, repo: str, private: bool = True) -> Dict[str, Any]:
        """Ensure repository exists, create if missing"""
        try:
            if not self._validate_repo_name(owner, repo):
                raise ValueError("Invalid repository name")
            
            # Check if repo exists
            try:
                repo_data = self._make_request('GET', f'/repos/{owner}/{repo}')
                logger.info(f"Repository {owner}/{repo} already exists")
                return repo_data
            except Exception as e:
                if '404' in str(e):
                    # Repository doesn't exist, create it
                    logger.info(f"Creating repository {owner}/{repo}")
                    
                    create_data = {
                        'name': repo,
                        'private': private,
                        'auto_init': False,
                        'description': f'SBH generated application - {repo}'
                    }
                    
                    repo_data = self._make_request('POST', f'/user/repos', json=create_data)
                    logger.info(f"Created repository {owner}/{repo}")
                    return repo_data
                else:
                    raise
            
        except Exception as e:
            logger.error(f"Error ensuring repository {owner}/{repo}: {e}")
            raise
    
    def sync_branch(self, owner: str, repo: str, branch: str, bundle: ExportBundle,
                   commit_message: str, default_branch: str = "main",
                   sync_mode: str = "replace_all") -> Dict[str, Any]:
        """Sync export bundle to GitHub repository branch"""
        try:
            if not self._validate_repo_name(owner, repo):
                raise ValueError("Invalid repository name")
            
            if not self._validate_branch_name(branch):
                raise ValueError("Invalid branch name")
            
            # Ensure repository exists
            repo_data = self.ensure_repo(owner, repo)
            
            # Get default branch reference
            default_ref = self._make_request('GET', f'/repos/{owner}/{repo}/git/ref/heads/{default_branch}')
            base_sha = default_ref['object']['sha']
            
            # Create tree from bundle
            tree_items = []
            for path, content in bundle.files.items():
                # Create blob for file content
                blob_data = {
                    'content': content,
                    'encoding': 'utf-8'
                }
                blob = self._make_request('POST', f'/repos/{owner}/{repo}/git/blobs', json=blob_data)
                
                tree_items.append({
                    'path': path,
                    'mode': '100644',
                    'type': 'blob',
                    'sha': blob['sha']
                })
            
            # Create tree
            tree_data = {
                'base_tree': base_sha,
                'tree': tree_items
            }
            tree = self._make_request('POST', f'/repos/{owner}/{repo}/git/trees', json=tree_data)
            
            # Create commit
            commit_data = {
                'message': commit_message,
                'tree': tree['sha'],
                'parents': [base_sha]
            }
            commit = self._make_request('POST', f'/repos/{owner}/{repo}/git/commits', json=commit_data)
            
            # Create or update branch reference
            try:
                # Try to update existing branch
                ref_data = {'sha': commit['sha']}
                self._make_request('PATCH', f'/repos/{owner}/{repo}/git/refs/heads/{branch}', json=ref_data)
            except Exception:
                # Branch doesn't exist, create it
                ref_data = {
                    'ref': f'refs/heads/{branch}',
                    'sha': commit['sha']
                }
                self._make_request('POST', f'/repos/{owner}/{repo}/git/refs', json=ref_data)
            
            result = {
                'repo_url': repo_data['html_url'],
                'default_branch': default_branch,
                'branch': branch,
                'commit_sha': commit['sha'],
                'pr_url': None
            }
            
            # Create pull request if branch is not default
            if branch != default_branch:
                pr_data = {
                    'title': f'SBH Sync: {commit_message}',
                    'body': f'Automated sync from System Builder Hub\n\nGenerated on: {bundle.manifest.export_timestamp.isoformat()}',
                    'head': branch,
                    'base': default_branch
                }
                
                try:
                    pr = self._make_request('POST', f'/repos/{owner}/{repo}/pulls', json=pr_data)
                    result['pr_url'] = pr['html_url']
                except Exception as e:
                    logger.warning(f"Failed to create pull request: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error syncing branch {owner}/{repo}/{branch}: {e}")
            raise
    
    def get_repo_stats(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository statistics"""
        try:
            repo_data = self._make_request('GET', f'/repos/{owner}/{repo}')
            
            return {
                'name': repo_data['name'],
                'full_name': repo_data['full_name'],
                'private': repo_data['private'],
                'description': repo_data['description'],
                'html_url': repo_data['html_url'],
                'clone_url': repo_data['clone_url'],
                'default_branch': repo_data['default_branch'],
                'stargazers_count': repo_data['stargazers_count'],
                'forks_count': repo_data['forks_count'],
                'open_issues_count': repo_data['open_issues_count'],
                'size': repo_data['size'],
                'updated_at': repo_data['updated_at']
            }
            
        except Exception as e:
            logger.error(f"Error getting repo stats for {owner}/{repo}: {e}")
            raise
    
    def check_permissions(self, owner: str, repo: str) -> Dict[str, bool]:
        """Check user permissions for repository"""
        try:
            repo_data = self._make_request('GET', f'/repos/{owner}/{repo}')
            
            return {
                'admin': repo_data.get('permissions', {}).get('admin', False),
                'push': repo_data.get('permissions', {}).get('push', False),
                'pull': repo_data.get('permissions', {}).get('pull', False)
            }
            
        except Exception as e:
            logger.error(f"Error checking permissions for {owner}/{repo}: {e}")
            return {'admin': False, 'push': False, 'pull': False}
