"""
Webhook delivery worker
"""
import json
import logging
import os
import time
import hmac
import hashlib
import requests
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from src.db_core import get_session
from src.integrations.models import WebhookDelivery, Webhook
from src.webhooks.verify import verify_signature

logger = logging.getLogger(__name__)

class WebhookWorker:
    """Webhook delivery worker"""
    
    def __init__(self):
        self.timeout = int(os.environ.get('WEBHOOK_TIMEOUT_MS', 5000)) / 1000
        self.max_retries = int(os.environ.get('WEBHOOK_MAX_RETRIES', 6))
        self.retry_delays = [60, 300, 900, 3600, 7200, 14400]  # 1m, 5m, 15m, 1h, 2h, 4h
    
    def deliver(self, delivery_id: str) -> bool:
        """Deliver webhook"""
        try:
            session = get_session()
            
            # Get delivery record
            delivery = session.query(WebhookDelivery).filter(
                WebhookDelivery.id == delivery_id
            ).first()
            
            if not delivery:
                logger.error(f"Webhook delivery {delivery_id} not found")
                return False
            
            # Get webhook
            webhook = session.query(Webhook).filter(
                Webhook.id == delivery.webhook_id
            ).first()
            
            if not webhook:
                logger.error(f"Webhook {delivery.webhook_id} not found")
                return False
            
            # Check if webhook is still active
            if webhook.status != 'active':
                logger.info(f"Webhook {webhook.id} is not active, skipping delivery")
                delivery.status = 'failed'
                delivery.error = 'Webhook is not active'
                session.commit()
                return False
            
            # Prepare payload
            payload = {
                'event_type': delivery.event_type,
                'data': delivery.payload,
                'timestamp': int(time.time() * 1000),
                'delivery_id': str(delivery.id)
            }
            
            # Create signature
            timestamp = str(payload['timestamp'])
            body = json.dumps(payload, separators=(',', ':'))
            signature = self._create_signature(webhook.secret, timestamp, body)
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'X-SBH-Event': delivery.event_type,
                'X-SBH-Timestamp': timestamp,
                'X-SBH-Signature': f'sha256={signature}',
                'X-SBH-Delivery-Id': str(delivery.id),
                'User-Agent': 'SBH-Webhooks/1.0'
            }
            
            # Add tenant info if available
            try:
                from src.tenancy.context import get_current_tenant_slug
                tenant_slug = get_current_tenant_slug()
                if tenant_slug:
                    headers['X-SBH-Tenant'] = tenant_slug
            except ImportError:
                pass
            
            # Make HTTP request
            start_time = time.time()
            
            try:
                response = requests.post(
                    webhook.target_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                
                response_time = int((time.time() - start_time) * 1000)
                
                # Check response
                if 200 <= response.status_code < 300:
                    delivery.status = 'success'
                    delivery.response_status = response.status_code
                    delivery.response_ms = response_time
                    logger.info(f"Webhook delivery {delivery_id} successful: {response.status_code}")
                else:
                    delivery.status = 'failed'
                    delivery.response_status = response.status_code
                    delivery.response_ms = response_time
                    delivery.error = f"HTTP {response.status_code}: {response.text[:500]}"
                    logger.warning(f"Webhook delivery {delivery_id} failed: {response.status_code}")
                
            except requests.exceptions.Timeout:
                delivery.status = 'failed'
                delivery.error = 'Request timeout'
                logger.warning(f"Webhook delivery {delivery_id} timeout")
                
            except requests.exceptions.RequestException as e:
                delivery.status = 'failed'
                delivery.error = str(e)
                logger.warning(f"Webhook delivery {delivery_id} request error: {e}")
            
            # Handle retries
            if delivery.status == 'failed' and delivery.attempt < self.max_retries:
                delivery.status = 'retrying'
                delivery.attempt += 1
                
                # Schedule retry
                try:
                    from src.jobs.tasks import deliver_webhook_job
                    delay = self.retry_delays[min(delivery.attempt - 1, len(self.retry_delays) - 1)]
                    deliver_webhook_job.apply_async(args=[delivery_id], countdown=delay)
                    logger.info(f"Webhook delivery {delivery_id} scheduled for retry in {delay}s")
                except ImportError:
                    logger.warning("Background jobs not available, manual retry required")
            
            session.commit()
            return delivery.status == 'success'
            
        except Exception as e:
            logger.error(f"Error delivering webhook {delivery_id}: {e}")
            return False
    
    def _create_signature(self, secret: str, timestamp: str, body: str) -> str:
        """Create HMAC signature"""
        message = f"{timestamp}.{body}"
        signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
