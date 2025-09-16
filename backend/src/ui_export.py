"""
Export UI routes
"""
from flask import Blueprint, render_template, request, redirect, url_for
from src.auth_api import require_auth
from src.tenancy.decorators import require_tenant

bp = Blueprint('ui_export', __name__)

@bp.route('/ui/export')
@require_auth
@require_tenant()
def export_page():
    """Export page"""
    return render_template('ui/export.html')

@bp.route('/ui/project/<project_id>/export')
@require_auth
@require_tenant()
def project_export_page(project_id):
    """Project-specific export page"""
    return render_template('ui/export.html', project_id=project_id)
