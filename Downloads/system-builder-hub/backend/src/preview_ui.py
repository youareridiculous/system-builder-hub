"""
Preview UI - Serve generated pages and project previews with alias support, dynamic API endpoints, and CRUD operations
"""
import os
import logging
import json
from flask import Blueprint, render_template, jsonify, current_app, request
from functools import wraps

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint("ui_preview", __name__)

def require_auth(f):
    """Mock auth decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def _get_available_templates():
    """Get list of available template files in templates/ui/"""
    try:
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'ui')
        if not os.path.exists(templates_dir):
            return []
        
        templates = []
        for filename in os.listdir(templates_dir):
            if filename.endswith('.html'):
                slug = filename[:-5]  # Remove .html extension
                templates.append(slug)
        
        return sorted(templates)
    except Exception as e:
        logger.error(f"Error getting available templates: {e}")
        return []

def _get_alias_map():
    """Build alias map from available templates and known aliases"""
    try:
        # In a real implementation, this would be built from the builder state
        # For now, we'll use a simple mapping based on common patterns
        alias_map = {}
        
        # Add known aliases (in a real app, this would come from emitted_pages)
        alias_map['taskspage'] = 'tasks'  # taskspage -> tasks
        alias_map['dashboardpage'] = 'dashboard'  # dashboardpage -> dashboard
        alias_map['homepage'] = 'home'  # homepage -> home
        alias_map['aboutpage'] = 'about'  # aboutpage -> about
        
        return alias_map
    except Exception as e:
        logger.error(f"Error building alias map: {e}")
        return {}

def _resolve_template_slug(requested_slug: str) -> str:
    """Resolve a requested slug to its canonical template slug"""
    available_templates = _get_available_templates()
    
    # If the requested slug exists directly, use it
    if requested_slug in available_templates:
        return requested_slug
    
    # Check if it's an alias
    alias_map = _get_alias_map()
    if requested_slug in alias_map:
        canonical_slug = alias_map[requested_slug]
        if canonical_slug in available_templates:
            return canonical_slug
    
    # Not found
    return None

def _get_project_pages(project_id):
    """Get pages generated for a specific project"""
    # In a real implementation, this would query the database
    # For now, return all available templates
    return _get_available_templates()

@bp.route('/ui/hello-page')
@require_auth
def hello_page():
    """Hello World page"""
    return render_template('ui/hello-page.html')

@bp.route('/ui/agent')
@require_auth
def ui_agent():
    """Conversational Builder UI"""
    return render_template('ui/agent.html')

@bp.route('/ui/tasks')
@require_auth
def ui_tasks():
    """Tasks management page"""
    return render_template('ui/tasks.html')

@bp.route('/ui/marketplace')
@require_auth
def ui_marketplace():
    """Marketplace page"""
    return render_template('ui/marketplace.html')

@bp.route('/ui/builds')
@require_auth
def ui_builds():
    """Builds dashboard page"""
    return render_template('ui/builds.html')

@bp.route('/ui/<page>')
@require_auth
def ui_page(page):
    """Serve a UI page by slug with alias support"""
    try:
        # Resolve the requested slug to canonical slug
        canonical_slug = _resolve_template_slug(page)
        
        if not canonical_slug:
            # Get available templates for 404 response
            available_templates = _get_available_templates()
            return jsonify({
                'error': 'Page not found',
                'message': f'Template for "{page}" not found',
                'available_templates': available_templates
            }), 404
        
        # Render the canonical template
        template_path = f'ui/{canonical_slug}.html'
        return render_template(template_path)
        
    except Exception as e:
        logger.error(f"Error serving UI page {page}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to serve page'
        }), 500

@bp.route('/preview/<project_id>')
@require_auth
def preview_by_project(project_id):
    """Project-specific preview index"""
    try:
        available_pages = _get_project_pages(project_id)
        
        return render_template('ui/preview_index.html',
                             project_id=project_id,
                             available_pages=available_pages)
        
    except Exception as e:
        logger.error(f"Error serving project preview {project_id}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to serve project preview'
        }), 500

@bp.route('/preview')
@require_auth
def preview_index():
    """General preview index"""
    try:
        available_pages = _get_available_templates()
        
        return render_template('ui/preview_index.html',
                             project_id=None,
                             available_pages=available_pages)
        
    except Exception as e:
        logger.error(f"Error serving preview index: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to serve preview index'
        }), 500

# Dynamic CRUD endpoints for database tables (register these BEFORE the general API endpoint)
@bp.route('/api/<table_name>', methods=['GET'])
@require_auth
def get_table_rows(table_name):
    """Get all rows from a table"""
    try:
        from .builder_api import generated_tables
        from .db import get_db, select_all
        
        if table_name not in generated_tables:
            return jsonify({
                'error': 'Table not found',
                'message': f'No table found for {table_name}'
            }), 404
        
        db = get_db()
        rows = select_all(db, table_name)
        return jsonify(rows)
        
    except Exception as e:
        logger.error(f"Error getting rows from table {table_name}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to get table rows'
        }), 500

@bp.route('/api/<table_name>', methods=['POST'])
@require_auth
def create_table_row(table_name):
    """Create a new row in a table"""
    try:
        from .builder_api import generated_tables
        from .db import get_db, insert_row
        
        if table_name not in generated_tables:
            return jsonify({
                'error': 'Table not found',
                'message': f'No table found for {table_name}'
            }), 404
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Invalid JSON payload',
                'message': 'Request body must be valid JSON'
            }), 422
        
        # Get insertable columns
        table_info = generated_tables[table_name]
        allowed_columns = table_info['insertable_columns']
        
        # Insert the row
        db = get_db()
        row_id = insert_row(db, table_name, data, allowed_columns)
        
        if row_id is None:
            return jsonify({
                'error': 'Insert failed',
                'message': 'Failed to insert row into table'
            }), 500
        
        return jsonify({
            'ok': True,
            'id': row_id
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating row in table {table_name}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to create table row'
        }), 500

# Dynamic API endpoints (register these AFTER the table-specific routes)
@bp.route('/api/<slug>')
@require_auth
def dynamic_api(slug):
    """Serve dynamic API endpoints generated by the builder"""
    try:
        # Import the generated_apis from builder_api
        from .builder_api import generated_apis
        
        endpoint_route = f'/api/{slug}'
        if endpoint_route in generated_apis:
            api_data = generated_apis[endpoint_route]
            return jsonify(api_data['response'])
        else:
            return jsonify({
                'error': 'API endpoint not found',
                'message': f'No API found for {endpoint_route}'
            }), 404
            
    except Exception as e:
        logger.error(f"Error serving API endpoint {slug}: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to serve API endpoint'
        }), 500

# Route aliases for custom routes
# These serve the canonical template for the route
@bp.route('/builder')
@require_auth
def builder_alias():
    """Alias for /builder -> /ui/build"""
    return ui_page('build')

@bp.route('/tasks')
@require_auth
def tasks_alias():
    """Alias for /tasks -> /ui/tasks"""
    return ui_page('tasks')

@bp.route('/dashboard')
@require_auth
def dashboard_alias():
    """Alias for /dashboard -> /ui/dashboard"""
    return ui_page('dashboard')

@bp.route('/home')
@require_auth
def home_alias():
    """Alias for /home -> /ui/home"""
    return ui_page('home')

@bp.route('/about')
@require_auth
def about_alias():
    """Alias for /about -> /ui/about"""
    return ui_page('about')
