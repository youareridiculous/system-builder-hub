#!/usr/bin/env python3
"""
Test visual builder with minimal routes
"""

from flask import Blueprint, request, jsonify

# Create blueprint
visual_builder_test_bp = Blueprint('visual_builder_test', __name__, url_prefix='/api/v1/visual-builder-test')

@visual_builder_test_bp.route('/test', methods=['GET'])
def test_route():
    """Test route"""
    return jsonify({'status': 'ok'})
