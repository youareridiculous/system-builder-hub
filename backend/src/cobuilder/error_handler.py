#!/usr/bin/env python3
"""
Error Handler for Co-Builder

Provides standard error shapes and retry actions for patch operations.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum

class ErrorType(Enum):
    ANCHOR_NOT_FOUND = "anchor_not_found"
    DIFF_TOO_LARGE = "diff_too_large"
    CONFLICT_IN_CONTEXT = "conflict_in_context"
    FILE_NOT_VISIBLE = "file_not_visible"
    VALIDATION_ERROR = "validation_error"
    PERMISSION_ERROR = "permission_error"

@dataclass
class StandardError:
    """Standard error shape for patch operations"""
    error_type: ErrorType
    message: str
    suggested_anchors: Optional[List[str]] = None
    suggested_split: Optional[str] = None
    mismatched_context: Optional[str] = None
    retry_actions: Optional[List[Dict[str, Any]]] = None

@dataclass
class RetryAction:
    """A retry action for failed operations"""
    action: str
    description: str
    payload: Dict[str, Any]
    one_click: bool = True

class ErrorHandler:
    """Handles errors and provides retry actions"""
    
    @staticmethod
    def create_anchor_not_found_error(anchor: str, file_path: str, 
                                    suggested_anchors: List[str]) -> StandardError:
        """Create anchor not found error with suggestions"""
        retry_actions = []
        
        # Add retry actions for each suggested anchor
        for i, suggested_anchor in enumerate(suggested_anchors[:3]):
            retry_actions.append({
                "action": "use_anchor",
                "description": f"Use anchor '{suggested_anchor}'",
                "payload": {"anchor": suggested_anchor},
                "one_click": True
            })
        
        # Add manual anchor action
        retry_actions.append({
            "action": "manual_anchor",
            "description": "Specify anchor manually",
            "payload": {"prompt": "Please specify the exact anchor text"},
            "one_click": False
        })
        
        return StandardError(
            error_type=ErrorType.ANCHOR_NOT_FOUND,
            message=f"Anchor '{anchor}' not found in {file_path}",
            suggested_anchors=suggested_anchors,
            retry_actions=retry_actions
        )
    
    @staticmethod
    def create_diff_too_large_error(current_lines: int, max_lines: int, 
                                  file_path: str) -> StandardError:
        """Create diff too large error with split suggestions"""
        retry_actions = [
            {
                "action": "raise_limit",
                "description": f"Raise diff limit to {current_lines + 10} for this patch",
                "payload": {"max_diff_lines": current_lines + 10},
                "one_click": True
            },
            {
                "action": "allow_full_rewrite",
                "description": "Allow full file rewrite",
                "payload": {"allow_full_rewrite": True},
                "one_click": True
            },
            {
                "action": "split_changes",
                "description": "Split into smaller changes",
                "payload": {"prompt": "Please break this into smaller, focused changes"},
                "one_click": False
            }
        ]
        
        return StandardError(
            error_type=ErrorType.DIFF_TOO_LARGE,
            message=f"Generated content too large: {current_lines} lines > {max_lines}",
            suggested_split=f"Split into changes of {max_lines} lines or less",
            retry_actions=retry_actions
        )
    
    @staticmethod
    def create_conflict_error(expected_context: str, actual_context: str, 
                           file_path: str) -> StandardError:
        """Create conflict in context error"""
        retry_actions = [
            {
                "action": "refresh_context",
                "description": "Refresh file context and retry",
                "payload": {"refresh": True},
                "one_click": True
            },
            {
                "action": "manual_resolve",
                "description": "Manually resolve conflict",
                "payload": {"prompt": "Please resolve the context conflict manually"},
                "one_click": False
            }
        ]
        
        return StandardError(
            error_type=ErrorType.CONFLICT_IN_CONTEXT,
            message=f"Context mismatch in {file_path}",
            mismatched_context=f"Expected: {expected_context}\nActual: {actual_context}",
            retry_actions=retry_actions
        )
    
    @staticmethod
    def create_file_not_visible_error(file_path: str, project_root: str) -> StandardError:
        """Create file not visible error"""
        retry_actions = [
            {
                "action": "use_relative_path",
                "description": "Use relative path from project root",
                "payload": {"prompt": "Please specify a relative path from the project root"},
                "one_click": False
            },
            {
                "action": "create_file",
                "description": "Create new file in allowed location",
                "payload": {"create": True, "location": "src/"},
                "one_click": True
            }
        ]
        
        return StandardError(
            error_type=ErrorType.FILE_NOT_VISIBLE,
            message=f"File {file_path} is not visible from project root {project_root}",
            retry_actions=retry_actions
        )
    
    @staticmethod
    def create_validation_error(message: str, field: str = None) -> StandardError:
        """Create validation error"""
        retry_actions = [
            {
                "action": "fix_validation",
                "description": f"Fix {field or 'validation'} error",
                "payload": {"prompt": f"Please fix the {field or 'validation'} error: {message}"},
                "one_click": False
            }
        ]
        
        return StandardError(
            error_type=ErrorType.VALIDATION_ERROR,
            message=message,
            retry_actions=retry_actions
        )
    
    @staticmethod
    def create_permission_error(file_path: str, operation: str) -> StandardError:
        """Create permission error"""
        retry_actions = [
            {
                "action": "check_permissions",
                "description": "Check file permissions",
                "payload": {"check": True},
                "one_click": True
            },
            {
                "action": "use_dry_run",
                "description": "Preview changes without applying",
                "payload": {"dry_run": True},
                "one_click": True
            }
        ]
        
        return StandardError(
            error_type=ErrorType.PERMISSION_ERROR,
            message=f"Permission denied for {operation} on {file_path}",
            retry_actions=retry_actions
        )
    
    @staticmethod
    def format_error_for_ui(error: StandardError) -> Dict[str, Any]:
        """Format error for UI display"""
        return {
            "error_type": error.error_type.value,
            "message": error.message,
            "suggested_anchors": error.suggested_anchors,
            "suggested_split": error.suggested_split,
            "mismatched_context": error.mismatched_context,
            "retry_actions": error.retry_actions or []
        }
    
    @staticmethod
    def get_friendly_error_message(error: StandardError) -> str:
        """Get a user-friendly error message"""
        if error.error_type == ErrorType.ANCHOR_NOT_FOUND:
            return f"🔍 Couldn't find '{error.message.split('not found')[0].strip()}' in the file. Try one of the suggested anchors below."
        elif error.error_type == ErrorType.DIFF_TOO_LARGE:
            return f"📏 Change is too large ({error.message.split('lines >')[0].split()[-1]} lines). Consider splitting into smaller changes."
        elif error.error_type == ErrorType.CONFLICT_IN_CONTEXT:
            return f"⚠️ File has changed since we started. Please refresh and try again."
        elif error.error_type == ErrorType.FILE_NOT_VISIBLE:
            return f"🚫 File is outside the project scope. Please use a relative path from the project root."
        elif error.error_type == ErrorType.VALIDATION_ERROR:
            return f"❌ {error.message}"
        elif error.error_type == ErrorType.PERMISSION_ERROR:
            return f"🔒 Permission denied. Check file permissions or try dry-run mode."
        else:
            return f"❌ {error.message}"
