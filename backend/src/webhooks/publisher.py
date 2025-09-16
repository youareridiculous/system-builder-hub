"""
Webhook event publisher
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from src.db_core import get_session
from src.integrations.models import Webhook, WebhookDelivery
from src.webhooks.registry import validate_event_type

logger = logging.getLogger(__name__)

class WebhookPublisher:
    """Webhook event publisher"""
    
    def __init__(self):
        self.max_retries = 6
        self.retry_delays = [60, 300, 900, 3600, 7200, 14400]  # 1m, 5m, 15m, 1h, 2h, 4h
    
    def enqueue_event(self, tenant_id: str, event_type: str, payload: Dict[str, Any]) -> List[str]:
        """Enqueue webhook event for delivery"""
        try:
            # Validate event type
            if not validate_event_type(event_type):
                logger.warning(f"Invalid event type: {event_type}")
                return []
            
            session = get_session()
            
            # Find active webhooks for this tenant and event
            webhooks = session.query(Webhook).filter(
                Webhook.tenant_id == tenant_id,
                Webhook.status == 'active',
                Webhook.events.contains([event_type])
            ).all()
            
            delivery_ids = []
            
            for webhook in webhooks:
                # Create delivery record
                delivery = WebhookDelivery(
                    webhook_id=webhook.id,
                    event_type=event_type,
                    payload=payload,
                    status='queued'
                )
                
                session.add(delivery)
                session.flush()  # Get the ID
                
                delivery_ids.append(str(delivery.id))
                
                logger.info(f"Queued webhook delivery {delivery.id} for event {event_type} to {webhook.target_url}")
            
            session.commit()
            
            # Enqueue background job for delivery
            try:
                from src.jobs.tasks import deliver_webhook_job
                for delivery_id in delivery_ids:
                    deliver_webhook_job.delay(delivery_id)
            except ImportError:
                logger.warning("Background jobs not available, webhook delivery will be manual")
            
            return delivery_ids
            
        except Exception as e:
            logger.error(f"Error enqueueing webhook event {event_type}: {e}")
            return []
    
    def get_delivery_status(self, delivery_id: str) -> Dict[str, Any]:
        """Get delivery status"""
        try:
            session = get_session()
            
            delivery = session.query(WebhookDelivery).filter(
                WebhookDelivery.id == delivery_id
            ).first()
            
            if not delivery:
                return {}
            
            return {
                'id': str(delivery.id),
                'webhook_id': str(delivery.webhook_id),
                'event_type': delivery.event_type,
                'status': delivery.status,
                'attempt': delivery.attempt,
                'response_status': delivery.response_status,
                'response_ms': delivery.response_ms,
                'error': delivery.error,
                'created_at': delivery.created_at.isoformat(),
                'updated_at': delivery.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting delivery status {delivery_id}: {e}")
            return {}
    
    def redeliver(self, delivery_id: str) -> bool:
        """Redeliver a failed webhook"""
        try:
            session = get_session()
            
            delivery = session.query(WebhookDelivery).filter(
                WebhookDelivery.id == delivery_id
            ).first()
            
            if not delivery:
                return False
            
            # Reset delivery for retry
            delivery.status = 'queued'
            delivery.attempt = 1
            delivery.error = None
            delivery.response_status = None
            delivery.response_ms = None
            session.commit()
            
            # Enqueue for delivery
            try:
                from src.jobs.tasks import deliver_webhook_job
                deliver_webhook_job.delay(delivery_id)
            except ImportError:
                logger.warning("Background jobs not available, manual redelivery required")
            
            logger.info(f"Redelivery queued for webhook delivery {delivery_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error redelivering webhook {delivery_id}: {e}")
            return False
