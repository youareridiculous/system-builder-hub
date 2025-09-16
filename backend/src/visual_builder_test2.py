#!/usr/bin/env python3
"""
Test visual builder with decorators
"""

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from feature_flags import flag_required
from multi_tenancy import require_tenant_context
from idempotency import idempotent
from costs import cost_accounted

# Create blueprint
visual_builder_test2_bp = Blueprint('visual_builder_test2', __name__, url_prefix='/api/v1/visual-builder-test2')

@visual_builder_test2_bp.route('/project', methods=['POST'])
@cross_origin()
@flag_required('visual_builder')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_project():
    """Create a new builder project"""
    return jsonify({'status': 'ok'})
