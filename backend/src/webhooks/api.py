"""
Webhooks API endpoints
"""
import logging
import secrets
import string
from flask import Blueprint, request, jsonify, g
from src.webhooks.registry import list_available_events, validate_event_type
from src.webhooks.publisher import WebhookPublisher
from src.tenancy.decorators import require_tenant, tenant_admin
from src.tenancy.context import get_current_tenant_id
from src.auth_api import require_auth
from src.db_core import get_session
from src.integrations.models import Webhook, WebhookDelivery

logger = logging.getLogger(__name__)
bp = Blueprint('webhooks', __name__, url_prefix='/api/webhooks')

webhook_publisher = WebhookPublisher()

@bp.route('', methods=['POST'])
@require_auth
@require_tenant()
@tenant_admin()
def create_webhook():
    """Create a new webhook"""
    try:
        data = request.get_json()
        target_url = data.get('target_url')
        events = data.get('events', [])
        
        if not target_url:
            return jsonify({'error': 'target_url is required'}), 400
        
        if not events:
            return jsonify({'error': 'events list is required'}), 400
        
        # Validate events
        for event in events:
            if not validate_event_type(event):
                return jsonify({'error': f'Invalid event type: {event}'}), 400
        
        tenant_id = get_current_tenant_id()
        
        # Generate secret
        secret = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        
        # Create webhook
        session = get_session()
        webhook = Webhook(
            tenant_id=tenant_id,
            target_url=target_url,
            secret=secret,
            secret_show_once=secret,  # Show once only
            events=events
        )
        
        session.add(webhook)
        session.commit()
        session.refresh(webhook)
        
        logger.info(f"Created webhook {webhook.id} for tenant {tenant_id}")
        
        return jsonify({
            'success': True,
            'webhook': {
                'id': str(webhook.id),
                'target_url': webhook.target_url,
                'events': webhook.events,
                'status': webhook.status,
                'secret': webhook.secret_show_once,  # Show once only
                'created_at': webhook.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('', methods=['GET'])
@require_auth
@require_tenant()
def list_webhooks():
    """List webhooks for current tenant"""
    try:
        tenant_id = get_current_tenant_id()
        
        session = get_session()
        webhooks = session.query(Webhook).filter(
            Webhook.tenant_id == tenant_id
        ).order_by(Webhook.created_at.desc()).all()
        
        result = []
        for webhook in webhooks:
            result.append({
                'id': str(webhook.id),
                'target_url': webhook.target_url,
                'events': webhook.events,
                'status': webhook.status,
                'created_at': webhook.created_at.isoformat(),
                'updated_at': webhook.updated_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'webhooks': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing webhooks: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<webhook_id>/pause', methods=['POST'])
@require_auth
@require_tenant()
@tenant_admin()
def pause_webhook(webhook_id):
    """Pause webhook"""
    try:
        session = get_session()
        
        webhook = session.query(Webhook).filter(
            Webhook.id == webhook_id,
            Webhook.tenant_id == get_current_tenant_id()
        ).first()
        
        if not webhook:
            return jsonify({'error': 'Webhook not found'}), 404
        
        webhook.status = 'paused'
        session.commit()
        
        logger.info(f"Paused webhook {webhook_id}")
        
        return jsonify({
            'success': True,
            'message': 'Webhook paused successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error pausing webhook {webhook_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<webhook_id>', methods=['DELETE'])
@require_auth
@require_tenant()
@tenant_admin()
def delete_webhook(webhook_id):
    """Delete webhook"""
    try:
        session = get_session()
        
        webhook = session.query(Webhook).filter(
            Webhook.id == webhook_id,
            Webhook.tenant_id == get_current_tenant_id()
        ).first()
        
        if not webhook:
            return jsonify({'error': 'Webhook not found'}), 404
        
        session.delete(webhook)
        session.commit()
        
        logger.info(f"Deleted webhook {webhook_id}")
        
        return jsonify({
            'success': True,
            'message': 'Webhook deleted successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting webhook {webhook_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/deliveries', methods=['GET'])
@require_auth
@require_tenant()
def list_deliveries():
    """List webhook deliveries"""
    try:
        tenant_id = get_current_tenant_id()
        event_type = request.args.get('event')
        limit = min(int(request.args.get('limit', 50)), 100)
        
        session = get_session()
        
        # Get webhooks for tenant
        webhook_ids = session.query(Webhook.id).filter(
            Webhook.tenant_id == tenant_id
        ).subquery()
        
        # Query deliveries
        query = session.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_id.in_(webhook_ids)
        )
        
        if event_type:
            query = query.filter(WebhookDelivery.event_type == event_type)
        
        deliveries = query.order_by(WebhookDelivery.created_at.desc()).limit(limit).all()
        
        result = []
        for delivery in deliveries:
            result.append({
                'id': str(delivery.id),
                'webhook_id': str(delivery.webhook_id),
                'event_type': delivery.event_type,
                'status': delivery.status,
                'attempt': delivery.attempt,
                'response_status': delivery.response_status,
                'response_ms': delivery.response_ms,
                'error': delivery.error,
                'created_at': delivery.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'deliveries': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing webhook deliveries: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/deliveries/<delivery_id>/redeliver', methods=['POST'])
@require_auth
@require_tenant()
@tenant_admin()
def redeliver_webhook(delivery_id):
    """Redeliver webhook"""
    try:
        success = webhook_publisher.redeliver(delivery_id)
        
        if not success:
            return jsonify({'error': 'Delivery not found or cannot be redelivered'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Webhook redelivery queued'
        }), 200
        
    except Exception as e:
        logger.error(f"Error redelivering webhook {delivery_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/events', methods=['GET'])
@require_auth
@require_tenant()
def list_events():
    """List available webhook events"""
    try:
        events = list_available_events()
        
        return jsonify({
            'success': True,
            'events': events
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing webhook events: {e}")
        return jsonify({'error': 'Internal server error'}), 500
