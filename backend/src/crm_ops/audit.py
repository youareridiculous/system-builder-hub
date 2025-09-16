"""
Audit logging service for CRM/Ops operations
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from src.crm_ops.models import CRMOpsAuditLog
from src.database import db_session
from src.tenancy.context import get_current_tenant_id

logger = logging.getLogger(__name__)

class CRMOpsAuditService:
    """Audit logging service for CRM/Ops operations"""
    
    @staticmethod
    def log_operation(
        action: str,
        table_name: str,
        record_id: str,
        user_id: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log an audit operation"""
        try:
            tenant_id = get_current_tenant_id()
            if not tenant_id:
                logger.warning("No tenant context for audit logging")
                return
            
            audit_log = CRMOpsAuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                table_name=table_name,
                record_id=record_id,
                old_values=old_values,
                new_values=new_values,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            with db_session() as session:
                session.add(audit_log)
                session.commit()
                
            logger.info(f"Audit log created: {action} on {table_name} {record_id}")
            
        except Exception as e:
            logger.error(f"Error creating audit log: {e}")
    
    @staticmethod
    def log_create(table_name: str, record_id: str, user_id: str, new_values: Dict[str, Any], **kwargs):
        """Log a create operation"""
        CRMOpsAuditService.log_operation(
            action='create',
            table_name=table_name,
            record_id=record_id,
            user_id=user_id,
            new_values=new_values,
            **kwargs
        )
    
    @staticmethod
    def log_update(table_name: str, record_id: str, user_id: str, old_values: Dict[str, Any], new_values: Dict[str, Any], **kwargs):
        """Log an update operation"""
        CRMOpsAuditService.log_operation(
            action='update',
            table_name=table_name,
            record_id=record_id,
            user_id=user_id,
            old_values=old_values,
            new_values=new_values,
            **kwargs
        )
    
    @staticmethod
    def log_delete(table_name: str, record_id: str, user_id: str, old_values: Dict[str, Any], **kwargs):
        """Log a delete operation"""
        CRMOpsAuditService.log_operation(
            action='delete',
            table_name=table_name,
            record_id=record_id,
            user_id=user_id,
            old_values=old_values,
            **kwargs
        )
    
    @staticmethod
    def get_audit_logs(
        tenant_id: str,
        table_name: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """Get audit logs with filtering"""
        try:
            with db_session() as session:
                query = session.query(CRMOpsAuditLog).filter(
                    CRMOpsAuditLog.tenant_id == tenant_id
                )
                
                if table_name:
                    query = query.filter(CRMOpsAuditLog.table_name == table_name)
                
                if user_id:
                    query = query.filter(CRMOpsAuditLog.user_id == user_id)
                
                if action:
                    query = query.filter(CRMOpsAuditLog.action == action)
                
                logs = query.order_by(CRMOpsAuditLog.created_at.desc()).offset(offset).limit(limit).all()
                
                return [
                    {
                        'id': str(log.id),
                        'action': log.action,
                        'table_name': log.table_name,
                        'record_id': str(log.record_id),
                        'user_id': log.user_id,
                        'old_values': log.old_values,
                        'new_values': log.new_values,
                        'ip_address': log.ip_address,
                        'user_agent': log.user_agent,
                        'created_at': log.created_at.isoformat()
                    }
                    for log in logs
                ]
                
        except Exception as e:
            logger.error(f"Error getting audit logs: {e}")
            return []
