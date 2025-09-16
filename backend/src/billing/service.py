"""
Billing Service - Provider-agnostic billing management
Supports trials, subscriptions, and customer lifecycle
"""

import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from src.db_core import get_database_url

logger = logging.getLogger(__name__)

class BillingService:
    """Provider-agnostic billing service with mock implementation"""
    
    def __init__(self):
        logger.info("Initializing BillingService...")
        self.database_url = get_database_url()
        logger.info(f"Billing service using database: {self.database_url}")
        # Use the same engine configuration as the rest of the app
        from src.db_core import get_engine
        self.engine = get_engine()
        logger.info(f"Billing service engine URL: {self.engine.url}")
        logger.info("BillingService initialized successfully")
    
    def create_customer(self, tenant_id: str) -> Dict[str, Any]:
        """Create a customer record for a tenant"""
        try:
            customer_id = str(uuid.uuid4())
            with self.engine.connect() as conn:
                # For now, we just log the customer creation
                # In a real implementation, this would create a customer in the billing provider
                logger.info(f"Created customer {customer_id} for tenant {tenant_id}")
                
                return {
                    'customer_id': customer_id,
                    'tenant_id': tenant_id,
                    'status': 'created'
                }
        except Exception as e:
            logger.error(f"Failed to create customer for tenant {tenant_id}: {e}")
            raise
    
    def start_trial(self, tenant_id: str, module: str, plan: str, days: int = 14) -> Dict[str, Any]:
        """Start a trial for a tenant/module combination"""
        try:
            subscription_id = str(uuid.uuid4())
            trial_ends_at = datetime.utcnow() + timedelta(days=days)
            
            with self.engine.begin() as conn:
                # Check if subscription already exists
                result = conn.execute(
                    text("SELECT id, status FROM billing_subscriptions WHERE tenant_id = :tenant_id AND module = :module"),
                    {'tenant_id': tenant_id, 'module': module}
                )
                existing = result.fetchone()
                
                if existing:
                    if existing.status == 'trial':
                        return {
                            'subscription_id': existing.id,
                            'status': 'already_on_trial',
                            'trial_ends_at': existing.trial_ends_at.isoformat() if existing.trial_ends_at else None
                        }
                    else:
                        return {
                            'subscription_id': existing.id,
                            'status': 'subscription_exists',
                            'current_status': existing.status
                        }
                
                # Create new trial subscription
                conn.execute(
                    text("""
                        INSERT INTO billing_subscriptions 
                        (id, tenant_id, module, plan, status, trial_ends_at, created_at, updated_at, metadata)
                        VALUES (:id, :tenant_id, :module, :plan, :status, :trial_ends_at, :created_at, :updated_at, :metadata)
                    """),
                    {
                        'id': subscription_id,
                        'tenant_id': tenant_id,
                        'module': module,
                        'plan': plan,
                        'status': 'trial',
                        'trial_ends_at': trial_ends_at,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow(),
                        'metadata': json.dumps({'trial_days': days})
                    }
                )
                
                # Log event in a separate transaction to avoid rollback
                try:
                    self._log_event(tenant_id, module, 'trial_started', {
                        'plan': plan,
                        'trial_days': days,
                        'trial_ends_at': trial_ends_at.isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Failed to log event: {e}")
                
                return {
                    'subscription_id': subscription_id,
                    'status': 'started_trial',
                    'trial_ends_at': trial_ends_at.isoformat()
                }
                
        except IntegrityError:
            # Handle race condition
            return self.start_trial(tenant_id, module, plan, days)
        except Exception as e:
            logger.error(f"Failed to start trial for tenant {tenant_id}, module {module}: {e}")
            raise
    
    def subscribe(self, tenant_id: str, module: str, plan: str) -> Dict[str, Any]:
        """Subscribe a tenant to a module plan"""
        try:
            with self.engine.begin() as conn:
                # Check if subscription exists
                result = conn.execute(
                    text("SELECT id, status FROM billing_subscriptions WHERE tenant_id = :tenant_id AND module = :module"),
                    {'tenant_id': tenant_id, 'module': module}
                )
                existing = result.fetchone()
                
                if existing:
                    if existing.status == 'active':
                        return {
                            'subscription_id': existing.id,
                            'status': 'already_subscribed'
                        }
                    else:
                        # Update existing subscription to active
                        conn.execute(
                            text("""
                                UPDATE billing_subscriptions 
                                SET plan = :plan, status = :status, updated_at = :updated_at
                                WHERE id = :id
                            """),
                            {
                                'plan': plan,
                                'status': 'active',
                                'updated_at': datetime.utcnow(),
                                'id': existing.id
                            }
                        )
                        
                        # Log event in a separate transaction to avoid rollback
                        try:
                            self._log_event(tenant_id, module, 'subscribed', {
                                'plan': plan,
                                'previous_status': existing.status
                            })
                        except Exception as e:
                            logger.warning(f"Failed to log event: {e}")
                        
                        return {
                            'subscription_id': existing.id,
                            'status': 'subscribed'
                        }
                else:
                    # Create new active subscription
                    subscription_id = str(uuid.uuid4())
                    conn.execute(
                        text("""
                            INSERT INTO billing_subscriptions 
                            (id, tenant_id, module, plan, status, created_at, updated_at, metadata)
                            VALUES (:id, :tenant_id, :module, :plan, :status, :created_at, :updated_at, :metadata)
                        """),
                        {
                            'id': subscription_id,
                            'tenant_id': tenant_id,
                            'module': module,
                            'plan': plan,
                            'status': 'active',
                            'created_at': datetime.utcnow(),
                            'updated_at': datetime.utcnow(),
                            'metadata': json.dumps({})
                        }
                    )
                    
                    # Log event in a separate transaction to avoid rollback
                    try:
                        self._log_event(tenant_id, module, 'subscribed', {
                            'plan': plan
                        })
                    except Exception as e:
                        logger.warning(f"Failed to log event: {e}")
                    
                    return {
                        'subscription_id': subscription_id,
                        'status': 'subscribed'
                    }
                    
        except IntegrityError:
            # Handle race condition
            return self.subscribe(tenant_id, module, plan)
        except Exception as e:
            logger.error(f"Failed to subscribe tenant {tenant_id} to module {module}: {e}")
            raise
    
    def cancel(self, tenant_id: str, module: str) -> Dict[str, Any]:
        """Cancel a subscription"""
        try:
            with self.engine.begin() as conn:
                result = conn.execute(
                    text("SELECT id, status FROM billing_subscriptions WHERE tenant_id = :tenant_id AND module = :module"),
                    {'tenant_id': tenant_id, 'module': module}
                )
                subscription = result.fetchone()
                
                if not subscription:
                    return {
                        'status': 'not_subscribed'
                    }
                
                if subscription.status == 'canceled':
                    return {
                        'subscription_id': subscription.id,
                        'status': 'already_canceled'
                    }
                
                # Cancel the subscription
                conn.execute(
                    text("""
                        UPDATE billing_subscriptions 
                        SET status = :status, updated_at = :updated_at
                        WHERE id = :id
                    """),
                    {
                        'status': 'canceled',
                        'updated_at': datetime.utcnow(),
                        'id': subscription.id
                    }
                )
                
                # Log event in a separate transaction to avoid rollback
                try:
                    self._log_event(tenant_id, module, 'canceled', {
                        'previous_status': subscription.status
                    })
                except Exception as e:
                    logger.warning(f"Failed to log event: {e}")
                
                return {
                    'subscription_id': subscription.id,
                    'status': 'canceled'
                }
                
        except Exception as e:
            logger.error(f"Failed to cancel subscription for tenant {tenant_id}, module {module}: {e}")
            raise
    
    def status(self, tenant_id: str, module: str) -> Dict[str, Any]:
        """Get subscription status for a tenant/module"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT id, plan, status, trial_ends_at, created_at, updated_at, metadata
                        FROM billing_subscriptions 
                        WHERE tenant_id = :tenant_id AND module = :module
                    """),
                    {'tenant_id': tenant_id, 'module': module}
                )
                subscription = result.fetchone()
                
                if not subscription:
                    return {
                        'status': 'not_subscribed'
                    }
                
                # Check if trial has expired
                if subscription.status == 'trial' and subscription.trial_ends_at:
                    # Convert string to datetime if needed
                    trial_ends_at = subscription.trial_ends_at
                    if isinstance(trial_ends_at, str):
                        from datetime import datetime
                        trial_ends_at = datetime.fromisoformat(trial_ends_at.replace('Z', '+00:00'))
                    
                    if datetime.utcnow() > trial_ends_at:
                        # Update status to expired
                        conn.execute(
                            text("""
                                UPDATE billing_subscriptions 
                                SET status = :status, updated_at = :updated_at
                                WHERE id = :id
                            """),
                            {
                                'status': 'expired',
                                'updated_at': datetime.utcnow(),
                                'id': subscription.id
                            }
                        )
                        
                        # Log event
                        self._log_event(tenant_id, module, 'trial_expired', {})
                        
                        return {
                            'subscription_id': subscription.id,
                            'status': 'expired',
                            'plan': subscription.plan,
                            'trial_ends_at': subscription.trial_ends_at,
                            'created_at': subscription.created_at,
                            'updated_at': subscription.updated_at
                        }
                
                return {
                    'subscription_id': subscription.id,
                    'status': subscription.status,
                    'plan': subscription.plan,
                    'trial_ends_at': subscription.trial_ends_at,
                    'created_at': subscription.created_at,
                    'updated_at': subscription.updated_at,
                    'metadata': json.loads(subscription.metadata) if subscription.metadata else {}
                }
                
        except Exception as e:
            logger.error(f"Failed to get status for tenant {tenant_id}, module {module}: {e}")
            raise
    
    def _log_event(self, tenant_id: str, module: str, event_type: str, metadata: Dict[str, Any]):
        """Log an event to the sbh_events table"""
        try:
            event_id = str(uuid.uuid4())
            with self.engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO sbh_events 
                        (id, tenant_id, module, event_type, metadata, created_at)
                        VALUES (:id, :tenant_id, :module, :event_type, :metadata, :created_at)
                    """),
                    {
                        'id': event_id,
                        'tenant_id': tenant_id,
                        'module': module,
                        'event_type': event_type,
                        'metadata': json.dumps(metadata),
                        'created_at': datetime.utcnow()
                    }
                )
        except Exception as e:
            logger.error(f"Failed to log event {event_type} for tenant {tenant_id}: {e}")

# Global billing service instance
logger.info("Creating global billing service instance...")
billing_service = BillingService()
logger.info("Global billing service instance created successfully")
