"""
Marketplace API endpoints
"""
import logging
from flask import Blueprint, request, jsonify, g
from src.market.service import MarketplaceService
from src.tenancy.decorators import require_tenant
from src.tenancy.context import get_current_tenant_id
from src.auth_api import require_auth
from src.analytics.service import AnalyticsService

logger = logging.getLogger(__name__)
bp = Blueprint('market', __name__, url_prefix='/api/market')

marketplace_service = MarketplaceService()
analytics_service = AnalyticsService()

@bp.route('/templates', methods=['GET'])
@require_auth
@require_tenant()
def list_templates():
    """List templates with filtering and pagination"""
    try:
        # Get query parameters
        category = request.args.get('category')
        search = request.args.get('q')
        price_filter = request.args.get('price')
        requires_plan = request.args.get('requires_plan')
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        # List templates
        result = marketplace_service.list_templates(
            category=category,
            search=search,
            price_filter=price_filter,
            requires_plan=requires_plan,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/templates/<slug>', methods=['GET'])
@require_auth
@require_tenant()
def get_template(slug):
    """Get template details"""
    try:
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        # Track view analytics
        try:
            analytics_service.track(
                tenant_id=tenant_id,
                event='market.template.view',
                user_id=user_id,
                source='market',
                props={'template_slug': slug}
            )
        except Exception as e:
            logger.warning(f"Failed to track template view: {e}")
        
        # Get template
        template = marketplace_service.get_template(slug)
        
        if not template:
            return jsonify({'error': 'Template not found'}), 404
        
        return jsonify({
            'success': True,
            'data': template
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting template {slug}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/templates/<slug>/plan', methods=['POST'])
@require_auth
@require_tenant()
def plan_template(slug):
    """Plan template using guided input"""
    try:
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        guided_input = data.get('guided_input', {})
        
        # Plan template
        result = marketplace_service.plan_template(slug, guided_input)
        
        # Track plan analytics
        try:
            analytics_service.track(
                tenant_id=tenant_id,
                event='market.template.use.start',
                user_id=user_id,
                source='market',
                props={
                    'template_slug': slug,
                    'guided_input': guided_input
                }
            )
        except Exception as e:
            logger.warning(f"Failed to track template plan: {e}")
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error planning template {slug}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/templates/<slug>/use', methods=['POST'])
@require_auth
@require_tenant()
def use_template(slug):
    """Use template to create project and generate build"""
    try:
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        guided_input = data.get('guided_input', {})
        variant_id = data.get('variant_id')
        
        # Check if template requires subscription
        template = marketplace_service.get_template(slug)
        if template and template.get('requires_plan'):
            return jsonify({
                'error': 'Template requires subscription',
                'requires_subscription': template['requires_plan']
            }), 402
        
        # Use template
        result = marketplace_service.use_template(
            slug=slug,
            guided_input=guided_input,
            variant_id=variant_id,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error using template {slug}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/templates', methods=['POST'])
@require_auth
@require_tenant()
def create_template():
    """Create a new template (admin only)"""
    try:
        # Check if user is admin
        if not hasattr(g, 'user_role') or g.user_role not in ['admin', 'owner']:
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        # Validate required fields
        required_fields = ['slug', 'name', 'category']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create template
        template = marketplace_service.create_template(
            template_data=data,
            author_user_id=g.user_id if hasattr(g, 'user_id') else None
        )
        
        return jsonify({
            'success': True,
            'data': template
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/templates/<slug>/publish', methods=['POST'])
@require_auth
@require_tenant()
def publish_template(slug):
    """Publish a template (admin only)"""
    try:
        # Check if user is admin
        if not hasattr(g, 'user_role') or g.user_role not in ['admin', 'owner']:
            return jsonify({'error': 'Admin access required'}), 403
        
        # Publish template
        success = marketplace_service.publish_template(slug)
        
        if not success:
            return jsonify({'error': 'Template not found'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Template published successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error publishing template {slug}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/templates/<slug>/unpublish', methods=['POST'])
@require_auth
@require_tenant()
def unpublish_template(slug):
    """Unpublish a template (admin only)"""
    try:
        # Check if user is admin
        if not hasattr(g, 'user_role') or g.user_role not in ['admin', 'owner']:
            return jsonify({'error': 'Admin access required'}), 403
        
        # Unpublish template
        success = marketplace_service.unpublish_template(slug)
        
        if not success:
            return jsonify({'error': 'Template not found'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Template unpublished successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error unpublishing template {slug}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
