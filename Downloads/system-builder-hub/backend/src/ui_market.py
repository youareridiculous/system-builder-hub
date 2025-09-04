"""
Marketplace UI routes
"""
from flask import Blueprint, render_template, request, redirect, url_for
from src.auth_api import require_auth
from src.tenancy.decorators import require_tenant

bp = Blueprint('ui_market', __name__)

@bp.route('/ui/market')
@require_auth
@require_tenant()
def market_page():
    """Marketplace page"""
    return render_template('ui/market.html')

@bp.route('/ui/market/my')
@require_auth
@require_tenant()
def manage_templates_page():
    """Template management page (admin only)"""
    return render_template('ui/market_manage.html')
