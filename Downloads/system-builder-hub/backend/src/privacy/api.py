"""
Privacy API Endpoints
REST API endpoints for privacy settings and operations.
"""

import logging
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import Session
from .service import privacy_service
from .modes import PrivacyMode
from ..database import db_session
from ..auth import require_role

logger = logging.getLogger(__name__)

# Create blueprint
privacy_bp = Blueprint('privacy', __name__, url_prefix='/api/privacy')


@privacy_bp.route('/settings', methods=['GET'])
@login_required
@require_role(['admin', 'owner'])
def get_privacy_settings():
    """Get privacy settings for the current tenant."""
    try:
        tenant_id = current_user.tenant_id
        with db_session() as db:
            settings = privacy_service.get_privacy_settings(tenant_id, db)
            
            if not settings:
                return jsonify({
                    "privacy_mode": PrivacyMode.PRIVATE_CLOUD.value,
                    "prompt_retention_seconds": 86400,
                    "response_retention_seconds": 86400,
                    "do_not_retain_prompts": False,
                    "do_not_retain_model_outputs": False,
                    "strip_attachments_from_logs": True,
                    "disable_third_party_calls": False
                }), 200
            
            return jsonify({
                "privacy_mode": settings.privacy_mode,
                "prompt_retention_seconds": settings.prompt_retention_seconds,
                "response_retention_seconds": settings.response_retention_seconds,
                "do_not_retain_prompts": settings.do_not_retain_prompts,
                "do_not_retain_model_outputs": settings.do_not_retain_model_outputs,
                "strip_attachments_from_logs": settings.strip_attachments_from_logs,
                "disable_third_party_calls": settings.disable_third_party_calls,
                "created_at": settings.created_at.isoformat() if settings.created_at else None,
                "updated_at": settings.updated_at.isoformat() if settings.updated_at else None
            }), 200
    except Exception as e:
        logger.error(f"Failed to get privacy settings: {e}")
        return jsonify({"error": "Failed to get privacy settings"}), 500


@privacy_bp.route('/settings', methods=['PUT'])
@login_required
@require_role(['admin', 'owner'])
def update_privacy_settings():
    """Update privacy settings for the current tenant."""
    try:
        tenant_id = current_user.tenant_id
        user_id = current_user.id
        data = request.get_json()
        
        with db_session() as db:
            settings = privacy_service.update_privacy_settings(
                tenant_id=tenant_id,
                user_id=user_id,
                db=db,
                privacy_mode=data.get('privacy_mode'),
                prompt_retention_seconds=data.get('prompt_retention_seconds'),
                response_retention_seconds=data.get('response_retention_seconds'),
                do_not_retain_prompts=data.get('do_not_retain_prompts'),
                do_not_retain_model_outputs=data.get('do_not_retain_model_outputs'),
                strip_attachments_from_logs=data.get('strip_attachments_from_logs'),
                disable_third_party_calls=data.get('disable_third_party_calls')
            )
            
            return jsonify({
                "message": "Privacy settings updated successfully",
                "settings": {
                    "privacy_mode": settings.privacy_mode,
                    "prompt_retention_seconds": settings.prompt_retention_seconds,
                    "response_retention_seconds": settings.response_retention_seconds,
                    "do_not_retain_prompts": settings.do_not_retain_prompts,
                    "do_not_retain_model_outputs": settings.do_not_retain_model_outputs,
                    "strip_attachments_from_logs": settings.strip_attachments_from_logs,
                    "disable_third_party_calls": settings.disable_third_party_calls
                }
            }), 200
    except Exception as e:
        logger.error(f"Failed to update privacy settings: {e}")
        return jsonify({"error": "Failed to update privacy settings"}), 500


@privacy_bp.route('/settings/mode', methods=['PUT'])
@login_required
@require_role(['admin', 'owner'])
def set_privacy_mode():
    """Set privacy mode for the current tenant."""
    try:
        tenant_id = current_user.tenant_id
        user_id = current_user.id
        data = request.get_json()
        
        mode_name = data.get('privacy_mode')
        if not mode_name:
            return jsonify({"error": "privacy_mode is required"}), 400
        
        try:
            mode = PrivacyMode(mode_name)
        except ValueError:
            return jsonify({"error": f"Invalid privacy mode: {mode_name}"}), 400
        
        with db_session() as db:
            settings = privacy_service.set_privacy_mode(tenant_id, user_id, mode, db)
            
            return jsonify({
                "message": f"Privacy mode updated to {mode.value}",
                "privacy_mode": settings.privacy_mode
            }), 200
    except Exception as e:
        logger.error(f"Failed to set privacy mode: {e}")
        return jsonify({"error": "Failed to set privacy mode"}), 500


@privacy_bp.route('/settings/byo-keys', methods=['POST'])
@login_required
@require_role(['admin', 'owner'])
def store_byo_key():
    """Store a BYO key for the current tenant."""
    try:
        tenant_id = current_user.tenant_id
        data = request.get_json()
        
        key_name = data.get('key_name')
        key_value = data.get('key_value')
        
        if not key_name or not key_value:
            return jsonify({"error": "key_name and key_value are required"}), 400
        
        with db_session() as db:
            success = privacy_service.store_byo_key(tenant_id, key_name, key_value, db)
            
            if success:
                return jsonify({
                    "message": f"BYO key {key_name} stored successfully"
                }), 200
            else:
                return jsonify({"error": f"Failed to store BYO key {key_name}"}), 500
    except Exception as e:
        logger.error(f"Failed to store BYO key: {e}")
        return jsonify({"error": "Failed to store BYO key"}), 500


@privacy_bp.route('/settings/byo-keys/<key_name>', methods=['GET'])
@login_required
@require_role(['admin', 'owner'])
def get_byo_key(key_name):
    """Get a BYO key for the current tenant (returns masked value)."""
    try:
        tenant_id = current_user.tenant_id
        
        with db_session() as db:
            key_value = privacy_service.get_byo_key(tenant_id, key_name, db)
            
            if key_value:
                # Return masked value for security
                masked_value = key_value[:4] + "*" * (len(key_value) - 8) + key_value[-4:]
                return jsonify({
                    "key_name": key_name,
                    "masked_value": masked_value,
                    "has_value": True
                }), 200
            else:
                return jsonify({
                    "key_name": key_name,
                    "has_value": False
                }), 200
    except Exception as e:
        logger.error(f"Failed to get BYO key: {e}")
        return jsonify({"error": "Failed to get BYO key"}), 500


@privacy_bp.route('/transparency', methods=['GET'])
@login_required
def get_transparency_info():
    """Get privacy transparency information for the current tenant."""
    try:
        tenant_id = current_user.tenant_id
        
        with db_session() as db:
            mode = privacy_service.get_privacy_mode(tenant_id, db)
            settings = privacy_service.get_privacy_settings(tenant_id, db)
            
            # Get recent transparency logs
            transparency_logs = db.query(PrivacyTransparencyLog).filter(
                PrivacyTransparencyLog.tenant_id == tenant_id
            ).order_by(PrivacyTransparencyLog.created_at.desc()).limit(10).all()
            
            return jsonify({
                "privacy_mode": mode.value,
                "retention_policies": {
                    "prompts": settings.prompt_retention_seconds if settings else 86400,
                    "responses": settings.response_retention_seconds if settings else 86400
                },
                "feature_toggles": {
                    "do_not_retain_prompts": settings.do_not_retain_prompts if settings else False,
                    "do_not_retain_model_outputs": settings.do_not_retain_model_outputs if settings else False,
                    "strip_attachments_from_logs": settings.strip_attachments_from_logs if settings else True,
                    "disable_third_party_calls": settings.disable_third_party_calls if settings else False
                },
                "recent_events": [
                    {
                        "event_type": log.event_type,
                        "data_category": log.data_category,
                        "data_volume": log.data_volume,
                        "retention_applied": log.retention_applied,
                        "redaction_applied": log.redaction_applied,
                        "created_at": log.created_at.isoformat() if log.created_at else None
                    }
                    for log in transparency_logs
                ]
            }), 200
    except Exception as e:
        logger.error(f"Failed to get transparency info: {e}")
        return jsonify({"error": "Failed to get transparency info"}), 500


@privacy_bp.route('/export', methods=['POST'])
@login_required
@require_role(['admin', 'owner'])
def export_privacy_data():
    """Export privacy-related data for the current tenant."""
    try:
        tenant_id = current_user.tenant_id
        
        with db_session() as db:
            data = privacy_service.export_privacy_data(tenant_id, db)
            
            return jsonify({
                "message": "Privacy data exported successfully",
                "data": data
            }), 200
    except Exception as e:
        logger.error(f"Failed to export privacy data: {e}")
        return jsonify({"error": "Failed to export privacy data"}), 500


@privacy_bp.route('/erase', methods=['POST'])
@login_required
@require_role(['owner'])
def erase_privacy_data():
    """Erase all privacy-related data for the current tenant."""
    try:
        tenant_id = current_user.tenant_id
        
        with db_session() as db:
            success = privacy_service.erase_privacy_data(tenant_id, db)
            
            if success:
                return jsonify({
                    "message": "Privacy data erased successfully"
                }), 200
            else:
                return jsonify({"error": "Failed to erase privacy data"}), 500
    except Exception as e:
        logger.error(f"Failed to erase privacy data: {e}")
        return jsonify({"error": "Failed to erase privacy data"}), 500


@privacy_bp.route('/audit', methods=['GET'])
@login_required
@require_role(['admin', 'owner'])
def get_audit_logs():
    """Get privacy audit logs for the current tenant."""
    try:
        tenant_id = current_user.tenant_id
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        with db_session() as db:
            audit_logs = db.query(PrivacyAuditLog).filter(
                PrivacyAuditLog.tenant_id == tenant_id
            ).order_by(PrivacyAuditLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
            
            total = db.query(PrivacyAuditLog).filter(
                PrivacyAuditLog.tenant_id == tenant_id
            ).count()
            
            return jsonify({
                "audit_logs": [
                    {
                        "action": log.action,
                        "resource_type": log.resource_type,
                        "privacy_mode": log.privacy_mode,
                        "redactions_applied": log.redactions_applied,
                        "details": log.details,
                        "created_at": log.created_at.isoformat() if log.created_at else None,
                        "user_id": log.user_id
                    }
                    for log in audit_logs
                ],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page
                }
            }), 200
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        return jsonify({"error": "Failed to get audit logs"}), 500
