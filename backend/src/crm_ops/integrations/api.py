"""
Integrations API for CRM/Ops Template
"""
import logging
from typing import Dict, Any
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Role
from src.tenancy.context import get_current_tenant_id
from src.crm_ops.integrations.slack_service import SlackService
from src.crm_ops.integrations.zapier_service import ZapierService
from src.crm_ops.integrations.import_service import ImportService
from src.crm_ops.integrations.google_drive_service import GoogleDriveService
from src.crm_ops.integrations.models import (
    SlackIntegration, ZapierIntegration, SalesforceIntegration, 
    HubSpotIntegration, GoogleDriveIntegration, IntegrationSync
)
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, handle_api_errors
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

bp = Blueprint('integrations', __name__, url_prefix='/api/integrations')

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

class IntegrationsAPI(CRMOpsAPIBase):
    """Integrations API implementation"""
    
    def __init__(self):
        super().__init__(None, 'integration')
        self.slack_service = SlackService()
        self.zapier_service = ZapierService()
        self.import_service = ImportService()
        self.google_drive_service = GoogleDriveService()
    
    @handle_api_errors
    def get_integrations(self) -> tuple:
        """Get all integrations for tenant"""
        tenant_id = get_current_tenant_id()
        
        with db_session() as session:
            # Get all integration types
            slack_integrations = session.query(SlackIntegration).filter(
                SlackIntegration.tenant_id == tenant_id
            ).all()
            
            zapier_integrations = session.query(ZapierIntegration).filter(
                ZapierIntegration.tenant_id == tenant_id
            ).all()
            
            salesforce_integrations = session.query(SalesforceIntegration).filter(
                SalesforceIntegration.tenant_id == tenant_id
            ).all()
            
            hubspot_integrations = session.query(HubSpotIntegration).filter(
                HubSpotIntegration.tenant_id == tenant_id
            ).all()
            
            google_drive_integrations = session.query(GoogleDriveIntegration).filter(
                GoogleDriveIntegration.tenant_id == tenant_id
            ).all()
            
            return jsonify({
                'data': {
                    'type': 'integrations',
                    'attributes': {
                        'slack': [integration.to_dict() for integration in slack_integrations],
                        'zapier': [integration.to_dict() for integration in zapier_integrations],
                        'salesforce': [integration.to_dict() for integration in salesforce_integrations],
                        'hubspot': [integration.to_dict() for integration in hubspot_integrations],
                        'google_drive': [integration.to_dict() for integration in google_drive_integrations]
                    }
                }
            }), 200
    
    @handle_api_errors
    @limiter.limit("50 per minute")
    def handle_slack_webhook(self) -> tuple:
        """Handle Slack webhook events"""
        tenant_id = get_current_tenant_id()
        
        # Verify Slack request
        if not self.slack_service.verify_slack_request(request.get_data(as_text=True), dict(request.headers)):
            raise CRMOpsAPIError("Invalid Slack request signature", 401, "INVALID_SIGNATURE")
        
        data = request.get_json()
        
        if data.get('type') == 'url_verification':
            # Handle Slack URL verification
            return jsonify({'challenge': data.get('challenge')}), 200
        
        elif data.get('type') == 'event_callback':
            # Handle Slack event
            event = data.get('event', {})
            event_type = event.get('type')
            
            if event_type == 'app_mention':
                # Handle app mention
                response = self.slack_service.handle_app_mention(tenant_id, event)
                return jsonify(response), 200
            
            elif event_type == 'message':
                # Handle message event
                response = self.slack_service.handle_message_event(tenant_id, event)
                return jsonify(response), 200
        
        return jsonify({'status': 'ok'}), 200
    
    @handle_api_errors
    @limiter.limit("50 per minute")
    def handle_slack_slash_command(self) -> tuple:
        """Handle Slack slash commands"""
        tenant_id = get_current_tenant_id()
        
        # Verify Slack request
        if not self.slack_service.verify_slack_request(request.get_data(as_text=True), dict(request.headers)):
            raise CRMOpsAPIError("Invalid Slack request signature", 401, "INVALID_SIGNATURE")
        
        form_data = request.form
        command = form_data.get('command')
        text = form_data.get('text', '')
        user_id = form_data.get('user_id')
        channel_id = form_data.get('channel_id')
        
        response = self.slack_service.handle_slash_command(tenant_id, command, text, user_id, channel_id)
        return jsonify(response), 200
    
    @handle_api_errors
    @limiter.limit("50 per minute")
    def handle_slack_interactive(self) -> tuple:
        """Handle Slack interactive messages"""
        tenant_id = get_current_tenant_id()
        
        # Verify Slack request
        if not self.slack_service.verify_slack_request(request.get_data(as_text=True), dict(request.headers)):
            raise CRMOpsAPIError("Invalid Slack request signature", 401, "INVALID_SIGNATURE")
        
        form_data = request.form
        payload = eval(form_data.get('payload', '{}'))  # In production, use proper JSON parsing
        
        response = self.slack_service.handle_interactive_message(tenant_id, payload)
        return jsonify(response), 200
    
    @handle_api_errors
    @limiter.limit("30 per minute")
    def handle_zapier_webhook(self) -> tuple:
        """Handle Zapier webhook"""
        # Validate API key
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            raise CRMOpsAPIError("API key required", 401, "MISSING_API_KEY")
        
        integration = self.zapier_service.validate_api_key(api_key)
        if not integration:
            raise CRMOpsAPIError("Invalid API key", 401, "INVALID_API_KEY")
        
        data = request.get_json()
        action_type = data.get('action_type')
        
        if not action_type:
            raise ValidationError("action_type is required", "action_type")
        
        result = self.zapier_service.handle_zapier_action(integration, action_type, data.get('data', {}))
        return jsonify(result), 200
    
    @handle_api_errors
    def get_zapier_triggers(self) -> tuple:
        """Get available Zapier triggers"""
        triggers = self.zapier_service.get_available_triggers()
        
        return jsonify({
            'data': {
                'type': 'zapier_triggers',
                'attributes': {
                    'triggers': triggers
                }
            }
        }), 200
    
    @handle_api_errors
    def get_zapier_actions(self) -> tuple:
        """Get available Zapier actions"""
        actions = self.zapier_service.get_available_actions()
        
        return jsonify({
            'data': {
                'type': 'zapier_actions',
                'attributes': {
                    'actions': actions
                }
            }
        }), 200
    
    @handle_api_errors
    @limiter.limit("10 per minute")
    def import_from_salesforce(self) -> tuple:
        """Import data from Salesforce"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        integration_id = data.get('integration_id')
        entity_types = data.get('entity_types', ['contacts', 'leads', 'opportunities'])
        
        if not integration_id:
            raise ValidationError("integration_id is required", "integration_id")
        
        try:
            sync = self.import_service.import_from_salesforce(tenant_id, integration_id, entity_types)
            
            # Log audit event
            self.log_audit_event('import', str(sync.id), new_values={
                'integration_type': 'salesforce',
                'entity_types': entity_types,
                'records_processed': sync.records_processed
            })
            
            return jsonify({
                'data': {
                    'id': str(sync.id),
                    'type': 'integration_sync',
                    'attributes': sync.to_dict()
                }
            }), 201
            
        except Exception as e:
            logger.error(f"Error importing from Salesforce: {e}")
            raise CRMOpsAPIError("Failed to import from Salesforce", 500, "IMPORT_ERROR")
    
    @handle_api_errors
    @limiter.limit("10 per minute")
    def import_from_hubspot(self) -> tuple:
        """Import data from HubSpot"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        integration_id = data.get('integration_id')
        entity_types = data.get('entity_types', ['contacts', 'companies', 'deals'])
        
        if not integration_id:
            raise ValidationError("integration_id is required", "integration_id")
        
        try:
            sync = self.import_service.import_from_hubspot(tenant_id, integration_id, entity_types)
            
            # Log audit event
            self.log_audit_event('import', str(sync.id), new_values={
                'integration_type': 'hubspot',
                'entity_types': entity_types,
                'records_processed': sync.records_processed
            })
            
            return jsonify({
                'data': {
                    'id': str(sync.id),
                    'type': 'integration_sync',
                    'attributes': sync.to_dict()
                }
            }), 201
            
        except Exception as e:
            logger.error(f"Error importing from HubSpot: {e}")
            raise CRMOpsAPIError("Failed to import from HubSpot", 500, "IMPORT_ERROR")
    
    @handle_api_errors
    def get_google_drive_files(self) -> tuple:
        """Get Google Drive files"""
        tenant_id = get_current_tenant_id()
        folder_id = request.args.get('folder_id')
        query = request.args.get('query')
        
        files = self.google_drive_service.list_files(tenant_id, folder_id, query)
        
        return jsonify({
            'data': {
                'type': 'google_drive_files',
                'attributes': {
                    'files': files
                }
            }
        }), 200
    
    @handle_api_errors
    def attach_google_drive_file(self) -> tuple:
        """Attach Google Drive file to entity"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        entity_type = data.get('entity_type')
        entity_id = data.get('entity_id')
        file_id = data.get('file_id')
        
        if not all([entity_type, entity_id, file_id]):
            raise ValidationError("entity_type, entity_id, and file_id are required")
        
        attachment = self.google_drive_service.attach_file_to_entity(
            tenant_id, entity_type, entity_id, file_id, user_id
        )
        
        if not attachment:
            raise CRMOpsAPIError("Failed to attach file", 500, "ATTACHMENT_ERROR")
        
        return jsonify({
            'data': {
                'id': str(attachment.id),
                'type': 'file_attachment',
                'attributes': attachment.to_dict()
            }
        }), 201
    
    @handle_api_errors
    def get_entity_attachments(self, entity_type: str, entity_id: str) -> tuple:
        """Get file attachments for entity"""
        tenant_id = get_current_tenant_id()
        
        attachments = self.google_drive_service.get_entity_attachments(tenant_id, entity_type, entity_id)
        
        return jsonify({
            'data': [
                {
                    'id': str(attachment.id),
                    'type': 'file_attachment',
                    'attributes': attachment.to_dict()
                }
                for attachment in attachments
            ]
        }), 200
    
    @handle_api_errors
    def remove_attachment(self, attachment_id: str) -> tuple:
        """Remove file attachment"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        success = self.google_drive_service.remove_attachment(tenant_id, attachment_id, user_id)
        
        if not success:
            raise CRMOpsAPIError("Failed to remove attachment", 500, "REMOVAL_ERROR")
        
        return jsonify({
            'data': {
                'type': 'file_attachment',
                'attributes': {
                    'removed': True,
                    'attachment_id': attachment_id
                }
            }
        }), 200
    
    @handle_api_errors
    def get_sync_history(self) -> tuple:
        """Get integration sync history"""
        tenant_id = get_current_tenant_id()
        integration_type = request.args.get('integration_type')
        limit = int(request.args.get('limit', 50))
        
        with db_session() as session:
            query = session.query(IntegrationSync).filter(
                IntegrationSync.tenant_id == tenant_id
            )
            
            if integration_type:
                query = query.filter(IntegrationSync.integration_type == integration_type)
            
            syncs = query.order_by(IntegrationSync.started_at.desc()).limit(limit).all()
            
            return jsonify({
                'data': [
                    {
                        'id': str(sync.id),
                        'type': 'integration_sync',
                        'attributes': sync.to_dict()
                    }
                    for sync in syncs
                ]
            }), 200

# Initialize API
integrations_api = IntegrationsAPI()

# Route handlers
@bp.route('', methods=['GET'])
@require_tenant_context
def get_integrations():
    """Get all integrations"""
    return integrations_api.get_integrations()

# Slack routes
@bp.route('/slack/webhook', methods=['POST'])
def handle_slack_webhook():
    """Handle Slack webhook"""
    return integrations_api.handle_slack_webhook()

@bp.route('/slack/command', methods=['POST'])
def handle_slack_slash_command():
    """Handle Slack slash command"""
    return integrations_api.handle_slack_slash_command()

@bp.route('/slack/interactive', methods=['POST'])
def handle_slack_interactive():
    """Handle Slack interactive message"""
    return integrations_api.handle_slack_interactive()

# Zapier routes
@bp.route('/zapier/webhook', methods=['POST'])
def handle_zapier_webhook():
    """Handle Zapier webhook"""
    return integrations_api.handle_zapier_webhook()

@bp.route('/zapier/triggers', methods=['GET'])
def get_zapier_triggers():
    """Get Zapier triggers"""
    return integrations_api.get_zapier_triggers()

@bp.route('/zapier/actions', methods=['GET'])
def get_zapier_actions():
    """Get Zapier actions"""
    return integrations_api.get_zapier_actions()

# Import routes
@bp.route('/import/salesforce', methods=['POST'])
@require_tenant_context
@require_role(Role.ADMIN)
def import_from_salesforce():
    """Import from Salesforce"""
    return integrations_api.import_from_salesforce()

@bp.route('/import/hubspot', methods=['POST'])
@require_tenant_context
@require_role(Role.ADMIN)
def import_from_hubspot():
    """Import from HubSpot"""
    return integrations_api.import_from_hubspot()

# Google Drive routes
@bp.route('/google-drive/files', methods=['GET'])
@require_tenant_context
def get_google_drive_files():
    """Get Google Drive files"""
    return integrations_api.get_google_drive_files()

@bp.route('/google-drive/attach', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def attach_google_drive_file():
    """Attach Google Drive file"""
    return integrations_api.attach_google_drive_file()

@bp.route('/attachments/<entity_type>/<entity_id>', methods=['GET'])
@require_tenant_context
def get_entity_attachments(entity_type, entity_id):
    """Get entity attachments"""
    return integrations_api.get_entity_attachments(entity_type, entity_id)

@bp.route('/attachments/<attachment_id>', methods=['DELETE'])
@require_tenant_context
@require_role(Role.MEMBER)
def remove_attachment(attachment_id):
    """Remove attachment"""
    return integrations_api.remove_attachment(attachment_id)

# Sync history
@bp.route('/sync/history', methods=['GET'])
@require_tenant_context
def get_sync_history():
    """Get sync history"""
    return integrations_api.get_sync_history()
