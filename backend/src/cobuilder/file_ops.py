"""
File operations utilities for Co-Builder
"""
import os
import hashlib
from pathlib import Path
from typing import Optional


def ensure_parents(file_path: str) -> None:
    """Ensure parent directories exist for a file path"""
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)


def write_file(file_path: str, content: str, log_fn=None) -> None:
    """Write content to a file, creating parent directories if needed"""
    ensure_parents(file_path)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    if log_fn:
        log_fn(f"Created {file_path}")


def read_file(file_path: str) -> Optional[str]:
    """Read content from a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return None


def file_exists(file_path: str) -> bool:
    """Check if a file exists"""
    return os.path.isfile(file_path)


def dir_exists(dir_path: str) -> bool:
    """Check if a directory exists"""
    return os.path.isdir(dir_path)


def calculate_sha256(file_path: str) -> str:
    """Calculate SHA256 hash of a file"""
    if not file_exists(file_path):
        return ""
    
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def calculate_content_sha256(content: str) -> str:
    """Calculate SHA256 hash of content string"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def count_lines(file_path: str) -> int:
    """Count lines in a file"""
    if not file_exists(file_path):
        return 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return sum(1 for _ in f)


def list_files(directory: str, pattern: str = "*") -> list:
    """List files in a directory matching a pattern"""
    if not dir_exists(directory):
        return []
    
    return [str(p) for p in Path(directory).glob(pattern) if p.is_file()]


def list_dirs(directory: str, pattern: str = "*") -> list:
    """List directories in a directory matching a pattern"""
    if not dir_exists(directory):
        return []
    
    return [str(p) for p in Path(directory).glob(pattern) if p.is_dir()]
