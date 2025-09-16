"""
UI Blueprint - Lightweight UI routes for all SBH features
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from functools import wraps
import logging

from features_catalog import get_feature_by_slug, get_features_for_role
from security import require_auth, require_role

logger = logging.getLogger(__name__)

ui_bp = Blueprint('ui', __name__, url_prefix='/ui')


def check_feature_access(feature_slug: str):
    """Decorator to check feature access based on role and feature flags"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get current user role (mock for now)
            current_role = request.args.get('role', 'developer')  # In real app, get from JWT
            
            # Get feature from catalog
            feature = get_feature_by_slug(feature_slug)
            if not feature:
                return render_template('unavailable.html', 
                                     reason="Feature not found",
                                     feature_slug=feature_slug), 404
            
            # Check role access
            if current_role not in feature.roles:
                return render_template('unavailable.html',
                                     reason=f"Access denied for role '{current_role}'",
                                     feature_slug=feature_slug), 200
            
            # Check feature flag (simplified for now)
            if feature.flag:
                # For now, assume all feature flags are enabled
                # In production, this would check the actual feature flag
                pass
            
            # Emit telemetry
            logger.info(f"Feature accessed: {feature_slug}, role: {current_role}, allowed: True, flag_on: True")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Hero Features
@ui_bp.route('/build')
@check_feature_access('start-build')
def build():
    """Start a Build - Prompt console/visual builder entry"""
    return render_template('ui/build.html', title="Start a Build")


@ui_bp.route('/preview')
@check_feature_access('open-preview')
def preview():
    """Open Preview - System preview environment"""
    return render_template('ui/preview.html', title="Open Preview")


@ui_bp.route('/brain')
@check_feature_access('create-brain')
def brain():
    """Create Brain - AI agent creation"""
    return render_template('ui/brain.html', title="Create Brain")


# Core Features
@ui_bp.route('/project-loader')
@check_feature_access('project-loader')
def project_loader():
    """Project Loader - Load and analyze existing projects"""
    return render_template('ui/project_loader.html', title="Project Loader")


@ui_bp.route('/visual-builder')
@check_feature_access('visual-builder')
def visual_builder():
    """Visual Builder - Drag-and-drop system creation"""
    return render_template('ui/visual_builder.html', title="Visual Builder")


@ui_bp.route('/autonomous-builder')
@check_feature_access('autonomous-builder')
def autonomous_builder():
    """Autonomous Builder - Continuous build loops"""
    return render_template('ui/autonomous_builder.html', title="Autonomous Builder")


@ui_bp.route('/template-launcher')
@check_feature_access('template-launcher')
def template_launcher():
    """Template Launcher - Launch system templates"""
    return render_template('ui/template_launcher.html', title="Template Launcher")


@ui_bp.route('/system-delivery')
@check_feature_access('system-delivery')
def system_delivery():
    """System Delivery - Automated deployment pipeline"""
    return render_template('ui/system_delivery.html', title="System Delivery")


# Intelligence Features
@ui_bp.route('/fastpath-agent')
@check_feature_access('fastpath-agent')
def fastpath_agent():
    """FastPath Agent - Intelligent build optimization"""
    return render_template('ui/fastpath_agent.html', title="FastPath Agent")


@ui_bp.route('/agent-ecosystem')
@check_feature_access('agent-ecosystem')
def agent_ecosystem():
    """Agent Ecosystem - Multi-agent collaboration"""
    return render_template('ui/agent_ecosystem.html', title="Agent Ecosystem")


@ui_bp.route('/agent-training')
@check_feature_access('agent-training')
def agent_training():
    """Agent Training - Train AI agents"""
    return render_template('ui/agent_training.html', title="Agent Training")


@ui_bp.route('/predictive-dashboard')
@check_feature_access('predictive-dashboard')
def predictive_dashboard():
    """Predictive Intelligence - AI-powered insights"""
    return render_template('ui/predictive_dashboard.html', title="Predictive Intelligence")


@ui_bp.route('/growth-agent')
@check_feature_access('growth-agent')
def growth_agent():
    """Growth Agent - AI-powered growth experiments"""
    return render_template('ui/growth_agent.html', title="Growth Agent")


# Data Features
@ui_bp.route('/data-refinery')
@check_feature_access('data-refinery')
def data_refinery():
    """Data Refinery - Process and transform data"""
    return render_template('ui/data_refinery.html', title="Data Refinery")


@ui_bp.route('/memory-upload')
@check_feature_access('memory-upload')
def memory_upload():
    """Memory Upload - Upload system memory files"""
    return render_template('ui/memory_upload.html', title="Memory Upload")


@ui_bp.route('/quality-gates')
@check_feature_access('quality-gates')
def quality_gates():
    """Quality Gates - Automated quality assurance"""
    return render_template('ui/quality_gates.html', title="Quality Gates")


# Business Features
@ui_bp.route('/gtm')
@check_feature_access('gtm-engine')
def gtm():
    """GTM Engine - Go-to-market automation"""
    return render_template('ui/gtm.html', title="GTM Engine")


@ui_bp.route('/investor')
@check_feature_access('investor-pack')
def investor():
    """Investor Pack - Investment-ready documentation"""
    return render_template('ui/investor.html', title="Investor Pack")


@ui_bp.route('/access-hub')
@check_feature_access('access-hub')
def access_hub():
    """Access Hub - User access management"""
    return render_template('ui/access_hub.html', title="Access Hub")


# Feature Router
@ui_bp.route('/feature/<slug>')
def feature_router(slug):
    """Route /feature/<slug> to the proper /ui/... route"""
    feature = get_feature_by_slug(slug)
    if not feature:
        return render_template('unavailable.html', 
                             reason="Feature not found",
                             feature_slug=slug), 404
    
    # Redirect to the canonical route
    return redirect(feature.route, code=302)


# Features Catalog API
@ui_bp.route('/api/features/catalog')
def features_catalog():
    """Get filtered features catalog"""
    role = request.args.get('role', 'developer')
    category = request.args.get('category')
    search_query = request.args.get('q')
    
    features = get_features_for_role(role, category, search_query)
    
    # Convert to JSON-serializable format
    features_data = []
    for feature in features:
        features_data.append({
            'slug': feature.slug,
            'title': feature.title,
            'category': feature.category,
            'route': feature.route,
            'roles': feature.roles,
            'flag': feature.flag,
            'status': feature.status,
            'description': feature.description,
            'icon': feature.icon
        })
    
    return jsonify({
        'features': features_data,
        'total': len(features_data),
        'role': role,
        'category': category,
        'search_query': search_query
    })
