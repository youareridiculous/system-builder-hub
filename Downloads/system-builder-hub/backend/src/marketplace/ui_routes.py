"""
SBH Marketplace UI Routes
Flask routes for the marketplace UI.
"""

from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required
from src.utils.auth import require_role

bp = Blueprint('marketplace_ui', __name__, url_prefix='/ui/marketplace')


@bp.route('/')
@jwt_required()
@require_role(['member', 'admin', 'owner'])
def marketplace_portal():
    """Main marketplace portal page."""
    return render_template('marketplace/portal.html')


@bp.route('/template/<slug>')
@jwt_required()
@require_role(['member', 'admin', 'owner'])
def template_detail(slug: str):
    """Template detail page."""
    return render_template('marketplace/template_detail.html', slug=slug)


@bp.route('/launch/<slug>')
@jwt_required()
@require_role(['admin', 'owner'])
def launch_template(slug: str):
    """Template launch page."""
    return render_template('marketplace/launch.html', slug=slug)
