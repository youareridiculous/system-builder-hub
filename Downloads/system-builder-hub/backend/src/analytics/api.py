"""
Analytics API endpoints
"""
import logging
from datetime import datetime, date
from flask import Blueprint, request, jsonify, g, Response
from src.analytics.service import AnalyticsService
from src.tenancy.decorators import require_tenant, tenant_admin
from src.tenancy.context import get_current_tenant_id
from src.auth_api import require_auth
from src.keys.middleware import require_api_key

logger = logging.getLogger(__name__)
bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

analytics_service = AnalyticsService()

@bp.route('/events', methods=['GET'])
@require_auth
@require_tenant()
@tenant_admin()
def get_events():
    """Get analytics events"""
    try:
        tenant_id = get_current_tenant_id()
        
        # Parse query parameters
        from_date_str = request.args.get('from')
        to_date_str = request.args.get('to')
        event = request.args.get('event')
        source = request.args.get('source')
        limit = min(int(request.args.get('limit', 100)), 1000)
        cursor = request.args.get('cursor')
        
        # Parse dates
        from_date = None
        to_date = None
        
        if from_date_str:
            try:
                from_date = datetime.fromisoformat(from_date_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid from date format'}), 400
        
        if to_date_str:
            try:
                to_date = datetime.fromisoformat(to_date_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid to date format'}), 400
        
        # Get events
        result = analytics_service.get_events(
            tenant_id=tenant_id,
            from_date=from_date,
            to_date=to_date,
            event=event,
            source=source,
            limit=limit,
            cursor=cursor
        )
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/usage', methods=['GET'])
@require_auth
@require_tenant()
@tenant_admin()
def get_usage():
    """Get usage data"""
    try:
        tenant_id = get_current_tenant_id()
        
        # Parse query parameters
        from_date_str = request.args.get('from')
        to_date_str = request.args.get('to')
        metrics = request.args.getlist('metric')
        
        # Parse dates
        from_date = None
        to_date = None
        
        if from_date_str:
            try:
                from_date = date.fromisoformat(from_date_str)
            except ValueError:
                return jsonify({'error': 'Invalid from date format'}), 400
        
        if to_date_str:
            try:
                to_date = date.fromisoformat(to_date_str)
            except ValueError:
                return jsonify({'error': 'Invalid to date format'}), 400
        
        # Get usage
        result = analytics_service.get_usage(
            tenant_id=tenant_id,
            from_date=from_date,
            to_date=to_date,
            metrics=metrics if metrics else None
        )
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting usage: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/metrics', methods=['GET'])
@require_auth
@require_tenant()
@tenant_admin()
def get_metrics():
    """Get quick metrics for KPIs"""
    try:
        tenant_id = get_current_tenant_id()
        
        result = analytics_service.get_metrics(tenant_id)
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/export.csv', methods=['GET'])
@require_auth
@require_tenant()
@tenant_admin()
def export_csv():
    """Export events to CSV"""
    try:
        tenant_id = get_current_tenant_id()
        
        # Parse query parameters
        from_date_str = request.args.get('from')
        to_date_str = request.args.get('to')
        event = request.args.get('event')
        source = request.args.get('source')
        
        # Parse dates
        from_date = None
        to_date = None
        
        if from_date_str:
            try:
                from_date = datetime.fromisoformat(from_date_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid from date format'}), 400
        
        if to_date_str:
            try:
                to_date = datetime.fromisoformat(to_date_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid to date format'}), 400
        
        # Generate CSV
        csv_content = analytics_service.export_csv(
            tenant_id=tenant_id,
            from_date=from_date,
            to_date=to_date,
            event=event,
            source=source
        )
        
        # Log export for audit
        logger.info(f"Analytics CSV export for tenant {tenant_id}")
        
        # Emit Prometheus metric
        try:
            from src.obs.metrics import get_analytics_export_counter
            counter = get_analytics_export_counter()
            counter.labels(tenant=tenant_id).inc()
        except ImportError:
            pass
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=analytics_export.csv'}
        )
        
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/quotas', methods=['GET'])
@require_auth
@require_tenant()
@tenant_admin()
def get_quotas():
    """Get current quota usage"""
    try:
        tenant_id = get_current_tenant_id()
        
        # Check quotas for common metrics
        quotas = {}
        metrics = ['api_requests_daily', 'builds_daily', 'emails_daily', 'webhooks_daily', 'storage_gb']
        
        for metric in metrics:
            quotas[metric] = analytics_service.check_quota(tenant_id, metric)
        
        return jsonify({
            'success': True,
            'data': quotas
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting quotas: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/rollup', methods=['POST'])
@require_auth
@require_tenant()
@tenant_admin()
def trigger_rollup():
    """Trigger analytics rollup for a specific date"""
    try:
        rollup_date_str = request.args.get('date')
        
        if not rollup_date_str:
            return jsonify({'error': 'Date parameter required'}), 400
        
        try:
            rollup_date = date.fromisoformat(rollup_date_str)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
        
        # Trigger rollup job
        try:
            from src.jobs.analytics_agg import rollup_daily_usage_job
            rollup_daily_usage_job.delay(rollup_date.isoformat())
            
            return jsonify({
                'success': True,
                'message': f'Rollup job queued for {rollup_date_str}'
            }), 200
            
        except ImportError:
            return jsonify({'error': 'Background jobs not available'}), 500
        
    except Exception as e:
        logger.error(f"Error triggering rollup: {e}")
        return jsonify({'error': 'Internal server error'}), 500
