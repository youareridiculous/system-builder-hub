"""
Tenant Lifecycle Management
Handles tenant creation, provisioning, and subscription lifecycle
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, text

from src.db_core import get_database_url
from src.billing.service import billing_service

logger = logging.getLogger(__name__)

class TenantLifecycle:
    """Manages tenant lifecycle and provisioning"""
    
    def __init__(self):
        self.database_url = get_database_url()
        self.engine = create_engine(self.database_url)
    
    def ensure_tenant(self, tenant_id: str, tenant_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ensure a tenant exists, create if needed"""
        try:
            with self.engine.connect() as conn:
                # Check if tenant exists
                result = conn.execute(
                    text("SELECT id, name, domain FROM tenants WHERE id = :tenant_id"),
                    {'tenant_id': tenant_id}
                )
                tenant = result.fetchone()
                
                if tenant:
                    return {
                        'tenant_id': tenant.id,
                        'name': tenant.name,
                        'domain': tenant.domain,
                        'status': 'exists'
                    }
                
                # Create new tenant
                tenant_name = tenant_data.get('name', f'Tenant {tenant_id}') if tenant_data else f'Tenant {tenant_id}'
                tenant_domain = tenant_data.get('domain') if tenant_data else None
                
                conn.execute(
                    text("""
                        INSERT INTO tenants (id, name, domain, created_at, updated_at)
                        VALUES (:id, :name, :domain, :created_at, :updated_at)
                    """),
                    {
                        'id': tenant_id,
                        'name': tenant_name,
                        'domain': tenant_domain,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                )
                
                logger.info(f"Created tenant {tenant_id} with name {tenant_name}")
                
                return {
                    'tenant_id': tenant_id,
                    'name': tenant_name,
                    'domain': tenant_domain,
                    'status': 'created'
                }
                
        except Exception as e:
            logger.error(f"Failed to ensure tenant {tenant_id}: {e}")
            raise
    
    def ensure_customer_record(self, tenant_id: str) -> Dict[str, Any]:
        """Ensure a customer record exists for billing"""
        try:
            # Use the billing service to create customer
            return billing_service.create_customer(tenant_id)
        except Exception as e:
            logger.error(f"Failed to ensure customer record for tenant {tenant_id}: {e}")
            raise
    
    def record_provision(self, module: str, tenant_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Record that a module was provisioned for a tenant"""
        try:
            # Ensure tenant exists
            tenant_info = self.ensure_tenant(tenant_id)
            
            # Log provisioning event
            billing_service._log_event(tenant_id, module, 'module_provisioned', {
                'tenant_status': tenant_info['status'],
                'metadata': metadata or {}
            })
            
            logger.info(f"Recorded provision of {module} for tenant {tenant_id}")
            
            return {
                'tenant_id': tenant_id,
                'module': module,
                'tenant_status': tenant_info['status'],
                'status': 'provisioned'
            }
            
        except Exception as e:
            logger.error(f"Failed to record provision for tenant {tenant_id}, module {module}: {e}")
            raise
    
    def record_subscription(self, tenant_id: str, module: str, plan: str, status: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Record subscription state for a tenant/module"""
        try:
            # Ensure tenant exists
            tenant_info = self.ensure_tenant(tenant_id)
            
            # Log subscription event
            billing_service._log_event(tenant_id, module, 'subscription_recorded', {
                'plan': plan,
                'status': status,
                'tenant_status': tenant_info['status'],
                'metadata': metadata or {}
            })
            
            logger.info(f"Recorded subscription {status} for tenant {tenant_id}, module {module}, plan {plan}")
            
            return {
                'tenant_id': tenant_id,
                'module': module,
                'plan': plan,
                'status': status,
                'tenant_status': tenant_info['status']
            }
            
        except Exception as e:
            logger.error(f"Failed to record subscription for tenant {tenant_id}, module {module}: {e}")
            raise
    
    def get_tenant_modules(self, tenant_id: str) -> Dict[str, Any]:
        """Get all modules and their status for a tenant"""
        try:
            with self.engine.connect() as conn:
                # Get all subscriptions for the tenant
                result = conn.execute(
                    text("""
                        SELECT module, plan, status, trial_ends_at, created_at, updated_at
                        FROM billing_subscriptions 
                        WHERE tenant_id = :tenant_id
                        ORDER BY created_at DESC
                    """),
                    {'tenant_id': tenant_id}
                )
                subscriptions = result.fetchall()
                
                modules = {}
                for sub in subscriptions:
                    modules[sub.module] = {
                        'plan': sub.plan,
                        'status': sub.status,
                        'trial_ends_at': sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
                        'created_at': sub.created_at.isoformat(),
                        'updated_at': sub.updated_at.isoformat()
                    }
                
                return {
                    'tenant_id': tenant_id,
                    'modules': modules,
                    'module_count': len(modules)
                }
                
        except Exception as e:
            logger.error(f"Failed to get modules for tenant {tenant_id}: {e}")
            raise
    
    def get_tenant_events(self, tenant_id: str, limit: int = 50) -> Dict[str, Any]:
        """Get recent events for a tenant"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT module, event_type, metadata, created_at
                        FROM sbh_events 
                        WHERE tenant_id = :tenant_id
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {'tenant_id': tenant_id, 'limit': limit}
                )
                events = result.fetchall()
                
                return {
                    'tenant_id': tenant_id,
                    'events': [
                        {
                            'module': event.module,
                            'event_type': event.event_type,
                            'metadata': event.metadata,
                            'created_at': event.created_at.isoformat()
                        }
                        for event in events
                    ],
                    'event_count': len(events)
                }
                
        except Exception as e:
            logger.error(f"Failed to get events for tenant {tenant_id}: {e}")
            raise

# Global tenant lifecycle instance
tenant_lifecycle = TenantLifecycle()
