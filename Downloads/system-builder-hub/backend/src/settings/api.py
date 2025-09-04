"""
Settings Hub API
REST API endpoints for settings management.
"""

import logging
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import Session
from .service import settings_service
from .diagnostics import diagnostics_service
from ..privacy.service import privacy_service
from ..crypto.keys import get_key_manager

logger = logging.getLogger(__name__)

# Create blueprint
settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')

# Helper function to get database session
def get_db():
    return current_app.db.session

# Helper function to check RBAC
def require_owner_or_admin():
    """Require owner or admin role."""
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401
    
    # TODO: Implement proper RBAC check
    # For now, assume all authenticated users can access
    return None

# User Account Settings

@settings_bp.route('/account/profile', methods=['GET'])
@login_required
def get_account_profile():
    """Get user profile settings."""
    try:
        db = get_db()
        settings = settings_service.get_user_settings(current_user.id, db)
        
        if not settings:
            return jsonify({"error": "Settings not found"}), 404
        
        return jsonify({
            "data": settings.to_dict()
        })
    except Exception as e:
        logger.error(f"Failed to get account profile: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/account/profile', methods=['PUT'])
@login_required
def update_account_profile():
    """Update user profile settings."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        db = get_db()
        
        # Extract profile data
        profile_data = data.get('profile', {})
        update_data = {}
        
        if 'name' in profile_data:
            update_data['name'] = profile_data['name']
        if 'avatar_url' in profile_data:
            update_data['avatar_url'] = profile_data['avatar_url']
        if 'timezone' in profile_data:
            update_data['timezone'] = profile_data['timezone']
        if 'locale' in profile_data:
            update_data['locale'] = profile_data['locale']
        
        settings = settings_service.update_user_settings(current_user.id, db, **update_data)
        
        return jsonify({
            "data": settings.to_dict(),
            "message": "Profile updated successfully"
        })
    except Exception as e:
        logger.error(f"Failed to update account profile: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/account/security', methods=['GET'])
@login_required
def get_account_security():
    """Get user security settings."""
    try:
        db = get_db()
        settings = settings_service.get_user_settings(current_user.id, db)
        
        if not settings:
            return jsonify({"error": "Settings not found"}), 404
        
        return jsonify({
            "data": {
                "two_factor_enabled": settings.two_factor_enabled,
                "has_recovery_codes": bool(settings.recovery_codes)
            }
        })
    except Exception as e:
        logger.error(f"Failed to get account security: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/account/security/2fa/enable', methods=['POST'])
@login_required
def enable_2fa():
    """Enable 2FA for user."""
    try:
        db = get_db()
        result = settings_service.enable_2fa(current_user.id, db)
        
        return jsonify({
            "data": result,
            "message": "2FA enabled successfully"
        })
    except Exception as e:
        logger.error(f"Failed to enable 2FA: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/account/security/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    """Disable 2FA for user."""
    try:
        db = get_db()
        success = settings_service.disable_2fa(current_user.id, db)
        
        if not success:
            return jsonify({"error": "Failed to disable 2FA"}), 400
        
        return jsonify({
            "message": "2FA disabled successfully"
        })
    except Exception as e:
        logger.error(f"Failed to disable 2FA: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/account/security/recovery-codes', methods=['POST'])
@login_required
def generate_recovery_codes():
    """Generate new recovery codes."""
    try:
        db = get_db()
        codes = settings_service.generate_recovery_codes(current_user.id, db)
        
        return jsonify({
            "data": {
                "recovery_codes": codes
            },
            "message": "Recovery codes generated successfully"
        })
    except Exception as e:
        logger.error(f"Failed to generate recovery codes: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/account/sessions', methods=['GET'])
@login_required
def get_account_sessions():
    """Get user sessions."""
    try:
        db = get_db()
        sessions = settings_service.get_user_sessions(current_user.id, db)
        
        return jsonify({
            "data": [session.to_dict() for session in sessions]
        })
    except Exception as e:
        logger.error(f"Failed to get account sessions: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/account/sessions/<session_id>/revoke', methods=['POST'])
@login_required
def revoke_session(session_id):
    """Revoke a user session."""
    try:
        db = get_db()
        success = settings_service.revoke_user_session(session_id, current_user.id, db)
        
        if not success:
            return jsonify({"error": "Session not found"}), 404
        
        return jsonify({
            "message": "Session revoked successfully"
        })
    except Exception as e:
        logger.error(f"Failed to revoke session: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/account/notifications', methods=['GET'])
@login_required
def get_account_notifications():
    """Get user notification settings."""
    try:
        db = get_db()
        settings = settings_service.get_user_settings(current_user.id, db)
        
        if not settings:
            return jsonify({"error": "Settings not found"}), 404
        
        return jsonify({
            "data": {
                "email_digest_daily": settings.email_digest_daily,
                "email_digest_weekly": settings.email_digest_weekly,
                "mention_emails": settings.mention_emails,
                "approvals_emails": settings.approvals_emails
            }
        })
    except Exception as e:
        logger.error(f"Failed to get account notifications: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/account/notifications', methods=['PUT'])
@login_required
def update_account_notifications():
    """Update user notification settings."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        db = get_db()
        
        # Extract notification data
        notification_data = data.get('notifications', {})
        update_data = {}
        
        if 'email_digest_daily' in notification_data:
            update_data['email_digest_daily'] = notification_data['email_digest_daily']
        if 'email_digest_weekly' in notification_data:
            update_data['email_digest_weekly'] = notification_data['email_digest_weekly']
        if 'mention_emails' in notification_data:
            update_data['mention_emails'] = notification_data['mention_emails']
        if 'approvals_emails' in notification_data:
            update_data['approvals_emails'] = notification_data['approvals_emails']
        
        settings = settings_service.update_user_settings(current_user.id, db, **update_data)
        
        return jsonify({
            "data": {
                "email_digest_daily": settings.email_digest_daily,
                "email_digest_weekly": settings.email_digest_weekly,
                "mention_emails": settings.mention_emails,
                "approvals_emails": settings.approvals_emails
            },
            "message": "Notification settings updated successfully"
        })
    except Exception as e:
        logger.error(f"Failed to update account notifications: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Workspace Settings

@settings_bp.route('/workspace/overview', methods=['GET'])
@login_required
def get_workspace_overview():
    """Get workspace overview."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400
        
        db = get_db()
        settings = settings_service.get_tenant_settings(tenant_id, db)
        
        if not settings:
            return jsonify({"error": "Settings not found"}), 404
        
        return jsonify({
            "data": settings.to_dict()
        })
    except Exception as e:
        logger.error(f"Failed to get workspace overview: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/workspace/overview', methods=['PUT'])
@login_required
def update_workspace_overview():
    """Update workspace overview."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        tenant_id = data.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400
        
        db = get_db()
        
        # Extract profile data
        profile_data = data.get('profile', {})
        update_data = {}
        
        if 'display_name' in profile_data:
            update_data['display_name'] = profile_data['display_name']
        if 'brand_color' in profile_color:
            update_data['brand_color'] = profile_data['brand_color']
        if 'logo_url' in profile_data:
            update_data['logo_url'] = profile_data['logo_url']
        
        settings = settings_service.update_tenant_settings(tenant_id, current_user.id, db, **update_data)
        
        return jsonify({
            "data": settings.to_dict(),
            "message": "Workspace overview updated successfully"
        })
    except Exception as e:
        logger.error(f"Failed to update workspace overview: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/workspace/privacy', methods=['GET'])
@login_required
def get_workspace_privacy():
    """Get workspace privacy settings."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400
        
        db = get_db()
        privacy_settings = privacy_service.get_privacy_settings(tenant_id, db)
        
        if not privacy_settings:
            return jsonify({"error": "Privacy settings not found"}), 404
        
        return jsonify({
            "data": privacy_settings.to_dict()
        })
    except Exception as e:
        logger.error(f"Failed to get workspace privacy: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/workspace/privacy', methods=['PUT'])
@login_required
def update_workspace_privacy():
    """Update workspace privacy settings."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        tenant_id = data.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400
        
        db = get_db()
        
        # Update privacy settings
        privacy_settings = privacy_service.update_privacy_settings(
            tenant_id, current_user.id, db, **data
        )
        
        return jsonify({
            "data": privacy_settings.to_dict(),
            "message": "Privacy settings updated successfully"
        })
    except Exception as e:
        logger.error(f"Failed to update workspace privacy: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/workspace/developer', methods=['GET'])
@login_required
def get_workspace_developer():
    """Get workspace developer settings."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400
        
        db = get_db()
        settings = settings_service.get_tenant_settings(tenant_id, db)
        
        if not settings:
            return jsonify({"error": "Settings not found"}), 404
        
        return jsonify({
            "data": {
                "default_llm_provider": settings.default_llm_provider,
                "default_llm_model": settings.default_llm_model,
                "temperature_default": settings.temperature_default,
                "http_allowlist": settings.get_http_allowlist()
            }
        })
    except Exception as e:
        logger.error(f"Failed to get workspace developer: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/workspace/developer', methods=['PUT'])
@login_required
def update_workspace_developer():
    """Update workspace developer settings."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        tenant_id = data.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400
        
        db = get_db()
        
        # Extract developer data
        developer_data = data.get('developer', {})
        update_data = {}
        
        if 'default_llm_provider' in developer_data:
            update_data['default_llm_provider'] = developer_data['default_llm_provider']
        if 'default_llm_model' in developer_data:
            update_data['default_llm_model'] = developer_data['default_llm_model']
        if 'temperature_default' in developer_data:
            update_data['temperature_default'] = developer_data['temperature_default']
        if 'http_allowlist' in developer_data:
            settings = settings_service.get_tenant_settings(tenant_id, db)
            if settings:
                settings.set_http_allowlist(developer_data['http_allowlist'])
                db.commit()
        
        settings = settings_service.update_tenant_settings(tenant_id, current_user.id, db, **update_data)
        
        return jsonify({
            "data": {
                "default_llm_provider": settings.default_llm_provider,
                "default_llm_model": settings.default_llm_model,
                "temperature_default": settings.temperature_default,
                "http_allowlist": settings.get_http_allowlist()
            },
            "message": "Developer settings updated successfully"
        })
    except Exception as e:
        logger.error(f"Failed to update workspace developer: {e}")
        return jsonify({"error": "Internal server error"}), 500

# API Keys

@settings_bp.route('/workspace/api-keys', methods=['GET'])
@login_required
def get_workspace_api_keys():
    """Get workspace API keys."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400
        
        db = get_db()
        tokens = settings_service.get_api_tokens(tenant_id, db)
        
        return jsonify({
            "data": [token.to_dict() for token in tokens]
        })
    except Exception as e:
        logger.error(f"Failed to get workspace API keys: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/workspace/api-keys', methods=['POST'])
@login_required
def create_workspace_api_key():
    """Create workspace API key."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        tenant_id = data.get('tenant_id')
        name = data.get('name')
        permissions = data.get('permissions', [])
        
        if not tenant_id or not name:
            return jsonify({"error": "Tenant ID and name required"}), 400
        
        db = get_db()
        result = settings_service.create_api_token(tenant_id, current_user.id, name, permissions, db)
        
        return jsonify({
            "data": result,
            "message": "API key created successfully"
        })
    except Exception as e:
        logger.error(f"Failed to create workspace API key: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/workspace/api-keys/<token_id>/revoke', methods=['POST'])
@login_required
def revoke_workspace_api_key(token_id):
    """Revoke workspace API key."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400
        
        db = get_db()
        success = settings_service.revoke_api_token(token_id, tenant_id, current_user.id, db)
        
        if not success:
            return jsonify({"error": "API key not found"}), 404
        
        return jsonify({
            "message": "API key revoked successfully"
        })
    except Exception as e:
        logger.error(f"Failed to revoke workspace API key: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Webhooks

@settings_bp.route('/workspace/webhooks', methods=['GET'])
@login_required
def get_workspace_webhooks():
    """Get workspace webhooks."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400
        
        db = get_db()
        webhooks = settings_service.get_webhooks(tenant_id, db)
        
        return jsonify({
            "data": [webhook.to_dict() for webhook in webhooks]
        })
    except Exception as e:
        logger.error(f"Failed to get workspace webhooks: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/workspace/webhooks', methods=['POST'])
@login_required
def create_workspace_webhook():
    """Create workspace webhook."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        tenant_id = data.get('tenant_id')
        name = data.get('name')
        target_url = data.get('target_url')
        events = data.get('events', [])
        
        if not all([tenant_id, name, target_url]):
            return jsonify({"error": "Tenant ID, name, and target URL required"}), 400
        
        db = get_db()
        webhook = settings_service.create_webhook(tenant_id, current_user.id, name, target_url, events, db)
        
        return jsonify({
            "data": webhook.to_dict(),
            "message": "Webhook created successfully"
        })
    except Exception as e:
        logger.error(f"Failed to create workspace webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/workspace/webhooks/<webhook_id>/test', methods=['POST'])
@login_required
def test_workspace_webhook(webhook_id):
    """Test workspace webhook."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400
        
        db = get_db()
        result = settings_service.test_webhook(webhook_id, tenant_id, db)
        
        return jsonify({
            "data": result
        })
    except Exception as e:
        logger.error(f"Failed to test workspace webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Diagnostics

@settings_bp.route('/workspace/diagnostics', methods=['GET'])
@login_required
def get_workspace_diagnostics():
    """Get workspace diagnostics."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400
        
        db = get_db()
        
        # Get system health
        health = diagnostics_service.get_system_health(tenant_id, db)
        
        # Get metrics summary
        metrics = diagnostics_service.get_metrics_summary(tenant_id, db)
        
        # Get config snapshot
        config = diagnostics_service.get_config_snapshot(tenant_id, db)
        
        return jsonify({
            "data": {
                "health": health,
                "metrics": metrics,
                "config": config
            }
        })
    except Exception as e:
        logger.error(f"Failed to get workspace diagnostics: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Danger Zone

@settings_bp.route('/workspace/danger/rotate-secrets', methods=['POST'])
@login_required
def rotate_workspace_secrets():
    """Rotate workspace secrets."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        tenant_id = data.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400
        
        db = get_db()
        
        # TODO: Implement secret rotation
        # For now, just return success
        
        return jsonify({
            "message": "Secrets rotated successfully"
        })
    except Exception as e:
        logger.error(f"Failed to rotate workspace secrets: {e}")
        return jsonify({"error": "Internal server error"}), 500

@settings_bp.route('/workspace/danger/delete', methods=['POST'])
@login_required
def delete_workspace():
    """Delete workspace."""
    try:
        # Check RBAC
        rbac_check = require_owner_or_admin()
        if rbac_check:
            return rbac_check
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        tenant_id = data.get('tenant_id')
        guard_phrase = data.get('guard_phrase')
        
        if not tenant_id or not guard_phrase:
            return jsonify({"error": "Tenant ID and guard phrase required"}), 400
        
        # TODO: Implement workspace deletion
        # For now, just return success
        
        return jsonify({
            "message": "Workspace deletion initiated"
        })
    except Exception as e:
        logger.error(f"Failed to delete workspace: {e}")
        return jsonify({"error": "Internal server error"}), 500
