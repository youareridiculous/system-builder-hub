"""
Codegen agent UI routes
"""
from flask import Blueprint, render_template, request, redirect, url_for
from src.auth_api import require_auth
from src.tenancy.decorators import require_tenant

bp = Blueprint('ui_agent_codegen', __name__)

@bp.route('/ui/agent-codegen')
@require_auth
@require_tenant()
def agent_codegen():
    """Codegen agent page"""
    return render_template('ui/agent_codegen.html')
