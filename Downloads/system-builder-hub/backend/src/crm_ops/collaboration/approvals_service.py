"""
Approvals service for CRM/Ops Template
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from src.database import db_session
from src.crm_ops.collaboration.models import Approval
from src.crm_ops.collaboration.notifications_service import NotificationsService

logger = logging.getLogger(__name__)

class ApprovalsService:
    """Service for approval workflow operations"""
    
    def __init__(self):
        self.notifications_service = NotificationsService()
    
    def request_approval(self, tenant_id: str, entity_type: str, entity_id: str, action_type: str, requested_by: str, approver_id: str, metadata: Dict[str, Any] = None) -> Approval:
        """Request approval for an action"""
        with db_session() as session:
            approval = Approval(
                tenant_id=tenant_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action_type=action_type,
                requested_by=requested_by,
                approver_id=approver_id,
                status='pending',
                metadata=metadata or {}
            )
            
            session.add(approval)
            session.commit()
            
            # Send notification to approver
            self.notifications_service.create_notification(
                session=session,
                tenant_id=tenant_id,
                user_id=approver_id,
                type='approval_request',
                title='Approval Required',
                message=f'Approval required for {action_type} on {entity_type}',
                data={
                    'approval_id': str(approval.id),
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'action_type': action_type,
                    'requested_by': requested_by
                }
            )
            
            return approval
    
    def get_pending_approvals(self, tenant_id: str, user_id: str) -> List[Approval]:
        """Get pending approvals for a user"""
        with db_session() as session:
            approvals = session.query(Approval).filter(
                Approval.tenant_id == tenant_id,
                Approval.approver_id == user_id,
                Approval.status == 'pending'
            ).order_by(Approval.created_at.desc()).all()
            
            return approvals
    
    def get_approval(self, approval_id: str, tenant_id: str, user_id: str) -> Optional[Approval]:
        """Get a specific approval"""
        with db_session() as session:
            approval = session.query(Approval).filter(
                Approval.id == approval_id,
                Approval.tenant_id == tenant_id,
                and_(
                    or_(
                        Approval.approver_id == user_id,
                        Approval.requested_by == user_id
                    )
                )
            ).first()
            
            return approval
    
    def approve(self, approval_id: str, tenant_id: str, approver_id: str, reason: str = None) -> bool:
        """Approve an action"""
        with db_session() as session:
            approval = session.query(Approval).filter(
                Approval.id == approval_id,
                Approval.tenant_id == tenant_id,
                Approval.approver_id == approver_id,
                Approval.status == 'pending'
            ).first()
            
            if not approval:
                return False
            
            approval.status = 'approved'
            approval.reason = reason
            approval.resolved_at = datetime.utcnow()
            
            session.commit()
            
            # Send notification to requester
            self.notifications_service.create_notification(
                session=session,
                tenant_id=tenant_id,
                user_id=approval.requested_by,
                type='approval_approved',
                title='Approval Granted',
                message=f'Your {approval.action_type} request for {approval.entity_type} has been approved',
                data={
                    'approval_id': str(approval.id),
                    'entity_type': approval.entity_type,
                    'entity_id': approval.entity_id,
                    'action_type': approval.action_type,
                    'approved_by': approver_id,
                    'reason': reason
                }
            )
            
            return True
    
    def reject(self, approval_id: str, tenant_id: str, approver_id: str, reason: str) -> bool:
        """Reject an action"""
        with db_session() as session:
            approval = session.query(Approval).filter(
                Approval.id == approval_id,
                Approval.tenant_id == tenant_id,
                Approval.approver_id == approver_id,
                Approval.status == 'pending'
            ).first()
            
            if not approval:
                return False
            
            approval.status = 'rejected'
            approval.reason = reason
            approval.resolved_at = datetime.utcnow()
            
            session.commit()
            
            # Send notification to requester
            self.notifications_service.create_notification(
                session=session,
                tenant_id=tenant_id,
                user_id=approval.requested_by,
                type='approval_rejected',
                title='Approval Denied',
                message=f'Your {approval.action_type} request for {approval.entity_type} has been rejected',
                data={
                    'approval_id': str(approval.id),
                    'entity_type': approval.entity_type,
                    'entity_id': approval.entity_id,
                    'action_type': approval.action_type,
                    'rejected_by': approver_id,
                    'reason': reason
                }
            )
            
            return True
    
    def get_approval_history(self, tenant_id: str, entity_type: str = None, entity_id: str = None, user_id: str = None) -> List[Approval]:
        """Get approval history"""
        with db_session() as session:
            query = session.query(Approval).filter(Approval.tenant_id == tenant_id)
            
            if entity_type:
                query = query.filter(Approval.entity_type == entity_type)
            
            if entity_id:
                query = query.filter(Approval.entity_id == entity_id)
            
            if user_id:
                query = query.filter(
                    or_(
                        Approval.requested_by == user_id,
                        Approval.approver_id == user_id
                    )
                )
            
            approvals = query.order_by(Approval.created_at.desc()).all()
            
            return approvals
    
    def check_approval_required(self, tenant_id: str, entity_type: str, action_type: str, metadata: Dict[str, Any] = None) -> bool:
        """Check if approval is required for an action"""
        # This would check tenant-specific approval rules
        # For now, implement basic rules
        
        if entity_type == 'deal' and action_type in ['create', 'update']:
            # Check if deal value requires approval
            if metadata and metadata.get('value', 0) > 50000:
                return True
        
        if entity_type == 'task' and action_type == 'delete':
            # Check if task is high priority
            if metadata and metadata.get('priority') == 'high':
                return True
        
        return False
    
    def get_approval_rules(self, tenant_id: str) -> Dict[str, Any]:
        """Get approval rules for a tenant"""
        # This would load from tenant configuration
        # For now, return default rules
        
        return {
            'deal': {
                'create': {'min_value': 50000},
                'update': {'min_value': 50000},
                'delete': {'always': True}
            },
            'task': {
                'delete': {'priority': 'high'}
            },
            'project': {
                'delete': {'always': True}
            }
        }
