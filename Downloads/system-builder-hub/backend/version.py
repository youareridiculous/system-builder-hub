"""
Version Management for System Builder Hub
"""
import os
import subprocess
import re
from typing import Optional

def get_git_version() -> Optional[str]:
    """Get version from git tag"""
    try:
        # Get the latest tag
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        
        # Validate version format (semantic versioning)
        if re.match(r'^v?\d+\.\d+\.\d+', version):
            # Remove 'v' prefix if present
            return version.lstrip('v')
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    return None

def get_git_commit_hash() -> Optional[str]:
    """Get current git commit hash"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def get_git_branch() -> Optional[str]:
    """Get current git branch"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def get_version_info() -> dict:
    """Get complete version information"""
    version = get_git_version()
    commit_hash = get_git_commit_hash()
    branch = get_git_branch()
    
    # Fallback version if no git tag
    if not version:
        version = "0.1.0-dev"
    
    # Build version string
    if commit_hash and branch and branch != 'main':
        version_string = f"{version}-{branch}-{commit_hash}"
    elif commit_hash:
        version_string = f"{version}-{commit_hash}"
    else:
        version_string = version
    
    return {
        'version': version,
        'version_string': version_string,
        'commit_hash': commit_hash,
        'branch': branch,
        'build_date': os.getenv('BUILD_DATE', ''),
        'build_id': os.getenv('BUILD_ID', '')
    }

# Default version (fallback)
APP_VERSION = "0.1.0"

# Try to get version from git
try:
    version_info = get_version_info()
    APP_VERSION = version_info['version']
    VERSION_STRING = version_info['version_string']
    COMMIT_HASH = version_info['commit_hash']
    BRANCH = version_info['branch']
    BUILD_DATE = version_info['build_date']
    BUILD_ID = version_info['build_id']
except Exception:
    # Fallback values
    VERSION_STRING = APP_VERSION
    COMMIT_HASH = None
    BRANCH = None
    BUILD_DATE = ''
    BUILD_ID = ''

if __name__ == '__main__':
    print(f"Version: {APP_VERSION}")
    print(f"Version String: {VERSION_STRING}")
    print(f"Commit Hash: {COMMIT_HASH}")
    print(f"Branch: {BRANCH}")
    print(f"Build Date: {BUILD_DATE}")
    print(f"Build ID: {BUILD_ID}")
