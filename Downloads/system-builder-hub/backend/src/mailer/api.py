"""
Email API endpoints
"""
import logging
from flask import Blueprint, request, jsonify, g
from src.mailer.sender import EmailSender
from src.tenancy.decorators import require_tenant
from src.tenancy.context import get_current_tenant_id
from src.auth_api import require_auth

logger = logging.getLogger(__name__)
bp = Blueprint('email', __name__, url_prefix='/api/email')

email_sender = EmailSender()

@bp.route('/test', methods=['POST'])
@require_auth
@require_tenant()
def send_test_email():
    """Send test email to current user (dev only)"""
    try:
        # Only allow in development
        from flask import current_app
        if current_app.config.get('ENV') == 'production':
            return jsonify({'error': 'Test emails not allowed in production'}), 403
        
        data = request.get_json()
        template = data.get('template', 'welcome')
        payload = data.get('payload', {})
        
        # Get current user email
        user_email = g.get('user_email') or 'test@example.com'
        tenant_id = get_current_tenant_id()
        
        # Send test email
        result = email_sender.send_email(tenant_id, user_email, template, payload)
        
        return jsonify({
            'success': True,
            'email': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/outbound', methods=['GET'])
@require_auth
@require_tenant()
def list_emails():
    """List recent outbound emails"""
    try:
        tenant_id = get_current_tenant_id()
        limit = min(int(request.args.get('limit', 50)), 100)
        
        emails = email_sender.list_emails(tenant_id, limit)
        
        return jsonify({
            'success': True,
            'emails': emails
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing emails: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/templates', methods=['GET'])
@require_auth
@require_tenant()
def list_templates():
    """List available email templates"""
    try:
        templates = email_sender.get_email_templates()
        
        return jsonify({
            'success': True,
            'templates': templates
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing email templates: {e}")
        return jsonify({'error': 'Internal server error'}), 500
