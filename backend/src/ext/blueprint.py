"""
Plugin Flask blueprint for mounting plugin routes
"""
import logging
from flask import Blueprint, request, jsonify, g
from src.ext.registry import plugin_registry
from src.ext.sandbox import plugin_sandbox
from src.security.decorators import require_tenant_context
from src.tenancy.context import get_current_tenant_id
from src.ext.sdk import PluginContext

logger = logging.getLogger(__name__)

def create_plugin_blueprint(plugin_slug: str):
    """Create Flask blueprint for a plugin"""
    
    bp = Blueprint(f'plugin_{plugin_slug}', __name__, url_prefix=f'/ext/{plugin_slug}')
    
    @bp.before_request
    def before_request():
        """Before request handler"""
        # Ensure tenant context
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({'error': 'Tenant context required'}), 401
        
        # Get plugin
        loaded_plugin = plugin_registry.get_plugin(tenant_id, plugin_slug)
        if not loaded_plugin:
            return jsonify({'error': 'Plugin not found'}), 404
        
        if not loaded_plugin.installation.enabled:
            return jsonify({'error': 'Plugin not enabled'}), 403
        
        # Store plugin in request context
        g.plugin = loaded_plugin
    
    @bp.route('/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
    def plugin_route(subpath):
        """Handle plugin routes"""
        try:
            loaded_plugin = g.plugin
            tenant_id = get_current_tenant_id()
            
            # Find route handler
            route_handler = None
            for attr_name in dir(loaded_plugin.module):
                attr = getattr(loaded_plugin.module, attr_name)
                if (hasattr(attr, '_plugin_route_type') and 
                    attr._plugin_route_type == 'route' and
                    attr._plugin_route_path == f'/{subpath}' and
                    request.method in attr._plugin_route_methods):
                    route_handler = attr
                    break
            
            if not route_handler:
                return jsonify({'error': 'Route not found'}), 404
            
            # Create context
            ctx = PluginContext(
                tenant_id=tenant_id,
                user_id=getattr(g, 'user_id', None),
                role=getattr(g, 'role', 'viewer')
            )
            
            # Get request data
            request_data = {}
            if request.is_json:
                request_data = request.get_json()
            elif request.form:
                request_data = dict(request.form)
            elif request.args:
                request_data = dict(request.args)
            
            # Run route handler in sandbox
            result = plugin_sandbox.execute_with_limits(route_handler, ctx, request_data)
            
            if result.get('success', False):
                return jsonify(result.get('result', {}))
            else:
                return jsonify({
                    'error': result.get('error', 'Plugin route execution failed')
                }), 500
                
        except Exception as e:
            logger.error(f"Error in plugin route {subpath}: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    return bp

def mount_plugin_routes(app):
    """Mount all plugin routes"""
    try:
        # Get all loaded plugins
        for tenant_id, plugins in plugin_registry._plugins.items():
            for plugin_slug, loaded_plugin in plugins.items():
                if loaded_plugin.installation.enabled and loaded_plugin.plugin.routes:
                    # Create and register blueprint
                    bp = create_plugin_blueprint(plugin_slug)
                    app.register_blueprint(bp)
                    logger.info(f"Mounted routes for plugin {plugin_slug}")
                    
    except Exception as e:
        logger.error(f"Error mounting plugin routes: {e}")
