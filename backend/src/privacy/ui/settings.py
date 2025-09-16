"""
Privacy Settings UI Component
Admin UI for privacy settings management.
"""

import json
from typing import Dict, Any, Optional
from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from ..service import privacy_service
from ..modes import PrivacyMode
from ...database import db_session

def render_privacy_settings_page():
    """Render the privacy settings admin page."""
    try:
        tenant_id = current_user.tenant_id
        
        with db_session() as db:
            settings = privacy_service.get_privacy_settings(tenant_id, db)
            mode = privacy_service.get_privacy_mode(tenant_id, db)
            
            # Get available privacy modes
            available_modes = [
                {
                    "value": mode.value,
                    "label": mode.value.replace("_", " ").title(),
                    "description": privacy_service.get_config(mode).description
                }
                for mode in PrivacyMode
            ]
            
            # Get retention policy options
            retention_options = [
                {"value": 0, "label": "No retention"},
                {"value": 3600, "label": "1 hour"},
                {"value": 86400, "label": "24 hours"},
                {"value": 604800, "label": "7 days"},
                {"value": 2592000, "label": "30 days"}
            ]
            
            return render_template(
                'admin/privacy_settings.html',
                settings=settings,
                current_mode=mode.value,
                available_modes=available_modes,
                retention_options=retention_options
            )
    except Exception as e:
        current_app.logger.error(f"Failed to render privacy settings: {e}")
        return render_template('error.html', error="Failed to load privacy settings")


def render_transparency_panel():
    """Render the privacy transparency panel."""
    try:
        tenant_id = current_user.tenant_id
        
        with db_session() as db:
            mode = privacy_service.get_privacy_mode(tenant_id, db)
            settings = privacy_service.get_privacy_settings(tenant_id, db)
            
            # Get recent transparency events
            transparency_logs = db.query(PrivacyTransparencyLog).filter(
                PrivacyTransparencyLog.tenant_id == tenant_id
            ).order_by(PrivacyTransparencyLog.created_at.desc()).limit(5).all()
            
            return render_template(
                'components/privacy_transparency.html',
                mode=mode.value,
                settings=settings,
                recent_events=transparency_logs
            )
    except Exception as e:
        current_app.logger.error(f"Failed to render transparency panel: {e}")
        return render_template('components/error.html', error="Failed to load transparency info")


def handle_privacy_settings_update():
    """Handle privacy settings update from UI."""
    try:
        tenant_id = current_user.tenant_id
        user_id = current_user.id
        data = request.get_json()
        
        with db_session() as db:
            settings = privacy_service.update_privacy_settings(
                tenant_id=tenant_id,
                user_id=user_id,
                db=db,
                **data
            )
            
            return jsonify({
                "success": True,
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
            })
    except Exception as e:
        current_app.logger.error(f"Failed to update privacy settings: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to update privacy settings"
        }), 500


def handle_byo_key_storage():
    """Handle BYO key storage from UI."""
    try:
        tenant_id = current_user.tenant_id
        data = request.get_json()
        
        key_name = data.get('key_name')
        key_value = data.get('key_value')
        
        if not key_name or not key_value:
            return jsonify({
                "success": False,
                "error": "Key name and value are required"
            }), 400
        
        with db_session() as db:
            success = privacy_service.store_byo_key(tenant_id, key_name, key_value, db)
            
            if success:
                return jsonify({
                    "success": True,
                    "message": f"BYO key {key_name} stored successfully"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": f"Failed to store BYO key {key_name}"
                }), 500
    except Exception as e:
        current_app.logger.error(f"Failed to store BYO key: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to store BYO key"
        }), 500
