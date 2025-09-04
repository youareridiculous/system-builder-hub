"""
Webhooks-as-Code system
"""
import yaml
import json
import logging
import hashlib
import hmac
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.ext.models import PluginWebhook
from src.ext.sandbox import plugin_sandbox

logger = logging.getLogger(__name__)

class WebhookManager:
    """Webhook manager for plugins"""
    
    def __init__(self):
        self.webhook_specs = {}
    
    def load_webhook_spec(self, plugin_slug: str, spec_path: str) -> Dict[str, Any]:
        """Load webhook specification from YAML"""
        try:
            with open(spec_path, 'r') as f:
                spec = yaml.safe_load(f)
            
            # Validate spec
            self._validate_webhook_spec(spec)
            
            # Store spec
            self.webhook_specs[plugin_slug] = spec
            
            return spec
            
        except Exception as e:
            logger.error(f"Error loading webhook spec {spec_path}: {e}")
            raise
    
    def _validate_webhook_spec(self, spec: Dict[str, Any]):
        """Validate webhook specification"""
        required_fields = ['api_version', 'on', 'delivery']
        for field in required_fields:
            if field not in spec:
                raise ValueError(f"Required field '{field}' missing from webhook spec")
        
        # Validate API version
        if spec['api_version'] != 'v1':
            raise ValueError("Unsupported API version")
        
        # Validate event types
        if not isinstance(spec['on'], list) or not spec['on']:
            raise ValueError("'on' field must be a non-empty list")
        
        # Validate delivery
        delivery = spec['delivery']
        if 'url' not in delivery:
            raise ValueError("Delivery URL is required")
    
    def deliver_webhook(self, plugin_slug: str, event_type: str, event_data: Dict[str, Any], 
                       tenant_id: str) -> Dict[str, Any]:
        """Deliver webhook for an event"""
        try:
            if plugin_slug not in self.webhook_specs:
                return {'success': False, 'error': 'Webhook spec not found'}
            
            spec = self.webhook_specs[plugin_slug]
            
            # Check if webhook is subscribed to this event
            if event_type not in spec['on']:
                return {'success': False, 'error': 'Event not subscribed'}
            
            # Get delivery configuration
            delivery = spec['delivery']
            url = delivery['url']
            headers = delivery.get('headers', {})
            
            # Apply transform if specified
            if 'transform' in spec:
                event_data = self._apply_transform(spec['transform'], event_data, tenant_id)
            
            # Add signature if configured
            if 'signing' in delivery:
                signature = self._generate_signature(event_data, delivery['signing'])
                headers['X-Signature'] = signature
            
            # Make HTTP request
            from src.ext.http_client import HTTPClient
            http_client = HTTPClient(tenant_id)
            
            response = http_client.post(url, json=event_data, headers=headers)
            
            # Handle retries if needed
            if not response.get('success', False) and 'retry' in spec:
                self._schedule_retry(plugin_slug, event_type, event_data, tenant_id, spec)
            
            return response
            
        except Exception as e:
            logger.error(f"Error delivering webhook for {plugin_slug}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _apply_transform(self, transform_spec: Dict[str, Any], event_data: Dict[str, Any], 
                        tenant_id: str) -> Dict[str, Any]:
        """Apply transform to event data"""
        try:
            language = transform_spec.get('language', 'python')
            entry = transform_spec.get('entry')
            
            if language == 'python' and entry:
                # Load transform function
                module_name, function_name = entry.split('#')
                
                # In a real implementation, this would load the actual module
                # For now, return the original data
                return event_data
            
            return event_data
            
        except Exception as e:
            logger.error(f"Error applying transform: {e}")
            return event_data
    
    def _generate_signature(self, data: Dict[str, Any], signing_config: Dict[str, str]) -> str:
        """Generate webhook signature"""
        try:
            algorithm = signing_config.get('alg', 'HMAC-SHA256')
            secret_key = signing_config.get('secret', '')
            
            # Convert data to JSON string
            data_str = json.dumps(data, sort_keys=True)
            
            if algorithm == 'HMAC-SHA256':
                signature = hmac.new(
                    secret_key.encode('utf-8'),
                    data_str.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                
                return f"sha256={signature}"
            
            return ''
            
        except Exception as e:
            logger.error(f"Error generating signature: {e}")
            return ''
    
    def _schedule_retry(self, plugin_slug: str, event_type: str, event_data: Dict[str, Any],
                       tenant_id: str, spec: Dict[str, Any]):
        """Schedule webhook retry"""
        try:
            retry_config = spec.get('retry', {})
            max_attempts = retry_config.get('max_attempts', 3)
            backoff = retry_config.get('backoff', 'exponential')
            
            # In a real implementation, this would schedule a retry job
            # For now, just log the retry
            logger.info(f"Scheduling retry for webhook {plugin_slug} event {event_type}")
            
        except Exception as e:
            logger.error(f"Error scheduling retry: {e}")

# Global webhook manager
webhook_manager = WebhookManager()
