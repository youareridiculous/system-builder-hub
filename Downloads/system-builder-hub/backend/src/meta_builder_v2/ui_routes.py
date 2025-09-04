"""
Meta-Builder v2 UI Routes
Portal pages for the Meta-Builder v2 interface.
"""

import logging
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_cors import cross_origin

from src.tenancy.context import get_current_tenant_id
from src.tenancy.decorators import require_tenant
from src.auth_api import require_auth
from src.auth_api import get_current_user

logger = logging.getLogger(__name__)

# Create blueprint
meta_builder_v2_ui = Blueprint('meta_builder_v2_ui', __name__, url_prefix='/meta-builder/v2')


@meta_builder_v2_ui.route('/')
@cross_origin()
@require_auth
@require_tenant()
def dashboard():
    """Meta-Builder v2 Dashboard."""
    return render_template('meta_builder_v2/dashboard.html')


@meta_builder_v2_ui.route('/composer')
@cross_origin()
@require_auth
@require_tenant()
def composer():
    """Specification Composer."""
    return render_template('meta_builder_v2/composer.html')


@meta_builder_v2_ui.route('/runs')
@cross_origin()
@require_auth
@require_tenant()
def runs():
    """Runs Console."""
    return render_template('meta_builder_v2/runs.html')


@meta_builder_v2_ui.route('/runs/<run_id>')
@cross_origin()
@require_auth
@require_tenant()
def run_detail(run_id):
    """Run Detail View."""
    return render_template('meta_builder_v2/run_detail.html', run_id=run_id)


@meta_builder_v2_ui.route('/history')
@cross_origin()
@require_auth
@require_tenant()
def history():
    """History and Analytics."""
    return render_template('meta_builder_v2/history.html')
