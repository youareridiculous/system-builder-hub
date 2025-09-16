"""
File operations helper for Co-Builder.

Provides safe, idempotent file creation capabilities with proper error handling
and metadata tracking.
"""

import os
import hashlib
from pathlib import Path
from typing import Dict, Any


def ensure_parents(path: str) -> None:
    """Ensure parent directories exist for the given path."""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)


def write_file(path: str, contents: str, *, overwrite: bool = True) -> Dict[str, Any]:
    """
    Write contents to a file with proper parent directory creation.
    
    Args:
        path: Target file path
        contents: File contents to write
        overwrite: If False and file exists, leave untouched
        
    Returns:
        Dict with metadata: path, is_directory, lines_changed, sha256
        
    Raises:
        Exception: Any file system or encoding errors
    """
    path_obj = Path(path)
    
    # Ensure parent directories exist
    ensure_parents(path)
    
    # Check if file exists and overwrite is False
    if path_obj.exists() and not overwrite:
        # Read existing file to get metadata
        with open(path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        # Compute SHA256 of existing content
        existing_bytes = existing_content.encode('utf-8')
        existing_sha = hashlib.sha256(existing_bytes).hexdigest()
        
        return {
            "path": str(path_obj),
            "is_directory": False,
            "lines_changed": 0,
            "sha256": existing_sha,
        }
    
    # Write the file
    with open(path, 'w', encoding='utf-8') as f:
        f.write(contents)
    
    # Compute metadata
    content_bytes = contents.encode('utf-8')
    sha256_hash = hashlib.sha256(content_bytes).hexdigest()
    lines_changed = len(contents.splitlines())
    
    return {
        "path": str(path_obj),
        "is_directory": False,
        "lines_changed": lines_changed,
        "sha256": sha256_hash,
    }
