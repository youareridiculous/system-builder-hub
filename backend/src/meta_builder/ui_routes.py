"""
SBH Meta-Builder UI Routes
Flask routes for the meta-builder UI.
"""

from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required
from src.utils.auth import require_role

bp = Blueprint('meta_builder_ui', __name__, url_prefix='/ui/meta')


@bp.route('/scaffold')
@jwt_required()
@require_role(['member', 'admin', 'owner'])
def scaffold_composer():
    """Meta-Builder scaffold composer UI."""
    return render_template('meta_builder/scaffold_composer.html')


@bp.route('/patterns')
@jwt_required()
@require_role(['member', 'admin', 'owner'])
def patterns_browser():
    """Pattern library browser UI."""
    return render_template('meta_builder/patterns_browser.html')


@bp.route('/templates')
@jwt_required()
@require_role(['member', 'admin', 'owner'])
def templates_browser():
    """Template library browser UI."""
    return render_template('meta_builder/templates_browser.html')


@bp.route('/evaluations')
@jwt_required()
@require_role(['admin', 'owner'])
def evaluations_dashboard():
    """Evaluation dashboard UI."""
    return render_template('meta_builder/evaluations_dashboard.html')
