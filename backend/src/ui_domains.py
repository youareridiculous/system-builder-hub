"""
Custom domains UI routes
"""
from flask import Blueprint, render_template, request, redirect, url_for
from src.auth_api import require_auth
from src.tenancy.decorators import require_tenant

bp = Blueprint('ui_domains', __name__)

@bp.route('/ui/domains')
@require_auth
@require_tenant()
def domains_page():
    """Custom domains management page"""
    return render_template('ui/domains.html')
