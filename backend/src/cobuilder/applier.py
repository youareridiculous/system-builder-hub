import hashlib
import os
import shutil
import tempfile
import time
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ALLOWED_ROOT = os.path.join(PROJECT_ROOT, "src")

@dataclass
class ApplyResult:
    file: str
    bytes_written: int
    created: bool
    sha256: str
    anchored: bool = False
    anchor_matched: bool = False
    lines_changed: int = 0
    backup_created: bool = False

@dataclass
class AnchoredPatch:
    """Represents an anchored patch operation"""
    target_file: str
    anchor: str
    insertion_point: str  # "before", "after", "replace"
    content: str
    max_lines: int = 25
    allow_full_rewrite: bool = False

def _safe_join(base: str, *paths: str) -> str:
    """Safely join paths, preventing directory traversal attacks"""
    p = os.path.abspath(os.path.join(base, *paths))
    if not p.startswith(base + os.sep) and p != base:
        raise ValueError("Unsafe path")
    return p

def find_anchor_in_file(file_path: str, anchor: str) -> Optional[Tuple[int, str]]:
    """Find anchor in file and return (line_number, line_content)"""
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if anchor in line:
                return (i + 1, line.rstrip())  # 1-based line numbers
        
        return None
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None

def create_backup(file_path: str) -> str:
    """Create a backup of the file and return backup path"""
    backup_path = f"{file_path}.backup.{int(time.time())}"
    shutil.copy2(file_path, backup_path)
    return backup_path

def restore_backup(backup_path: str, file_path: str) -> bool:
    """Restore file from backup"""
    try:
        shutil.copy2(backup_path, file_path)
        return True
    except Exception as e:
        logger.error(f"Failed to restore backup: {e}")
        return False

def apply_anchored_patch(patch: AnchoredPatch) -> ApplyResult:
    """Apply an anchored patch with safety checks and atomic operations"""
    # Resolve target file path
    if os.path.isabs(patch.target_file):
        target_file = patch.target_file
    else:
        target_file = _safe_join(ALLOWED_ROOT, os.path.normpath(patch.target_file.replace("\\", "/")))
    
    # Check if file exists
    if not os.path.exists(target_file):
        # For new files, use regular apply
        return apply_single_file(os.path.relpath(target_file, ALLOWED_ROOT), patch.content)
    
    # Find anchor
    anchor_info = find_anchor_in_file(target_file, patch.anchor)
    if not anchor_info:
        raise ValueError(f"Anchor '{patch.anchor}' not found in {target_file}")
    
    line_num, line_content = anchor_info
    
    # Check content size
    content_lines = patch.content.count('\n') + 1 if patch.content else 0
    if content_lines > patch.max_lines and not patch.allow_full_rewrite:
        raise ValueError(f"Generated content too large: {content_lines} lines > {patch.max_lines}")
    
    # Create backup
    backup_path = create_backup(target_file)
    
    try:
        # Read current file
        with open(target_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Apply patch
        new_lines = lines.copy()
        if patch.insertion_point == "after":
            # Insert after anchor line
            new_lines.insert(line_num, patch.content + '\n')
        elif patch.insertion_point == "before":
            # Insert before anchor line
            new_lines.insert(line_num - 1, patch.content + '\n')
        else:  # replace
            # Replace anchor line
            new_lines[line_num - 1] = patch.content + '\n'
        
        # Write to temp file first
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as temp_file:
            temp_file.writelines(new_lines)
            temp_path = temp_file.name
        
        # Verify SHA256 of temp file
        with open(temp_path, 'rb') as f:
            temp_sha = hashlib.sha256(f.read()).hexdigest()
        
        # Atomic move
        shutil.move(temp_path, target_file)
        
        # Calculate final SHA256
        with open(target_file, 'rb') as f:
            final_sha = hashlib.sha256(f.read()).hexdigest()
        
        # Clean up backup on success
        os.remove(backup_path)
        
        return ApplyResult(
            file=os.path.relpath(target_file, PROJECT_ROOT),
            bytes_written=len(''.join(new_lines).encode("utf-8")),
            created=False,
            sha256=final_sha,
            anchored=True,
            anchor_matched=True,
            lines_changed=content_lines,
            backup_created=True
        )
        
    except Exception as e:
        # Restore backup on failure
        restore_backup(backup_path, target_file)
        os.remove(backup_path)
        raise e

def apply_single_file(rel_path: str, content: str, require_anchor: bool = True) -> ApplyResult:
    """Apply a single file change, creating parent directories as needed"""
    # Only allow files under src/
    dest = _safe_join(ALLOWED_ROOT, os.path.normpath(rel_path.replace("\\", "/")))
    
    # Check if this is a full file rewrite
    if require_anchor and os.path.exists(dest):
        # Read existing content to check if it's a full rewrite
        with open(dest, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        # If content is significantly different, require anchor
        if content != existing_content and (len(content) > 100 or len(content) < len(existing_content) * 0.1):
            raise ValueError("Full file rewrite detected. Please provide an anchor or set allow_full_rewrite=true")
    
    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    
    # Check if file already exists
    created = not os.path.exists(dest)
    
    # Create backup if file exists
    backup_created = False
    if not created:
        backup_path = create_backup(dest)
        backup_created = True
    
    try:
        # Write the content
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        
        # Calculate SHA256 hash
        with open(dest, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        
        # Clean up backup on success
        if backup_created:
            os.remove(backup_path)
            backup_created = False
        
        return ApplyResult(
            file=os.path.relpath(dest, PROJECT_ROOT),
            bytes_written=len(content.encode("utf-8")),
            created=created,
            sha256=sha,
            anchored=False,
            anchor_matched=False,
            lines_changed=content.count('\n') + 1,
            backup_created=backup_created
        )
        
    except Exception as e:
        # Restore backup on failure
        if backup_created and os.path.exists(backup_path):
            restore_backup(backup_path, dest)
            os.remove(backup_path)
        raise e
