"""
Plugin API endpoints
"""
import logging
import zipfile
import tempfile
from flask import Blueprint, request, jsonify, g
from src.ext.loader import plugin_loader
from src.ext.registry import plugin_registry
from src.ext.models import Plugin, PluginInstallation
from src.ext.sandbox import plugin_sandbox
from src.security.policy import UserContext, Action, Resource, Role
from src.security.decorators import require_role, require_tenant_context
from src.tenancy.context import get_current_tenant_id
from src.database import db_session

logger = logging.getLogger(__name__)

bp = Blueprint('plugins', __name__, url_prefix='/api/plugins')

@bp.route('/', methods=['GET'])
@require_tenant_context
def list_plugins():
    """List installed plugins for tenant"""
    try:
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            installations = session.query(PluginInstallation).filter(
                PluginInstallation.tenant_id == tenant_id
            ).all()
            
            plugins = []
            for installation in installations:
                plugin = session.query(Plugin).filter(
                    Plugin.id == installation.plugin_id
                ).first()
                
                if plugin:
                    plugins.append({
                        'id': str(installation.id),
                        'slug': plugin.slug,
                        'name': plugin.name,
                        'version': plugin.version,
                        'description': plugin.description,
                        'enabled': installation.enabled,
                        'installed_version': installation.installed_version,
                        'permissions': installation.permissions_json,
                        'created_at': installation.created_at.isoformat()
                    })
            
            return jsonify({
                'success': True,
                'data': plugins
            })
            
    except Exception as e:
        logger.error(f"Error listing plugins: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/upload', methods=['POST'])
@require_role(Role.ADMIN)
@require_tenant_context
def upload_plugin():
    """Upload and install plugin"""
    try:
        tenant_id = get_current_tenant_id()
        
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
            file.save(temp_file.name)
            
            # Load plugin from ZIP
            plugin, installation = plugin_loader.load_plugin_from_zip(temp_file.name, tenant_id)
            
            # Save to database
            with db_session() as session:
                session.add(plugin)
                session.flush()  # Get plugin ID
                
                installation.plugin_id = plugin.id
                session.add(installation)
                session.commit()
            
            # Load plugin module
            loaded_plugin = plugin_loader.load_plugin_module(plugin, installation)
            
            # Install in registry
            plugin_registry.install_plugin(tenant_id, installation, plugin, loaded_plugin.module)
            
            return jsonify({
                'success': True,
                'data': {
                    'plugin_id': str(plugin.id),
                    'installation_id': str(installation.id),
                    'slug': plugin.slug,
                    'name': plugin.name,
                    'version': plugin.version
                }
            })
            
    except Exception as e:
        logger.error(f"Error uploading plugin: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<plugin_id>/enable', methods=['POST'])
@require_role(Role.ADMIN)
@require_tenant_context
def enable_plugin(plugin_id):
    """Enable a plugin"""
    try:
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            installation = session.query(PluginInstallation).filter(
                PluginInstallation.id == plugin_id,
                PluginInstallation.tenant_id == tenant_id
            ).first()
            
            if not installation:
                return jsonify({
                    'success': False,
                    'error': 'Plugin installation not found'
                }), 404
            
            plugin = session.query(Plugin).filter(
                Plugin.id == installation.plugin_id
            ).first()
            
            if not plugin:
                return jsonify({
                    'success': False,
                    'error': 'Plugin not found'
                }), 404
            
            # Enable in registry
            success = plugin_registry.enable_plugin(tenant_id, plugin.slug)
            
            if success:
                return jsonify({
                    'success': True,
                    'data': {
                        'plugin_id': str(installation.id),
                        'enabled': True
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to enable plugin'
                }), 500
            
    except Exception as e:
        logger.error(f"Error enabling plugin: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<plugin_id>/disable', methods=['POST'])
@require_role(Role.ADMIN)
@require_tenant_context
def disable_plugin(plugin_id):
    """Disable a plugin"""
    try:
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            installation = session.query(PluginInstallation).filter(
                PluginInstallation.id == plugin_id,
                PluginInstallation.tenant_id == tenant_id
            ).first()
            
            if not installation:
                return jsonify({
                    'success': False,
                    'error': 'Plugin installation not found'
                }), 404
            
            plugin = session.query(Plugin).filter(
                Plugin.id == installation.plugin_id
            ).first()
            
            if not plugin:
                return jsonify({
                    'success': False,
                    'error': 'Plugin not found'
                }), 404
            
            # Disable in registry
            success = plugin_registry.disable_plugin(tenant_id, plugin.slug)
            
            if success:
                return jsonify({
                    'success': True,
                    'data': {
                        'plugin_id': str(installation.id),
                        'enabled': False
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to disable plugin'
                }), 500
            
    except Exception as e:
        logger.error(f"Error disabling plugin: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<plugin_id>/secrets', methods=['POST'])
@require_role(Role.ADMIN)
@require_tenant_context
def set_secret(plugin_id):
    """Set plugin secret"""
    try:
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        key = data.get('key')
        value = data.get('value')
        
        if not key or not value:
            return jsonify({
                'success': False,
                'error': 'Key and value are required'
            }), 400
        
        with db_session() as session:
            installation = session.query(PluginInstallation).filter(
                PluginInstallation.id == plugin_id,
                PluginInstallation.tenant_id == tenant_id
            ).first()
            
            if not installation:
                return jsonify({
                    'success': False,
                    'error': 'Plugin installation not found'
                }), 404
            
            # Set secret
            from src.ext.secrets import SecretsManager
            secrets_manager = SecretsManager(tenant_id, str(installation.id))
            success = secrets_manager.set(key, value)
            
            if success:
                return jsonify({
                    'success': True,
                    'data': {
                        'key': key,
                        'set': True
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to set secret'
                }), 500
            
    except Exception as e:
        logger.error(f"Error setting secret: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<plugin_id>/jobs/<job_name>/run-now', methods=['POST'])
@require_role(Role.ADMIN)
@require_tenant_context
def run_job_now(plugin_id, job_name):
    """Run plugin job immediately"""
    try:
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            installation = session.query(PluginInstallation).filter(
                PluginInstallation.id == plugin_id,
                PluginInstallation.tenant_id == tenant_id
            ).first()
            
            if not installation:
                return jsonify({
                    'success': False,
                    'error': 'Plugin installation not found'
                }), 404
            
            plugin = session.query(Plugin).filter(
                Plugin.id == installation.plugin_id
            ).first()
            
            if not plugin:
                return jsonify({
                    'success': False,
                    'error': 'Plugin not found'
                }), 404
            
            # Get loaded plugin
            loaded_plugin = plugin_registry.get_plugin(tenant_id, plugin.slug)
            if not loaded_plugin:
                return jsonify({
                    'success': False,
                    'error': 'Plugin not loaded'
                }), 500
            
            # Find job function
            job_func = None
            for attr_name in dir(loaded_plugin.module):
                attr = getattr(loaded_plugin.module, attr_name)
                if (hasattr(attr, '_plugin_job_type') and 
                    attr._plugin_job_type == 'job' and 
                    attr._plugin_job_name == job_name):
                    job_func = attr
                    break
            
            if not job_func:
                return jsonify({
                    'success': False,
                    'error': f'Job {job_name} not found'
                }), 404
            
            # Create context and run job
            from src.ext.sdk import PluginContext
            ctx = PluginContext(tenant_id, getattr(g, 'user_id', None))
            
            # Run in sandbox
            result = plugin_sandbox.execute_with_limits(job_func, ctx)
            
            return jsonify({
                'success': True,
                'data': {
                    'job_name': job_name,
                    'result': result
                }
            })
            
    except Exception as e:
        logger.error(f"Error running job {job_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/test-event', methods=['POST'])
@require_role(Role.ADMIN)
@require_tenant_context
def test_event():
    """Test event delivery"""
    try:
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        event_type = data.get('event_type')
        event_data = data.get('event_data', {})
        
        if not event_type:
            return jsonify({
                'success': False,
                'error': 'event_type is required'
            }), 400
        
        # Get event hooks
        hooks = plugin_registry.get_event_hooks(event_type)
        
        results = []
        for hook in hooks:
            try:
                # Create context
                from src.ext.sdk import PluginContext
                ctx = PluginContext(tenant_id, getattr(g, 'user_id', None))
                
                # Run hook in sandbox
                result = plugin_sandbox.execute_with_limits(hook, ctx, event_data)
                results.append({
                    'hook': hook.__name__,
                    'success': result.get('success', False),
                    'result': result.get('result'),
                    'error': result.get('error')
                })
                
            except Exception as e:
                results.append({
                    'hook': hook.__name__,
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'data': {
                'event_type': event_type,
                'hooks_executed': len(hooks),
                'results': results
            }
        })
        
    except Exception as e:
        logger.error(f"Error testing event: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/metrics', methods=['GET'])
@require_role(Role.ADMIN)
@require_tenant_context
def get_metrics():
    """Get plugin metrics"""
    try:
        tenant_id = get_current_tenant_id()
        
        # Get registry stats
        stats = plugin_registry.get_stats()
        
        # Get tenant-specific stats
        tenant_plugins = plugin_registry.get_tenant_plugins(tenant_id)
        enabled_plugins = plugin_registry.get_enabled_plugins(tenant_id)
        
        return jsonify({
            'success': True,
            'data': {
                'global_stats': stats,
                'tenant_plugins': len(tenant_plugins),
                'enabled_plugins': len(enabled_plugins),
                'plugins': [
                    {
                        'slug': p.plugin.slug,
                        'name': p.plugin.name,
                        'enabled': p.installation.enabled,
                        'hooks': len(p.hooks),
                        'jobs': len(p.jobs)
                    }
                    for p in tenant_plugins
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
