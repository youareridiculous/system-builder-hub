"""
Audit API endpoints
"""
import logging
from flask import Blueprint, jsonify, request
from src.obs.audit import get_recent_audit_events

logger = logging.getLogger(__name__)

bp = Blueprint('audit', __name__, url_prefix='/api/audit')

@bp.route('/recent', methods=['GET'])
def get_recent_events():
    """Get recent audit events (admin only)"""
    try:
        # TODO: Add proper admin authentication
        # For now, allow access (in production, check admin role)
        
        limit = request.args.get('limit', 100, type=int)
        limit = min(limit, 1000)  # Cap at 1000
        
        events = get_recent_audit_events(limit)
        
        return jsonify({
            'success': True,
            'events': events,
            'count': len(events)
        })
        
    except Exception as e:
        logger.error(f"Failed to get audit events: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve audit events'
        }), 500
