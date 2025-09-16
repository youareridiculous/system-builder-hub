"""
Webhook event registry
"""
from typing import Dict, Any

# Standard webhook events
WEBHOOK_EVENTS = {
    'build.started': {
        'description': 'Build process started',
        'payload_schema': {
            'project_id': 'string',
            'build_id': 'string',
            'tenant_id': 'string',
            'started_at': 'datetime'
        }
    },
    'build.completed': {
        'description': 'Build process completed',
        'payload_schema': {
            'project_id': 'string',
            'build_id': 'string',
            'tenant_id': 'string',
            'status': 'string',  # success, failed
            'completed_at': 'datetime',
            'pages_count': 'integer',
            'apis_count': 'integer',
            'tables_count': 'integer'
        }
    },
    'auth.user.created': {
        'description': 'New user created',
        'payload_schema': {
            'user_id': 'string',
            'tenant_id': 'string',
            'email': 'string',
            'created_at': 'datetime'
        }
    },
    'payments.subscription.updated': {
        'description': 'Subscription status changed',
        'payload_schema': {
            'tenant_id': 'string',
            'subscription_id': 'string',
            'status': 'string',  # active, canceled, past_due
            'plan': 'string',
            'updated_at': 'datetime'
        }
    },
    'files.uploaded': {
        'description': 'File uploaded',
        'payload_schema': {
            'tenant_id': 'string',
            'file_id': 'string',
            'filename': 'string',
            'size': 'integer',
            'uploaded_at': 'datetime'
        }
    },
    'domain.created': {
        'description': 'Custom domain created',
        'payload_schema': {
            'tenant_id': 'string',
            'domain_id': 'string',
            'hostname': 'string',
            'status': 'string',
            'created_at': 'datetime'
        }
    },
    'domain.activated': {
        'description': 'Custom domain activated',
        'payload_schema': {
            'tenant_id': 'string',
            'domain_id': 'string',
            'hostname': 'string',
            'activated_at': 'datetime'
        }
    }
}

def get_event_schema(event_type: str) -> Dict[str, Any]:
    """Get event schema by type"""
    return WEBHOOK_EVENTS.get(event_type, {})

def list_available_events() -> Dict[str, str]:
    """List all available webhook events"""
    return {event: details['description'] for event, details in WEBHOOK_EVENTS.items()}

def validate_event_type(event_type: str) -> bool:
    """Validate if event type is supported"""
    return event_type in WEBHOOK_EVENTS

def get_event_payload_schema(event_type: str) -> Dict[str, str]:
    """Get payload schema for event type"""
    event = WEBHOOK_EVENTS.get(event_type, {})
    return event.get('payload_schema', {})
