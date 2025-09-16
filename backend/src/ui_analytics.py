"""
Analytics UI routes
"""
from flask import Blueprint, render_template, request, redirect, url_for
from src.auth_api import require_auth
from src.tenancy.decorators import require_tenant, tenant_admin

bp = Blueprint('ui_analytics', __name__)

@bp.route('/ui/analytics')
@require_auth
@require_tenant()
@tenant_admin()
def analytics_page():
    """Analytics dashboard page"""
    return render_template('ui/analytics.html')
