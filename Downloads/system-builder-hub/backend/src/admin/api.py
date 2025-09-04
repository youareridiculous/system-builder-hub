"""
Admin API endpoints
"""
import logging
from flask import Blueprint, request, jsonify, g
from src.jobs.demo_seed import demo_seed_job
from src.tenancy.decorators import require_tenant, tenant_admin
from src.tenancy.context import get_current_tenant_id
from src.analytics.service import AnalyticsService

logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__, url_prefix='/api/admin')
analytics = AnalyticsService()

@bp.route('/seed-demo', methods=['POST'])
@require_tenant
@tenant_admin
def seed_demo():
    """Seed demo data for enterprise stack"""
    try:
        data = request.get_json() or {}
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        # Validate environment (dev & staging only)
        import os
        environment = os.environ.get('FLASK_ENV', 'development')
        if environment == 'production':
            return jsonify({
                'success': False,
                'error': 'Demo seeding is not allowed in production'
            }), 403
        
        # Get parameters
        tenant_slug = data.get('tenant_slug', tenant_id)
        num_projects = data.get('num_projects', 3)
        tasks_per_project = data.get('tasks_per_project', 8)
        
        # Validate parameters
        if num_projects < 1 or num_projects > 10:
            return jsonify({
                'success': False,
                'error': 'num_projects must be between 1 and 10'
            }), 400
        
        if tasks_per_project < 1 or tasks_per_project > 20:
            return jsonify({
                'success': False,
                'error': 'tasks_per_project must be between 1 and 20'
            }), 400
        
        # Track seeding request
        analytics.track(
            tenant_id=tenant_id,
            event='admin.demo_seed.requested',
            user_id=user_id,
            source='admin',
            props={
                'tenant_slug': tenant_slug,
                'num_projects': num_projects,
                'tasks_per_project': tasks_per_project
            }
        )
        
        # Execute demo seeding
        result = demo_seed_job.seed_enterprise_demo(
            tenant_slug=tenant_slug,
            num_projects=num_projects,
            tasks_per_project=tasks_per_project
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Demo seeding failed')
            }), 500
        
    except Exception as e:
        logger.error(f"Error seeding demo data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/analytics', methods=['GET'])
@require_tenant
@tenant_admin
def get_analytics():
    """Get analytics data for admin dashboard"""
    try:
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        # Get date range
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        # Get analytics data
        from src.analytics.service import AnalyticsService
        analytics_service = AnalyticsService()
        
        # Get basic metrics
        metrics = analytics_service.get_daily_usage(
            tenant_id=tenant_id,
            from_date=from_date,
            to_date=to_date
        )
        
        # Get recent events
        events = analytics_service.get_events(
            tenant_id=tenant_id,
            limit=50
        )
        
        return jsonify({
            'success': True,
            'data': {
                'metrics': metrics,
                'recent_events': events
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/domains', methods=['GET'])
@require_tenant
@tenant_admin
def get_domains():
    """Get custom domains for tenant"""
    try:
        tenant_id = get_current_tenant_id()
        
        # Mock domain data
        domains = [
            {
                'domain': f'{tenant_id}.custom.com',
                'status': 'verified',
                'verified_at': '2024-01-15T10:00:00Z',
                'is_primary': True
            },
            {
                'domain': f'www.{tenant_id}.custom.com',
                'status': 'pending',
                'verified_at': None,
                'is_primary': False
            }
        ]
        
        return jsonify({
            'success': True,
            'data': domains
        })
        
    except Exception as e:
        logger.error(f"Error getting domains: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/domains/verify', methods=['POST'])
@require_tenant
@tenant_admin
def verify_domain():
    """Verify a custom domain"""
    try:
        data = request.get_json()
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        domain = data.get('domain')
        if not domain:
            return jsonify({
                'success': False,
                'error': 'domain is required'
            }), 400
        
        # Mock domain verification
        verification_result = {
            'domain': domain,
            'status': 'verified',
            'verified_at': '2024-01-15T10:00:00Z',
            'dns_records': [
                {
                    'type': 'CNAME',
                    'name': domain,
                    'value': f'{tenant_id}.sbh.com'
                }
            ]
        }
        
        # Track domain verification
        analytics.track(
            tenant_id=tenant_id,
            event='admin.domain.verified',
            user_id=user_id,
            source='admin',
            props={
                'domain': domain
            }
        )
        
        return jsonify({
            'success': True,
            'data': verification_result
        })
        
    except Exception as e:
        logger.error(f"Error verifying domain: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/integrations', methods=['GET'])
@require_tenant
@tenant_admin
def get_integrations():
    """Get integration settings"""
    try:
        tenant_id = get_current_tenant_id()
        
        # Mock integration data
        integrations = {
            'api_keys': [
                {
                    'id': 'key_1',
                    'name': 'Production API Key',
                    'created_at': '2024-01-15T10:00:00Z',
                    'last_used': '2024-01-15T12:00:00Z'
                }
            ],
            'webhooks': [
                {
                    'id': 'webhook_1',
                    'url': 'https://api.example.com/webhooks',
                    'events': ['user.created', 'subscription.updated'],
                    'status': 'active'
                }
            ],
            'email_settings': {
                'provider': 'ses',
                'from_email': f'noreply@{tenant_id}.com',
                'templates': ['welcome', 'subscription_created', 'subscription_updated']
            }
        }
        
        return jsonify({
            'success': True,
            'data': integrations
        })
        
    except Exception as e:
        logger.error(f"Error getting integrations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/integrations/test-email', methods=['POST'])
@require_tenant
@tenant_admin
def test_email():
    """Test email integration"""
    try:
        data = request.get_json()
        tenant_id = get_current_tenant_id()
        user_id = g.user_id if hasattr(g, 'user_id') else None
        
        to_email = data.get('to_email')
        template = data.get('template', 'welcome')
        
        if not to_email:
            return jsonify({
                'success': False,
                'error': 'to_email is required'
            }), 400
        
        # Use email.send tool to test
        from src.agent_tools.kernel import tool_kernel
        from src.agent_tools.types import ToolCall, ToolContext
        
        tool_context = ToolContext(
            tenant_id=tenant_id,
            user_id=user_id,
            role='admin'
        )
        
        call = ToolCall(
            id='test_email',
            tool='email.send',
            args={
                'template': template,
                'to': to_email,
                'payload': {
                    'company_name': f'{tenant_id.title()} Corp',
                    'test_mode': True
                },
                'dry_run': True
            }
        )
        
        result = tool_kernel.execute(call, tool_context)
        
        if result.ok:
            return jsonify({
                'success': True,
                'data': {
                    'message': 'Test email sent successfully',
                    'result': result.redacted_output
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error.get('message', 'Failed to send test email')
            }), 500
        
    except Exception as e:
        logger.error(f"Error testing email: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
