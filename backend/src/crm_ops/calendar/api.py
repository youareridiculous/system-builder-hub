"""
Calendar API for CRM/Ops Template
"""
import logging
from datetime import datetime
from typing import Dict, Any
from flask import Blueprint, request, jsonify, g, send_file
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Role
from src.tenancy.context import get_current_tenant_id
from src.crm_ops.calendar.models import CalendarEvent, CalendarInvitation
from src.crm_ops.calendar.service import CalendarService
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, handle_api_errors
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import io

logger = logging.getLogger(__name__)

bp = Blueprint('calendar', __name__, url_prefix='/api/calendar')

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

class CalendarAPI(CRMOpsAPIBase):
    """Calendar API implementation"""
    
    def __init__(self):
        super().__init__(None, 'calendar')
        self.service = CalendarService()
    
    @handle_api_errors
    def get_events(self) -> tuple:
        """Get calendar events"""
        tenant_id = get_current_tenant_id()
        
        # Get date range from query params
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        
        if not from_date or not to_date:
            raise ValidationError("from and to date parameters are required")
        
        try:
            start_date = datetime.fromisoformat(from_date)
            end_date = datetime.fromisoformat(to_date)
        except ValueError:
            raise ValidationError("Invalid date format. Use ISO format (YYYY-MM-DD)")
        
        events = self.service.get_events(tenant_id, start_date, end_date)
        
        return jsonify({
            'data': [
                {
                    'id': str(event.id),
                    'type': 'calendar_event',
                    'attributes': event.to_dict()
                }
                for event in events
            ]
        }), 200
    
    @handle_api_errors
    @limiter.limit("20 per minute")
    def create_event(self) -> tuple:
        """Create calendar event"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate required fields
        if not data.get('title'):
            raise ValidationError("Title is required", "title")
        if not data.get('start_time'):
            raise ValidationError("Start time is required", "start_time")
        if not data.get('end_time'):
            raise ValidationError("End time is required", "end_time")
        
        try:
            event = self.service.create_event(tenant_id, user_id, data)
            
            # Log audit event
            self.log_audit_event('create', str(event.id), new_values={
                'title': event.title,
                'start_time': event.start_time.isoformat()
            })
            
            return jsonify({
                'data': {
                    'id': str(event.id),
                    'type': 'calendar_event',
                    'attributes': event.to_dict()
                }
            }), 201
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            raise CRMOpsAPIError("Failed to create event", 500, "EVENT_CREATE_ERROR")
    
    @handle_api_errors
    @limiter.limit("20 per minute")
    def update_event(self, event_id: str) -> tuple:
        """Update calendar event"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        try:
            event = self.service.update_event(event_id, tenant_id, data)
            
            # Log audit event
            self.log_audit_event('update', str(event.id), new_values=data)
            
            return jsonify({
                'data': {
                    'id': str(event.id),
                    'type': 'calendar_event',
                    'attributes': event.to_dict()
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error updating event: {e}")
            raise CRMOpsAPIError("Failed to update event", 500, "EVENT_UPDATE_ERROR")
    
    @handle_api_errors
    def delete_event(self, event_id: str) -> tuple:
        """Delete calendar event"""
        tenant_id = get_current_tenant_id()
        
        try:
            success = self.service.delete_event(event_id, tenant_id)
            
            if not success:
                raise CRMOpsAPIError("Event not found", 404, "EVENT_NOT_FOUND")
            
            # Log audit event
            self.log_audit_event('delete', event_id)
            
            return jsonify({
                'data': {
                    'type': 'calendar_event',
                    'attributes': {
                        'deleted': True,
                        'event_id': event_id
                    }
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            raise CRMOpsAPIError("Failed to delete event", 500, "EVENT_DELETE_ERROR")
    
    @handle_api_errors
    @limiter.limit("10 per minute")
    def send_invitation(self, event_id: str) -> tuple:
        """Send calendar invitation"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        attendee_email = data.get('attendee_email')
        attendee_name = data.get('attendee_name')
        
        if not attendee_email:
            raise ValidationError("attendee_email is required")
        
        try:
            success = self.service.send_invitation(event_id, tenant_id, attendee_email, attendee_name)
            
            if not success:
                raise CRMOpsAPIError("Event not found", 404, "EVENT_NOT_FOUND")
            
            # Log audit event
            self.log_audit_event('create', event_id, new_values={
                'action': 'send_invitation',
                'attendee_email': attendee_email
            })
            
            return jsonify({
                'data': {
                    'type': 'calendar_invitation',
                    'attributes': {
                        'sent': success,
                        'attendee_email': attendee_email
                    }
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error sending invitation: {e}")
            raise CRMOpsAPIError("Failed to send invitation", 500, "INVITATION_ERROR")
    
    @handle_api_errors
    @limiter.limit("5 per minute")
    def import_ics(self) -> tuple:
        """Import events from ICS file"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        if 'file' not in request.files:
            raise ValidationError("No file provided", "file")
        
        file = request.files['file']
        if file.filename == '':
            raise ValidationError("No file selected", "file")
        
        if not file.filename.lower().endswith('.ics'):
            raise ValidationError("File must be an ICS file", "file")
        
        try:
            ics_content = file.read().decode('utf-8')
            events = self.service.import_ics(tenant_id, user_id, ics_content)
            
            # Log audit event
            self.log_audit_event('create', 'ics_import', new_values={
                'events_imported': len(events)
            })
            
            return jsonify({
                'data': {
                    'type': 'ics_import',
                    'attributes': {
                        'events_imported': len(events),
                        'events': [
                            {
                                'id': str(event.id),
                                'title': event.title
                            }
                            for event in events
                        ]
                    }
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error importing ICS: {e}")
            raise CRMOpsAPIError("Failed to import ICS file", 500, "ICS_IMPORT_ERROR")
    
    @handle_api_errors
    @limiter.limit("5 per minute")
    def export_ics(self) -> tuple:
        """Export events to ICS format"""
        tenant_id = get_current_tenant_id()
        
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        
        if not from_date or not to_date:
            raise ValidationError("from and to date parameters are required")
        
        try:
            start_date = datetime.fromisoformat(from_date)
            end_date = datetime.fromisoformat(to_date)
        except ValueError:
            raise ValidationError("Invalid date format. Use ISO format (YYYY-MM-DD)")
        
        try:
            ics_content = self.service.export_ics(tenant_id, start_date, end_date)
            
            # Create file response
            output = io.StringIO()
            output.write(ics_content)
            output.seek(0)
            
            # Log audit event
            self.log_audit_event('read', 'ics_export', new_values={
                'from_date': from_date,
                'to_date': to_date
            })
            
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/calendar',
                as_attachment=True,
                download_name=f'calendar_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.ics'
            )
            
        except Exception as e:
            logger.error(f"Error exporting ICS: {e}")
            raise CRMOpsAPIError("Failed to export ICS", 500, "ICS_EXPORT_ERROR")

# Initialize API
calendar_api = CalendarAPI()

# Route handlers
@bp.route('/events', methods=['GET'])
@require_tenant_context
def get_events():
    """Get calendar events"""
    return calendar_api.get_events()

@bp.route('/events', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def create_event():
    """Create calendar event"""
    return calendar_api.create_event()

@bp.route('/events/<event_id>', methods=['PUT'])
@require_tenant_context
@require_role(Role.MEMBER)
def update_event(event_id):
    """Update calendar event"""
    return calendar_api.update_event(event_id)

@bp.route('/events/<event_id>', methods=['DELETE'])
@require_tenant_context
@require_role(Role.MEMBER)
def delete_event(event_id):
    """Delete calendar event"""
    return calendar_api.delete_event(event_id)

@bp.route('/events/<event_id>/invite', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def send_invitation(event_id):
    """Send calendar invitation"""
    return calendar_api.send_invitation(event_id)

@bp.route('/import', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def import_ics():
    """Import ICS file"""
    return calendar_api.import_ics()

@bp.route('/export.ics', methods=['GET'])
@require_tenant_context
def export_ics():
    """Export ICS file"""
    return calendar_api.export_ics()
