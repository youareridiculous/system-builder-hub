"""
CRM/Ops API router
"""
from flask import Blueprint
from src.crm_ops.api.contacts import bp as contacts_bp
from src.crm_ops.api.deals import bp as deals_bp
from src.crm_ops.api.activities import bp as activities_bp
from src.crm_ops.api.projects import bp as projects_bp
from src.crm_ops.api.tasks import bp as tasks_bp
from src.crm_ops.api.messages import bp as messages_bp
from src.crm_ops.api.analytics import bp as analytics_bp
from src.crm_ops.api.admin import bp as admin_bp

def register_crm_ops_blueprints(app):
    """Register all CRM/Ops API blueprints"""
    app.register_blueprint(contacts_bp)
    app.register_blueprint(deals_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(admin_bp)
