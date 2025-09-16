"""
UI Visual Builder Blueprint
"""
from flask import Blueprint, render_template, request, jsonify
import logging

logger = logging.getLogger(__name__)

# Create blueprint
ui_visual_builder_bp = Blueprint('ui_visual_builder', __name__, url_prefix='/ui/visual-builder')

@ui_visual_builder_bp.route('/')
def visual_builder():
    """Visual Builder main page"""
    return render_template('ui/visual_builder.html')
