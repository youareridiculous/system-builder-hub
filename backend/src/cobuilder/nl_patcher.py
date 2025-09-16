#!/usr/bin/env python3
"""
Natural Language Patcher for Co-Builder

Converts plain-English edit requests into GuardedPatch objects for safe file modifications.
Enhanced with feature flags, JSON logging, and improved error handling.
"""

import re
import os
import logging
import json
import time
import hashlib
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Global config with environment variable defaults
COB_NL_TRANSLATOR_ENABLED = os.getenv('COB_NL_TRANSLATOR_ENABLED', 'true').lower() == 'true'
COB_MAX_DIFF_LINES = int(os.getenv('COB_MAX_DIFF_LINES', '25'))
COB_STRICT_IMPORTS = os.getenv('COB_STRICT_IMPORTS', 'true').lower() == 'true'
COB_DRY_RUN = os.getenv('COB_DRY_RUN', 'false').lower() == 'true'

@dataclass
class GuardedPatch:
    """Represents a constrained file patch operation"""
    target_file: str
    anchor: str
    insertion_point: str  # "before", "after", "replace"
    content: str
    constraints: List[str]
    max_lines: int = 50
    dry_run: bool = False
    allow_full_rewrite: bool = False

@dataclass
class PatchResult:
    """Result of a patch operation with metadata"""
    success: bool
    file: str
    lines_changed: int
    anchor_matched: bool
    elapsed_ms: int
    sha256: str
    dry_run: bool
    status: str
    error: Optional[str] = None
    suggested_anchors: Optional[List[str]] = None
    diff: Optional[str] = None
    snippet: Optional[str] = None

@dataclass
class PatchError:
    """Standard error shapes for patch operations"""
    error_type: str  # "anchor_not_found", "diff_too_large", "conflict_in_context", "file_not_visible"
    message: str
    suggested_anchors: Optional[List[str]] = None
    suggested_split: Optional[str] = None
    mismatched_context: Optional[str] = None

class NLPatchTranslator:
    """Translates natural language edit requests into GuardedPatch objects"""
    
    def __init__(self, project_root: str = None, config: Dict[str, Any] = None):
        self.project_root = project_root or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.config = config or {}
        self.max_diff_lines = self.config.get('max_diff_lines', COB_MAX_DIFF_LINES)
        self.strict_imports = self.config.get('strict_imports', COB_STRICT_IMPORTS)
        self.dry_run = self.config.get('dry_run', COB_DRY_RUN)
        
    def is_edit_request(self, message: str) -> bool:
        """Detect if message is an edit request"""
        edit_indicators = [
            r'\b(add|insert|append|prepend|replace|modify|edit|change)\b',
            r'\b(after|before|below|above|following|preceding)\b',
            r'\b(in|to|at)\s+[a-zA-Z_/][a-zA-Z0-9_/]*\.(py|js|ts|html|css|md|txt)\b',
            r'\b(route|endpoint|function|class|method|import|blueprint)\b',
            r'\b(anchor|line|block|section)\b'
        ]
        
        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in edit_indicators)
    
    def extract_target_file(self, message: str) -> Optional[str]:
        """Extract target file path from message"""
        # Look for explicit file paths
        file_patterns = [
            r'\b([a-zA-Z_/][a-zA-Z0-9_/]*\.(py|js|ts|html|css|md|txt))\b',
            r'\b(src/[a-zA-Z_/][a-zA-Z0-9_/]*\.py)\b',
            r'\b(venture_os/[a-zA-Z_/][a-zA-Z0-9_/]*\.py)\b'
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, message)
            if matches:
                # Return the first match, preferring src/ paths
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    if match.startswith('src/') or match.startswith('venture_os/'):
                        return match
                return matches[0] if isinstance(matches[0], str) else matches[0][0]
        
        return None
    
    def extract_anchor(self, message: str, target_file: str) -> Optional[str]:
        """Extract anchor text/pattern from message with enhanced concept resolution"""
        # Enhanced patterns for more robust anchor extraction
        anchor_patterns = [
            r'\b(after|before|below|above|following|preceding)\s+["\']?([^"\',]+)["\']?',
            r'\b(anchor|line|block|section)\s*[:\-]?\s*["\']?([^"\',]+)["\']?',
            r'\b(after|below)\s+the\s+([^,\.]+?)(?:\s+block|\s+section|\s+part|\s+area)?(?:\s|$|,|\.)',
            r'\b(at|near)\s+the\s+(?:bottom|end|top|start)\s+of\s+([^,\.]+?)(?:\s|$|,|\.)',
            r'\b(where|when)\s+([^,\.]+?)(?:\s+are\s+registered|\s+is\s+defined)(?:\s|$|,|\.)',
            r'\b(_repo\s*=)',
            r'\b(Blueprint\s*\()',
            r'\b(@.*route)',
            r'\b(def\s+\w+)',
            r'\b(class\s+\w+)',
            r'\b(import\s+\w+)'
        ]
        
        for pattern in anchor_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    # Return the second group (the actual anchor text)
                    anchor_text = matches[0][1] if matches[0][1] else matches[0][0]
                    # Clean up the anchor text - stop at comma or other delimiters
                    anchor_text = anchor_text.strip('"\'')
                    # Take only the first part before comma
                    anchor_text = anchor_text.split(',')[0].strip()
                    # Resolve conceptual anchors to concrete patterns
                    anchor_text = self._resolve_anchor_concept(anchor_text)
                    return anchor_text
                return matches[0]
        
        return None
    
    def _resolve_anchor_concept(self, anchor: str) -> str:
        """Resolve conceptual anchors to concrete patterns"""
        concept_mappings = {
            'repo selection block': '_repo',
            'repo assignment': '_repo',
            'repo initialization': '_repo',
            'blueprint registration': 'register_blueprint',
            'blueprint definition': 'Blueprint',
            'imports': 'import',
            'import block': 'import',
            'function definition': 'def ',
            'class definition': 'class ',
            'route definition': '@.*\\.route',
            'endpoint definition': '@.*\\.route',
        }
        
        # Check for exact concept matches
        for concept, pattern in concept_mappings.items():
            if concept.lower() in anchor.lower():
                return pattern
        
        # Clean up common phrases
        anchor = re.sub(r'\s+(block|section|part|area|definition|registration|assignment|initialization)$', '', anchor, flags=re.IGNORECASE)
        
        return anchor
    
    def extract_insertion_point(self, message: str) -> str:
        """Extract insertion point (before/after/replace)"""
        message_lower = message.lower()
        
        if re.search(r'\b(before|above|preceding)\b', message_lower):
            return "before"
        elif re.search(r'\b(after|below|following)\b', message_lower):
            return "after"
        elif re.search(r'\b(replace|substitute|change)\b', message_lower):
            return "replace"
        else:
            return "after"  # default
    
    def extract_constraints(self, message: str) -> List[str]:
        """Extract constraints from message"""
        constraints = []
        message_lower = message.lower()
        
        if "don't touch imports" in message_lower or "no imports" in message_lower:
            constraints.append("no_import_changes")
        
        if "don't reformat" in message_lower or "no reformatting" in message_lower or "reformat" in message_lower:
            constraints.append("no_reformatting")
        
        if "abort if" in message_lower or "don't guess" in message_lower:
            constraints.append("strict_anchor_match")
        
        if "no server" in message_lower or "don't touch server" in message_lower:
            constraints.append("no_server_changes")
        
        # Default constraints
        if not constraints:
            constraints = ["no_import_changes", "no_reformatting", "strict_anchor_match"]
        
        return constraints
    
    def generate_patch_content(self, message: str, target_file: str) -> str:
        """Generate the patch content based on the request"""
        # This is a simplified version - in practice, you'd use an LLM to generate the actual code
        # For now, we'll extract key elements and create a template
        
        content_lines = []
        
        # Look for specific patterns
        if "blueprint" in message.lower():
            content_lines.append("from flask import Blueprint, request, jsonify")
            content_lines.append("")
            content_lines.append("bp = Blueprint('venture_os', __name__, url_prefix='/api/venture_os')")
            content_lines.append("")
        
        if "route" in message.lower() and "seed" in message.lower():
            content_lines.append("@bp.route('/seed/demo', methods=['POST'])")
            content_lines.append("def seed_demo():")
            content_lines.append("    tenant_id = request.headers.get('X-Tenant-ID', 'demo_tenant')")
            content_lines.append("    from venture_os.rbac.model import Role, User")
            content_lines.append("    from venture_os.service.entity_service import create_entity")
            content_lines.append("    admin = User(id='seed_admin', tenant_id=tenant_id, email='seed@demo.local', name='Seed Admin', roles=[Role.ADMIN])")
            content_lines.append("    created = 0")
            content_lines.append("    for name in ['Acme Corp', 'Globex', 'Soylent']:")
            content_lines.append("        res = create_entity(admin, _repo, tenant_id=tenant_id, kind='company', name=name, metadata={'id': f'c_{created + 1}'})")
            content_lines.append("        if hasattr(res, 'data'): created += 1")
            content_lines.append("    return jsonify({'ok': True, 'created': created})")
            content_lines.append("")
        
        if "route" in message.lower() and "entities" in message.lower():
            content_lines.append("@bp.route('/entities', methods=['GET'])")
            content_lines.append("def list_entities():")
            content_lines.append("    tenant_id = request.headers.get('X-Tenant-ID')")
            content_lines.append("    if not tenant_id: return jsonify({'ok': False, 'error': 'missing X-Tenant-ID'}), 400")
            content_lines.append("    try:")
            content_lines.append("        limit = int(request.args.get('limit', 10))")
            content_lines.append("        offset = int(request.args.get('offset', 0))")
            content_lines.append("    except ValueError: return jsonify({'ok': False, 'error': 'invalid pagination params'}), 400")
            content_lines.append("    page = _repo.list(tenant_id=tenant_id, limit=limit, offset=offset)")
            content_lines.append("    items = [(getattr(it, 'model_dump', getattr(it, 'dict', lambda: it)))() for it in page.items]")
            content_lines.append("    return jsonify({'ok': True, 'total': page.total, 'items': items})")
            content_lines.append("")
        
        return "\n".join(content_lines)
    
    def find_anchor_in_file(self, file_path: str, anchor: str) -> Optional[Tuple[int, str]]:
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
    
    def translate(self, message: str) -> Optional[GuardedPatch]:
        """Translate natural language message to GuardedPatch"""
        if not self.is_edit_request(message):
            return None
        
        # Extract components
        target_file = self.extract_target_file(message)
        if not target_file:
            logger.warning("No target file found in message")
            return None
        
        # Resolve relative paths
        if not target_file.startswith('/'):
            target_file = os.path.join(self.project_root, target_file)
        
        anchor = self.extract_anchor(message, target_file)
        if not anchor:
            logger.warning("No anchor found in message")
            return None
        
        # Verify anchor exists in file
        anchor_info = self.find_anchor_in_file(target_file, anchor)
        if not anchor_info:
            logger.warning(f"Anchor '{anchor}' not found in {target_file}")
            return None
        
        insertion_point = self.extract_insertion_point(message)
        constraints = self.extract_constraints(message)
        content = self.generate_patch_content(message, target_file)
        
        # Check content size
        content_lines = content.count('\n') + 1 if content else 0
        if content_lines > self.max_diff_lines:
            logger.warning(f"Generated content too large: {content_lines} lines > {self.max_diff_lines}")
            return None
        
        return GuardedPatch(
            target_file=target_file,
            anchor=anchor,
            insertion_point=insertion_point,
            content=content,
            constraints=constraints,
            max_lines=self.max_diff_lines
        )
    
    def generate_unified_diff(self, patch: GuardedPatch) -> str:
        """Generate unified diff for the patch"""
        if not os.path.exists(patch.target_file):
            return f"--- /dev/null\n+++ {patch.target_file}\n@@ -0,0 +1,{patch.content.count(chr(10)) + 1} @@\n+{patch.content.replace(chr(10), chr(10) + '+')}"
        
        # Find anchor line
        anchor_info = self.find_anchor_in_file(patch.target_file, patch.anchor)
        if not anchor_info:
            return ""
        
        line_num, line_content = anchor_info
        
        # Read current file
        with open(patch.target_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Generate diff
        diff_lines = []
        diff_lines.append(f"--- a/{patch.target_file}")
        diff_lines.append(f"+++ b/{patch.target_file}")
        
        if patch.insertion_point == "after":
            # Insert after anchor line
            diff_lines.append(f"@@ -{line_num},0 +{line_num + 1},{patch.content.count(chr(10)) + 1} @@")
            diff_lines.append(f" {line_content}")
            for content_line in patch.content.split('\n'):
                diff_lines.append(f"+{content_line}")
        elif patch.insertion_point == "before":
            # Insert before anchor line
            diff_lines.append(f"@@ -{line_num - 1},0 +{line_num},{patch.content.count(chr(10)) + 1} @@")
            for content_line in patch.content.split('\n'):
                diff_lines.append(f"+{content_line}")
            diff_lines.append(f" {line_content}")
        else:  # replace
            # Replace anchor line
            diff_lines.append(f"@@ -{line_num},1 +{line_num},{patch.content.count(chr(10)) + 1} @@")
            diff_lines.append(f"-{line_content}")
            for content_line in patch.content.split('\n'):
                diff_lines.append(f"+{content_line}")
        
        return '\n'.join(diff_lines)
    
    def _log_patch_operation(self, step_id: str, role: str, result: PatchResult):
        """Emit one JSON log line with patch operation metadata"""
        log_entry = {
            "step_id": step_id,
            "role": role,
            "file": result.file,
            "lines_changed": result.lines_changed,
            "anchor_matched": result.anchor_matched,
            "elapsed_ms": result.elapsed_ms,
            "sha256": result.sha256,
            "dry_run": result.dry_run,
            "status": result.status,
            "timestamp": time.time()
        }
        logger.info(f"PATCH_OP: {json.dumps(log_entry)}")
    
    def _get_suggested_anchors(self, file_path: str, limit: int = 3) -> List[str]:
        """Get top candidate anchors from a file"""
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Look for common anchor patterns
            anchors = []
            for i, line in enumerate(lines):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Function definitions
                if re.match(r'def\s+\w+', line):
                    anchors.append(f"def {line.split('(')[0].split()[-1]}")
                # Class definitions
                elif re.match(r'class\s+\w+', line):
                    anchors.append(f"class {line.split(':')[0].split()[-1]}")
                # Variable assignments
                elif '=' in line and not line.startswith(' '):
                    var_name = line.split('=')[0].strip()
                    if len(var_name) < 20:  # Reasonable length
                        anchors.append(var_name)
                # Import statements
                elif line.startswith('import ') or line.startswith('from '):
                    anchors.append(line)
                
                if len(anchors) >= limit:
                    break
            
            return anchors[:limit]
        except Exception as e:
            logger.warning(f"Error getting suggested anchors: {e}")
            return []
    
    def _validate_file_visibility(self, file_path: str) -> bool:
        """Check if file is visible from project root"""
        try:
            abs_path = os.path.abspath(file_path)
            project_root = os.path.abspath(self.project_root)
            return abs_path.startswith(project_root + os.sep) or abs_path == project_root
        except Exception:
            return False
    
    def _calculate_sha256(self, content: str) -> str:
        """Calculate SHA256 hash of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _get_file_snippet(self, file_path: str, anchor_line: int, context_lines: int = 15) -> str:
        """Get a snippet of the file around the anchor line"""
        if not os.path.exists(file_path):
            return ""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            start = max(0, anchor_line - context_lines - 1)
            end = min(len(lines), anchor_line + context_lines)
            
            snippet_lines = []
            for i in range(start, end):
                marker = ">>> " if i == anchor_line - 1 else "    "
                snippet_lines.append(f"{marker}{i+1:3d}: {lines[i].rstrip()}")
            
            return "\n".join(snippet_lines)
        except Exception as e:
            logger.warning(f"Error getting file snippet: {e}")
            return ""
    
    def apply_patch(self, patch: GuardedPatch, step_id: str = "unknown", role: str = "nl_patcher") -> PatchResult:
        """Apply a patch with full metadata tracking and error handling"""
        start_time = time.time()
        
        try:
            # Validate file visibility
            if not self._validate_file_visibility(patch.target_file):
                error = PatchError(
                    error_type="file_not_visible",
                    message=f"File {patch.target_file} is not visible from project root"
                )
                return PatchResult(
                    success=False,
                    file=patch.target_file,
                    lines_changed=0,
                    anchor_matched=False,
                    elapsed_ms=int((time.time() - start_time) * 1000),
                    sha256="",
                    dry_run=patch.dry_run,
                    status="error",
                    error=error.message
                )
            
            # Check if anchor exists
            anchor_info = self.find_anchor_in_file(patch.target_file, patch.anchor)
            if not anchor_info:
                suggested_anchors = self._get_suggested_anchors(patch.target_file)
                error = PatchError(
                    error_type="anchor_not_found",
                    message=f"Anchor '{patch.anchor}' not found in {patch.target_file}",
                    suggested_anchors=suggested_anchors
                )
                return PatchResult(
                    success=False,
                    file=patch.target_file,
                    lines_changed=0,
                    anchor_matched=False,
                    elapsed_ms=int((time.time() - start_time) * 1000),
                    sha256="",
                    dry_run=patch.dry_run,
                    status="error",
                    error=error.message,
                    suggested_anchors=suggested_anchors
                )
            
            # Check diff size
            content_lines = patch.content.count('\n') + 1 if patch.content else 0
            if content_lines > patch.max_lines and not patch.allow_full_rewrite:
                error = PatchError(
                    error_type="diff_too_large",
                    message=f"Generated content too large: {content_lines} lines > {patch.max_lines}",
                    suggested_split=f"Split into smaller changes or set allow_full_rewrite=true"
                )
                return PatchResult(
                    success=False,
                    file=patch.target_file,
                    lines_changed=content_lines,
                    anchor_matched=True,
                    elapsed_ms=int((time.time() - start_time) * 1000),
                    sha256="",
                    dry_run=patch.dry_run,
                    status="error",
                    error=error.message
                )
            
            # Generate diff and snippet
            diff = self.generate_unified_diff(patch)
            snippet = self._get_file_snippet(patch.target_file, anchor_info[0])
            sha256 = self._calculate_sha256(patch.content)
            
            # Apply the patch if not dry run
            if not patch.dry_run:
                from .applier import apply_anchored_patch, AnchoredPatch
                rel_path = os.path.relpath(patch.target_file, self.project_root)
                if rel_path.startswith('src/'):
                    rel_path = rel_path[4:]  # Remove src/ prefix
                
                # Create anchored patch
                anchored_patch = AnchoredPatch(
                    target_file=rel_path,
                    anchor=patch.anchor,
                    insertion_point=patch.insertion_point,
                    content=patch.content,
                    max_lines=patch.max_lines,
                    allow_full_rewrite=patch.allow_full_rewrite
                )
                
                apply_result = apply_anchored_patch(anchored_patch)
                sha256 = apply_result.sha256
            
            result = PatchResult(
                success=True,
                file=patch.target_file,
                lines_changed=content_lines,
                anchor_matched=True,
                elapsed_ms=int((time.time() - start_time) * 1000),
                sha256=sha256,
                dry_run=patch.dry_run,
                status="success",
                diff=diff,
                snippet=snippet
            )
            
            # Log the operation
            self._log_patch_operation(step_id, role, result)
            
            return result
            
        except Exception as e:
            result = PatchResult(
                success=False,
                file=patch.target_file,
                lines_changed=0,
                anchor_matched=False,
                elapsed_ms=int((time.time() - start_time) * 1000),
                sha256="",
                dry_run=patch.dry_run,
                status="error",
                error=str(e)
            )
            self._log_patch_operation(step_id, role, result)
            return result
