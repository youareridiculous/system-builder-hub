"""
LLM UI routes
"""
from flask import Blueprint, render_template, request, redirect, url_for
from src.auth_api import require_auth
from src.tenancy.decorators import require_tenant

bp = Blueprint('ui_llm', __name__)

@bp.route('/ui/llm')
@require_auth
@require_tenant()
def llm_playground():
    """LLM playground page"""
    return render_template('ui/llm.html')

@bp.route('/ui/llm/evals')
@require_auth
@require_tenant()
def llm_evals():
    """LLM evaluations page (admin only)"""
    return render_template('ui/llm_evals.html')
