"""
Approval Pipeline System
Priority 12: Team Collaboration & Org Management Layer
"""

import os
import json
import sqlite3
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any
import uuid


class ApprovalStatus(Enum):
    """Approval status"""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class ApprovalTrigger(Enum):
    """Approval triggers"""
    MANUAL = "manual"
    AUTO_ON_COMPLETE = "auto_on_complete"
    AUTO_ON_EXPORT = "auto_on_export"
    SCHEDULED = "scheduled"
    ROLE_BASED = "role_based"


class ApprovalType(Enum):
    """Approval types"""
    SYSTEM_BUILD = "system_build"
    AGENT_CREATION = "agent_creation"
    TEMPLATE_PUBLISH = "template_publish"
    EXPORT_DELIVERY = "export_delivery"
    CONFIGURATION_CHANGE = "configuration_change"
    ACCESS_PERMISSION = "access_permission"


class ReviewerRole(Enum):
    """Reviewer roles"""
    EDITOR = "editor"
    REVIEWER = "reviewer"
    QA = "qa"
    ARCHITECT = "architect"
    PROJECT_MANAGER = "project_manager"
    ADMIN = "admin"


@dataclass
class ApprovalRequest:
    """Approval request entity"""
    request_id: str
    resource_id: str
    resource_type: str
    organization_id: str
    requester_id: str
    approval_type: ApprovalType
    status: ApprovalStatus
    title: str
    description: str
    created_at: datetime
    updated_at: datetime
    trigger: ApprovalTrigger
    required_approvers: List[str]
    current_approvers: List[str]
    approved_by: List[str]
    rejected_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    rejection_notes: Optional[str] = None
    metadata: Dict[str, Any] = None
    expires_at: Optional[datetime] = None
    auto_approve_after: Optional[datetime] = None


@dataclass
class ApprovalLog:
    """Approval log entry"""
    log_id: str
    request_id: str
    reviewer_id: str
    reviewer_role: ReviewerRole
    action: str  # approve, reject, comment, request_changes
    timestamp: datetime
    notes: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class ApprovalWorkflow:
    """Approval workflow configuration"""
    workflow_id: str
    organization_id: str
    approval_type: ApprovalType
    name: str
    description: str
    required_roles: List[ReviewerRole]
    min_approvers: int
    auto_approve_after_hours: Optional[int] = None
    escalation_after_hours: Optional[int] = None
    escalation_roles: List[ReviewerRole] = None
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class ApprovalTemplate:
    """Approval template for common workflows"""
    template_id: str
    organization_id: str
    name: str
    description: str
    approval_type: ApprovalType
    workflow_config: Dict[str, Any]
    is_default: bool = False
    created_at: datetime = None
    updated_at: datetime = None


class ApprovalPipeline:
    """Approval Pipeline System"""
    
    def __init__(self, base_dir: str, access_control, system_delivery, llm_factory):
        self.base_dir = base_dir
        self.access_control = access_control
        self.system_delivery = system_delivery
        self.llm_factory = llm_factory
        self.db_path = f"{base_dir}/approval_pipeline.db"
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize approval pipeline database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS approval_requests (
                    request_id TEXT PRIMARY KEY,
                    resource_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    requester_id TEXT NOT NULL,
                    approval_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    required_approvers TEXT NOT NULL,
                    current_approvers TEXT NOT NULL,
                    approved_by TEXT NOT NULL,
                    rejected_by TEXT,
                    rejection_reason TEXT,
                    rejection_notes TEXT,
                    metadata TEXT,
                    expires_at TEXT,
                    auto_approve_after TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS approval_logs (
                    log_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    reviewer_role TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    notes TEXT,
                    metadata TEXT,
                    FOREIGN KEY (request_id) REFERENCES approval_requests (request_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS approval_workflows (
                    workflow_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    approval_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    required_roles TEXT NOT NULL,
                    min_approvers INTEGER NOT NULL,
                    auto_approve_after_hours INTEGER,
                    escalation_after_hours INTEGER,
                    escalation_roles TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS approval_templates (
                    template_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    approval_type TEXT NOT NULL,
                    workflow_config TEXT NOT NULL,
                    is_default BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
    
    def create_approval_request(self, resource_id: str, resource_type: str, organization_id: str,
                              requester_id: str, approval_type: ApprovalType, title: str,
                              description: str, trigger: ApprovalTrigger = ApprovalTrigger.MANUAL,
                              required_approvers: List[str] = None, metadata: Dict[str, Any] = None,
                              expires_at: Optional[datetime] = None) -> ApprovalRequest:
        """Create a new approval request"""
        request_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Get default approvers if not specified
        if not required_approvers:
            required_approvers = self._get_default_approvers(organization_id, approval_type)
        
        # Create approval request
        request = ApprovalRequest(
            request_id=request_id,
            resource_id=resource_id,
            resource_type=resource_type,
            organization_id=organization_id,
            requester_id=requester_id,
            approval_type=approval_type,
            status=ApprovalStatus.DRAFT,
            title=title,
            description=description,
            created_at=now,
            updated_at=now,
            trigger=trigger,
            required_approvers=required_approvers,
            current_approvers=[],
            approved_by=[],
            metadata=metadata or {},
            expires_at=expires_at
        )
        
        # Save request
        self._save_approval_request(request)
        
        # Create initial log entry
        self._create_log_entry(request_id, requester_id, ReviewerRole.EDITOR, "created", "Request created")
        
        return request
    
    def submit_for_review(self, request_id: str, submitted_by: str) -> bool:
        """Submit approval request for review"""
        request = self.get_approval_request(request_id)
        if not request:
            return False
        
        # Check if user can submit for review
        if not self._can_submit_for_review(submitted_by, request.organization_id):
            raise PermissionError(f"User {submitted_by} cannot submit for review")
        
        # Update status
        request.status = ApprovalStatus.IN_REVIEW
        request.updated_at = datetime.now()
        
        # Set auto-approve time if configured
        workflow = self._get_workflow_for_type(request.organization_id, request.approval_type)
        if workflow and workflow.auto_approve_after_hours:
            request.auto_approve_after = datetime.now().replace(
                hour=datetime.now().hour + workflow.auto_approve_after_hours
            )
        
        # Save request
        self._save_approval_request(request)
        
        # Create log entry
        self._create_log_entry(request_id, submitted_by, ReviewerRole.EDITOR, "submitted", "Submitted for review")
        
        # Send notifications to approvers
        self._notify_approvers(request)
        
        return True
    
    def approve_request(self, request_id: str, approver_id: str, notes: str = None) -> bool:
        """Approve an approval request"""
        request = self.get_approval_request(request_id)
        if not request:
            return False
        
        # Check if user can approve
        if not self._can_approve(approver_id, request.organization_id, request.approval_type):
            raise PermissionError(f"User {approver_id} cannot approve this request")
        
        # Check if already approved by this user
        if approver_id in request.approved_by:
            raise ValueError(f"User {approver_id} has already approved this request")
        
        # Add to approved list
        request.approved_by.append(approver_id)
        request.current_approvers.append(approver_id)
        request.updated_at = datetime.now()
        
        # Check if enough approvals
        workflow = self._get_workflow_for_type(request.organization_id, request.approval_type)
        min_approvers = workflow.min_approvers if workflow else 1
        
        if len(request.approved_by) >= min_approvers:
            request.status = ApprovalStatus.APPROVED
            request.updated_at = datetime.now()
            
            # Create log entry for approval
            self._create_log_entry(request_id, approver_id, ReviewerRole.REVIEWER, "approved", notes)
            
            # Create log entry for final approval
            self._create_log_entry(request_id, approver_id, ReviewerRole.REVIEWER, "final_approved", "Request fully approved")
            
            # Trigger post-approval actions
            self._handle_post_approval(request)
        else:
            # Create log entry for partial approval
            self._create_log_entry(request_id, approver_id, ReviewerRole.REVIEWER, "approved", notes)
        
        # Save request
        self._save_approval_request(request)
        
        return True
    
    def reject_request(self, request_id: str, rejector_id: str, reason: str, notes: str = None) -> bool:
        """Reject an approval request"""
        request = self.get_approval_request(request_id)
        if not request:
            return False
        
        # Check if user can reject
        if not self._can_reject(rejector_id, request.organization_id, request.approval_type):
            raise PermissionError(f"User {rejector_id} cannot reject this request")
        
        # Update request
        request.status = ApprovalStatus.REJECTED
        request.rejected_by = rejector_id
        request.rejection_reason = reason
        request.rejection_notes = notes
        request.updated_at = datetime.now()
        
        # Save request
        self._save_approval_request(request)
        
        # Create log entry
        self._create_log_entry(request_id, rejector_id, ReviewerRole.REVIEWER, "rejected", f"Rejected: {reason}")
        
        # Send notification to requester
        self._notify_requester_rejection(request)
        
        return True
    
    def request_changes(self, request_id: str, reviewer_id: str, changes_requested: str) -> bool:
        """Request changes to an approval request"""
        request = self.get_approval_request(request_id)
        if not request:
            return False
        
        # Check if user can request changes
        if not self._can_request_changes(reviewer_id, request.organization_id, request.approval_type):
            raise PermissionError(f"User {reviewer_id} cannot request changes")
        
        # Create log entry
        self._create_log_entry(request_id, reviewer_id, ReviewerRole.REVIEWER, "requested_changes", changes_requested)
        
        # Send notification to requester
        self._notify_requester_changes(request, changes_requested)
        
        return True
    
    def publish_approved_request(self, request_id: str, publisher_id: str) -> bool:
        """Publish an approved request"""
        request = self.get_approval_request(request_id)
        if not request:
            return False
        
        # Check if request is approved
        if request.status != ApprovalStatus.APPROVED:
            raise ValueError(f"Request {request_id} is not approved")
        
        # Check if user can publish
        if not self._can_publish(publisher_id, request.organization_id, request.approval_type):
            raise PermissionError(f"User {publisher_id} cannot publish this request")
        
        # Update status
        request.status = ApprovalStatus.PUBLISHED
        request.updated_at = datetime.now()
        
        # Save request
        self._save_approval_request(request)
        
        # Create log entry
        self._create_log_entry(request_id, publisher_id, ReviewerRole.ADMIN, "published", "Request published")
        
        # Trigger post-publish actions
        self._handle_post_publish(request)
        
        return True
    
    def create_workflow(self, organization_id: str, approval_type: ApprovalType, name: str,
                       description: str, required_roles: List[ReviewerRole], min_approvers: int,
                       auto_approve_after_hours: Optional[int] = None,
                       escalation_after_hours: Optional[int] = None,
                       escalation_roles: List[ReviewerRole] = None) -> ApprovalWorkflow:
        """Create a new approval workflow"""
        workflow_id = str(uuid.uuid4())
        now = datetime.now()
        
        workflow = ApprovalWorkflow(
            workflow_id=workflow_id,
            organization_id=organization_id,
            approval_type=approval_type,
            name=name,
            description=description,
            required_roles=required_roles,
            min_approvers=min_approvers,
            auto_approve_after_hours=auto_approve_after_hours,
            escalation_after_hours=escalation_after_hours,
            escalation_roles=escalation_roles or [],
            created_at=now,
            updated_at=now
        )
        
        # Save workflow
        self._save_workflow(workflow)
        
        return workflow
    
    def create_template(self, organization_id: str, name: str, description: str,
                       approval_type: ApprovalType, workflow_config: Dict[str, Any],
                       is_default: bool = False) -> ApprovalTemplate:
        """Create an approval template"""
        template_id = str(uuid.uuid4())
        now = datetime.now()
        
        template = ApprovalTemplate(
            template_id=template_id,
            organization_id=organization_id,
            name=name,
            description=description,
            approval_type=approval_type,
            workflow_config=workflow_config,
            is_default=is_default,
            created_at=now,
            updated_at=now
        )
        
        # Save template
        self._save_template(template)
        
        return template
    
    def get_approval_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get approval request by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM approval_requests WHERE request_id = ?
            """, (request_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_approval_request(row)
            return None
    
    def get_resource_approvals(self, resource_id: str, resource_type: str,
                             organization_id: str) -> List[ApprovalRequest]:
        """Get all approval requests for a resource"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM approval_requests 
                WHERE resource_id = ? AND resource_type = ? AND organization_id = ?
                ORDER BY created_at DESC
            """, (resource_id, resource_type, organization_id))
            
            return [self._row_to_approval_request(row) for row in cursor.fetchall()]
    
    def get_user_approvals(self, user_id: str, organization_id: str,
                          status: Optional[ApprovalStatus] = None) -> List[ApprovalRequest]:
        """Get approval requests for a user"""
        query = """
            SELECT * FROM approval_requests 
            WHERE (requester_id = ? OR ? IN required_approvers) AND organization_id = ?
        """
        params = [user_id, user_id, organization_id]
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        query += " ORDER BY created_at DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_approval_request(row) for row in cursor.fetchall()]
    
    def get_pending_approvals(self, organization_id: str) -> List[ApprovalRequest]:
        """Get pending approval requests"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM approval_requests 
                WHERE organization_id = ? AND status = 'in_review'
                ORDER BY created_at ASC
            """, (organization_id,))
            
            return [self._row_to_approval_request(row) for row in cursor.fetchall()]
    
    def get_approval_logs(self, request_id: str) -> List[ApprovalLog]:
        """Get approval logs for a request"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM approval_logs 
                WHERE request_id = ?
                ORDER BY timestamp ASC
            """, (request_id,))
            
            return [self._row_to_approval_log(row) for row in cursor.fetchall()]
    
    def get_workflow(self, workflow_id: str) -> Optional[ApprovalWorkflow]:
        """Get workflow by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM approval_workflows WHERE workflow_id = ?
            """, (workflow_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_workflow(row)
            return None
    
    def get_organization_workflows(self, organization_id: str) -> List[ApprovalWorkflow]:
        """Get all workflows for an organization"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM approval_workflows 
                WHERE organization_id = ? AND is_active = TRUE
                ORDER BY name
            """, (organization_id,))
            
            return [self._row_to_workflow(row) for row in cursor.fetchall()]
    
    def get_templates(self, organization_id: str) -> List[ApprovalTemplate]:
        """Get approval templates for an organization"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM approval_templates 
                WHERE organization_id = ?
                ORDER BY is_default DESC, name
            """, (organization_id,))
            
            return [self._row_to_template(row) for row in cursor.fetchall()]
    
    def get_approval_statistics(self, organization_id: str) -> Dict[str, Any]:
        """Get approval statistics for organization"""
        with sqlite3.connect(self.db_path) as conn:
            # Total requests
            cursor = conn.execute("""
                SELECT COUNT(*) FROM approval_requests WHERE organization_id = ?
            """, (organization_id,))
            total_requests = cursor.fetchone()[0]
            
            # Requests by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) FROM approval_requests 
                WHERE organization_id = ? GROUP BY status
            """, (organization_id,))
            status_distribution = dict(cursor.fetchall())
            
            # Requests by type
            cursor = conn.execute("""
                SELECT approval_type, COUNT(*) FROM approval_requests 
                WHERE organization_id = ? GROUP BY approval_type
            """, (organization_id,))
            type_distribution = dict(cursor.fetchall())
            
            # Average approval time
            cursor = conn.execute("""
                SELECT AVG(
                    (julianday(updated_at) - julianday(created_at)) * 24
                ) FROM approval_requests 
                WHERE organization_id = ? AND status IN ('approved', 'rejected')
            """, (organization_id,))
            avg_approval_time = cursor.fetchone()[0] or 0
            
            return {
                "total_requests": total_requests,
                "status_distribution": status_distribution,
                "type_distribution": type_distribution,
                "avg_approval_time_hours": round(avg_approval_time, 2)
            }
    
    def _get_default_approvers(self, organization_id: str, approval_type: ApprovalType) -> List[str]:
        """Get default approvers for approval type"""
        workflow = self._get_workflow_for_type(organization_id, approval_type)
        if workflow:
            # This would integrate with access_control to get users with required roles
            # For now, return mock data
            return ["admin_user", "reviewer_user"]
        return ["admin_user"]
    
    def _get_workflow_for_type(self, organization_id: str, approval_type: ApprovalType) -> Optional[ApprovalWorkflow]:
        """Get workflow for approval type"""
        workflows = self.get_organization_workflows(organization_id)
        for workflow in workflows:
            if workflow.approval_type == approval_type:
                return workflow
        return None
    
    def _can_submit_for_review(self, user_id: str, organization_id: str) -> bool:
        """Check if user can submit for review"""
        # This would integrate with access_control system
        return True
    
    def _can_approve(self, user_id: str, organization_id: str, approval_type: ApprovalType) -> bool:
        """Check if user can approve"""
        # This would integrate with access_control system
        return True
    
    def _can_reject(self, user_id: str, organization_id: str, approval_type: ApprovalType) -> bool:
        """Check if user can reject"""
        # This would integrate with access_control system
        return True
    
    def _can_request_changes(self, user_id: str, organization_id: str, approval_type: ApprovalType) -> bool:
        """Check if user can request changes"""
        # This would integrate with access_control system
        return True
    
    def _can_publish(self, user_id: str, organization_id: str, approval_type: ApprovalType) -> bool:
        """Check if user can publish"""
        # This would integrate with access_control system
        return True
    
    def _notify_approvers(self, request: ApprovalRequest):
        """Send notifications to approvers"""
        # This would integrate with notification system
        for approver_id in request.required_approvers:
            print(f"Notification: {approver_id} needs to approve request {request.request_id}")
    
    def _notify_requester_rejection(self, request: ApprovalRequest):
        """Send rejection notification to requester"""
        # This would integrate with notification system
        print(f"Notification: Request {request.request_id} rejected by {request.rejected_by}")
    
    def _notify_requester_changes(self, request: ApprovalRequest, changes_requested: str):
        """Send changes notification to requester"""
        # This would integrate with notification system
        print(f"Notification: Changes requested for request {request.request_id}")
    
    def _handle_post_approval(self, request: ApprovalRequest):
        """Handle post-approval actions"""
        # This would trigger system delivery or other actions
        print(f"Post-approval: Request {request.request_id} approved, triggering actions")
    
    def _handle_post_publish(self, request: ApprovalRequest):
        """Handle post-publish actions"""
        # This would trigger publishing actions
        print(f"Post-publish: Request {request.request_id} published")
    
    def _create_log_entry(self, request_id: str, reviewer_id: str, reviewer_role: ReviewerRole,
                         action: str, notes: str = None, metadata: Dict[str, Any] = None):
        """Create approval log entry"""
        log_id = str(uuid.uuid4())
        now = datetime.now()
        
        log = ApprovalLog(
            log_id=log_id,
            request_id=request_id,
            reviewer_id=reviewer_id,
            reviewer_role=reviewer_role,
            action=action,
            timestamp=now,
            notes=notes,
            metadata=metadata or {}
        )
        
        self._save_approval_log(log)
    
    def _save_approval_request(self, request: ApprovalRequest):
        """Save approval request to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO approval_requests 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.request_id, request.resource_id, request.resource_type,
                request.organization_id, request.requester_id, request.approval_type.value,
                request.status.value, request.title, request.description,
                request.created_at.isoformat(), request.updated_at.isoformat(),
                request.trigger.value, json.dumps(request.required_approvers),
                json.dumps(request.current_approvers), json.dumps(request.approved_by),
                request.rejected_by, request.rejection_reason, request.rejection_notes,
                json.dumps(request.metadata) if request.metadata else None,
                request.expires_at.isoformat() if request.expires_at else None,
                request.auto_approve_after.isoformat() if request.auto_approve_after else None
            ))
            conn.commit()
    
    def _save_approval_log(self, log: ApprovalLog):
        """Save approval log to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO approval_logs 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log.log_id, log.request_id, log.reviewer_id, log.reviewer_role.value,
                log.action, log.timestamp.isoformat(), log.notes,
                json.dumps(log.metadata) if log.metadata else None
            ))
            conn.commit()
    
    def _save_workflow(self, workflow: ApprovalWorkflow):
        """Save workflow to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO approval_workflows 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow.workflow_id, workflow.organization_id, workflow.approval_type.value,
                workflow.name, workflow.description, json.dumps([r.value for r in workflow.required_roles]),
                workflow.min_approvers, workflow.auto_approve_after_hours,
                workflow.escalation_after_hours,
                json.dumps([r.value for r in workflow.escalation_roles]) if workflow.escalation_roles else None,
                workflow.is_active, workflow.created_at.isoformat(), workflow.updated_at.isoformat()
            ))
            conn.commit()
    
    def _save_template(self, template: ApprovalTemplate):
        """Save template to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO approval_templates 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template.template_id, template.organization_id, template.name,
                template.description, template.approval_type.value,
                json.dumps(template.workflow_config), template.is_default,
                template.created_at.isoformat(), template.updated_at.isoformat()
            ))
            conn.commit()
    
    def _row_to_approval_request(self, row) -> ApprovalRequest:
        """Convert database row to ApprovalRequest object"""
        return ApprovalRequest(
            request_id=row[0],
            resource_id=row[1],
            resource_type=row[2],
            organization_id=row[3],
            requester_id=row[4],
            approval_type=ApprovalType(row[5]),
            status=ApprovalStatus(row[6]),
            title=row[7],
            description=row[8],
            created_at=datetime.fromisoformat(row[9]),
            updated_at=datetime.fromisoformat(row[10]),
            trigger=ApprovalTrigger(row[11]),
            required_approvers=json.loads(row[12]),
            current_approvers=json.loads(row[13]),
            approved_by=json.loads(row[14]),
            rejected_by=row[15],
            rejection_reason=row[16],
            rejection_notes=row[17],
            metadata=json.loads(row[18]) if row[18] else {},
            expires_at=datetime.fromisoformat(row[19]) if row[19] else None,
            auto_approve_after=datetime.fromisoformat(row[20]) if row[20] else None
        )
    
    def _row_to_approval_log(self, row) -> ApprovalLog:
        """Convert database row to ApprovalLog object"""
        return ApprovalLog(
            log_id=row[0],
            request_id=row[1],
            reviewer_id=row[2],
            reviewer_role=ReviewerRole(row[3]),
            action=row[4],
            timestamp=datetime.fromisoformat(row[5]),
            notes=row[6],
            metadata=json.loads(row[7]) if row[7] else {}
        )
    
    def _row_to_workflow(self, row) -> ApprovalWorkflow:
        """Convert database row to ApprovalWorkflow object"""
        return ApprovalWorkflow(
            workflow_id=row[0],
            organization_id=row[1],
            approval_type=ApprovalType(row[2]),
            name=row[3],
            description=row[4],
            required_roles=[ReviewerRole(r) for r in json.loads(row[5])],
            min_approvers=row[6],
            auto_approve_after_hours=row[7],
            escalation_after_hours=row[8],
            escalation_roles=[ReviewerRole(r) for r in json.loads(row[9])] if row[9] else [],
            is_active=bool(row[10]),
            created_at=datetime.fromisoformat(row[11]),
            updated_at=datetime.fromisoformat(row[12])
        )
    
    def _row_to_template(self, row) -> ApprovalTemplate:
        """Convert database row to ApprovalTemplate object"""
        return ApprovalTemplate(
            template_id=row[0],
            organization_id=row[1],
            name=row[2],
            description=row[3],
            approval_type=ApprovalType(row[4]),
            workflow_config=json.loads(row[5]),
            is_default=bool(row[6]),
            created_at=datetime.fromisoformat(row[7]),
            updated_at=datetime.fromisoformat(row[8])
        )
