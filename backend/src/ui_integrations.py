"""
Integrations UI routes
"""
from flask import Blueprint, render_template, request, redirect, url_for
from src.auth_api import require_auth
from src.tenancy.decorators import require_tenant

bp = Blueprint('ui_integrations', __name__)

@bp.route('/ui/integrations')
@require_auth
@require_tenant()
def integrations_page():
    """Integrations management page"""
    return render_template('ui/integrations.html')
