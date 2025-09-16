#!/usr/bin/env python3
"""
Response Builder for Co-Builder

Creates structured, clear responses with role separation and metadata.
"""

import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from enum import Enum

class Role(Enum):
    USER = "user"
    CO_BUILDER = "co_builder"
    APPLY_ENGINE = "apply_engine"
    SMOKE_SCRIPT = "smoke_script"

@dataclass
class ResponseSection:
    """A section of a structured response"""
    title: str
    content: str
    collapsible: bool = False
    role: Role = Role.CO_BUILDER

@dataclass
class StructuredResponse:
    """A structured response with multiple sections"""
    success: bool
    role: Role
    step_id: str
    tenant_id: str
    status: str
    elapsed_ms: int
    timestamp: float
    sections: List[ResponseSection]
    metadata: Dict[str, Any]
    retry_actions: Optional[List[Dict[str, Any]]] = None

class ResponseBuilder:
    """Builds structured responses for Co-Builder"""
    
    def __init__(self, step_id: str, tenant_id: str, role: Role = Role.CO_BUILDER):
        self.step_id = step_id
        self.tenant_id = tenant_id
        self.role = role
        self.start_time = time.time()
        self.sections = []
        self.metadata = {}
        self.retry_actions = []
    
    def add_prompt_section(self, intent: str, message: str):
        """Add PROMPT section with parsed intent"""
        content = f"**Intent:** {intent}\n**Message:** {message}"
        self.sections.append(ResponseSection(
            title="PROMPT",
            content=content,
            role=Role.USER
        ))
        return self
    
    def add_plan_section(self, plan_items: List[str]):
        """Add PLAN section with 1-3 bullets"""
        content = "\n".join([f"• {item}" for item in plan_items])
        self.sections.append(ResponseSection(
            title="PLAN",
            content=content,
            role=Role.CO_BUILDER
        ))
        return self
    
    def add_result_section(self, success: bool, file: str, bytes_written: int, 
                          sha256: str, elapsed_ms: int, anchor_matched: bool = True, 
                          lines_changed: int = 0):
        """Add RESULT section with ✅/❌ and metadata"""
        status_icon = "✅" if success else "❌"
        content = f"{status_icon} **File:** {file}\n"
        content += f"**Bytes:** {bytes_written}\n"
        content += f"**SHA256:** {sha256[:16]}...\n"
        content += f"**Elapsed:** {elapsed_ms}ms\n"
        if anchor_matched is not None:
            content += f"**Anchor Matched:** {anchor_matched}\n"
        if lines_changed > 0:
            content += f"**Lines Changed:** {lines_changed}"
        
        self.sections.append(ResponseSection(
            title="RESULT",
            content=content,
            role=Role.APPLY_ENGINE
        ))
        return self
    
    def add_diff_section(self, diff: str):
        """Add DIFF section (collapsible)"""
        self.sections.append(ResponseSection(
            title="DIFF",
            content=diff,
            collapsible=True,
            role=Role.APPLY_ENGINE
        ))
        return self
    
    def add_snippet_section(self, snippet: str, context_lines: int = 20):
        """Add SNIPPET section with 20-30 lines"""
        lines = snippet.split('\n')
        if len(lines) > context_lines:
            lines = lines[:context_lines]
            lines.append("... (truncated)")
        
        content = "\n".join(lines)
        self.sections.append(ResponseSection(
            title="SNIPPET",
            content=content,
            role=Role.APPLY_ENGINE
        ))
        return self
    
    def add_error_section(self, error_type: str, message: str, suggestions: Optional[List[str]] = None):
        """Add error section with suggestions"""
        content = f"**Error Type:** {error_type}\n**Message:** {message}"
        if suggestions:
            content += "\n**Suggestions:**\n" + "\n".join([f"• {s}" for s in suggestions])
        
        self.sections.append(ResponseSection(
            title="ERROR",
            content=content,
            role=Role.APPLY_ENGINE
        ))
        return self
    
    def add_retry_action(self, action: str, description: str, payload: Dict[str, Any]):
        """Add a retry action"""
        self.retry_actions.append({
            "action": action,
            "description": description,
            "payload": payload
        })
        return self
    
    def set_metadata(self, **kwargs):
        """Set metadata fields"""
        self.metadata.update(kwargs)
        return self
    
    def build(self, success: bool, status: str = "completed") -> StructuredResponse:
        """Build the final structured response"""
        elapsed_ms = int((time.time() - self.start_time) * 1000)
        
        return StructuredResponse(
            success=success,
            role=self.role,
            step_id=self.step_id,
            tenant_id=self.tenant_id,
            status=status,
            elapsed_ms=elapsed_ms,
            timestamp=time.time(),
            sections=self.sections,
            metadata=self.metadata,
            retry_actions=self.retry_actions if self.retry_actions else None
        )
    
    def to_dict(self, success: bool, status: str = "completed") -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        response = self.build(success, status)
        return asdict(response)
    
    def to_frontend_format(self, success: bool, status: str = "completed") -> Dict[str, Any]:
        """Convert to frontend-friendly format"""
        response = self.build(success, status)
        
        # Create role-based sections
        sections_by_role = {}
        for section in response.sections:
            role_name = section.role.value
            if role_name not in sections_by_role:
                sections_by_role[role_name] = []
            sections_by_role[role_name].append({
                "title": section.title,
                "content": section.content,
                "collapsible": section.collapsible
            })
        
        return {
            "success": response.success,
            "step_id": response.step_id,
            "tenant_id": response.tenant_id,
            "status": response.status,
            "elapsed_ms": response.elapsed_ms,
            "sections": sections_by_role,
            "metadata": response.metadata,
            "retry_actions": response.retry_actions,
            "sticky_header": {
                "tenant": response.tenant_id,
                "step": response.step_id,
                "status": response.status,
                "elapsed_ms": response.elapsed_ms
            }
        }

def create_nl_patch_response(step_id: str, tenant_id: str, patch_result: Any, 
                           intent: str, message: str) -> Dict[str, Any]:
    """Create a structured response for NL patch operations"""
    builder = ResponseBuilder(step_id, tenant_id, Role.CO_BUILDER)
    
    # Add prompt section
    builder.add_prompt_section(intent, message)
    
    # Add plan section
    plan_items = [
        f"Parse edit request for {patch_result.file}",
        f"Find anchor in file",
        f"Apply {patch_result.lines_changed} lines"
    ]
    builder.add_plan_section(plan_items)
    
    # Add result section
    builder.add_result_section(
        success=patch_result.success,
        file=patch_result.file,
        bytes_written=len(patch_result.content.encode('utf-8')) if hasattr(patch_result, 'content') else 0,
        sha256=patch_result.sha256,
        elapsed_ms=patch_result.elapsed_ms,
        anchor_matched=patch_result.anchor_matched,
        lines_changed=patch_result.lines_changed
    )
    
    # Set required metadata fields
    builder.set_metadata(
        role="nl_patcher",
        step=step_id,
        file=patch_result.file,
        bytes=len(patch_result.content.encode('utf-8')) if hasattr(patch_result, 'content') else 0,
        sha256=patch_result.sha256,
        elapsed_ms=patch_result.elapsed_ms,
        status=patch_result.status,
        anchor_matched=patch_result.anchor_matched,
        lines_changed=patch_result.lines_changed,
        dry_run=patch_result.dry_run,
        anchored=True
    )
    
    # Add diff and snippet if available
    if hasattr(patch_result, 'diff') and patch_result.diff:
        builder.add_diff_section(patch_result.diff)
    
    if hasattr(patch_result, 'snippet') and patch_result.snippet:
        builder.add_snippet_section(patch_result.snippet)
    
    # Add error section if failed
    if not patch_result.success:
        builder.add_error_section(
            error_type="patch_failed",
            message=patch_result.error or "Unknown error",
            suggestions=patch_result.suggested_anchors
        )
        
        # Add retry actions
        if patch_result.suggested_anchors:
            for anchor in patch_result.suggested_anchors[:2]:  # Top 2 suggestions
                builder.add_retry_action(
                    action="use_anchor",
                    description=f"Use anchor '{anchor}'",
                    payload={"anchor": anchor}
                )
    
    # Set metadata
    builder.set_metadata(
        model="nl_patcher",
        dry_run=patch_result.dry_run,
        anchored=patch_result.anchor_matched
    )
    
    return builder.to_frontend_format(patch_result.success)
