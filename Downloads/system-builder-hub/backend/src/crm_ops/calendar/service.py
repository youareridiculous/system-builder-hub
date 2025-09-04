"""
Calendar service for CRM/Ops Template
"""
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.database import db_session
from src.crm_ops.calendar.models import CalendarEvent, CalendarInvitation
from src.crm_ops.mailer.service import EmailService
from src.config import get_config

logger = logging.getLogger(__name__)

class CalendarService:
    """Service for calendar operations"""
    
    def __init__(self):
        self.config = get_config()
        self.email_service = EmailService()
    
    def create_event(self, tenant_id: str, user_id: str, event_data: Dict[str, Any]) -> CalendarEvent:
        """Create a calendar event"""
        with db_session() as session:
            event = CalendarEvent(
                tenant_id=tenant_id,
                title=event_data['title'],
                description=event_data.get('description'),
                start_time=datetime.fromisoformat(event_data['start_time']),
                end_time=datetime.fromisoformat(event_data['end_time']),
                location=event_data.get('location'),
                attendees=event_data.get('attendees', []),
                organizer_email=event_data.get('organizer_email'),
                organizer_name=event_data.get('organizer_name'),
                related_contact_id=event_data.get('related_contact_id'),
                related_deal_id=event_data.get('related_deal_id'),
                is_all_day=event_data.get('is_all_day', False),
                created_by=user_id
            )
            
            session.add(event)
            session.commit()
            
            # Send invitations if attendees provided
            if event.attendees:
                self._send_invitations(session, event)
            
            return event
    
    def update_event(self, event_id: str, tenant_id: str, event_data: Dict[str, Any]) -> CalendarEvent:
        """Update a calendar event"""
        with db_session() as session:
            event = session.query(CalendarEvent).filter(
                CalendarEvent.id == event_id,
                CalendarEvent.tenant_id == tenant_id
            ).first()
            
            if not event:
                raise ValueError("Event not found")
            
            # Update fields
            if 'title' in event_data:
                event.title = event_data['title']
            if 'description' in event_data:
                event.description = event_data['description']
            if 'start_time' in event_data:
                event.start_time = datetime.fromisoformat(event_data['start_time'])
            if 'end_time' in event_data:
                event.end_time = datetime.fromisoformat(event_data['end_time'])
            if 'location' in event_data:
                event.location = event_data['location']
            if 'attendees' in event_data:
                event.attendees = event_data['attendees']
            if 'is_all_day' in event_data:
                event.is_all_day = event_data['is_all_day']
            
            session.commit()
            
            return event
    
    def delete_event(self, event_id: str, tenant_id: str) -> bool:
        """Delete a calendar event"""
        with db_session() as session:
            event = session.query(CalendarEvent).filter(
                CalendarEvent.id == event_id,
                CalendarEvent.tenant_id == tenant_id
            ).first()
            
            if not event:
                return False
            
            session.delete(event)
            session.commit()
            
            return True
    
    def get_events(self, tenant_id: str, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Get events for a date range"""
        with db_session() as session:
            events = session.query(CalendarEvent).filter(
                CalendarEvent.tenant_id == tenant_id,
                CalendarEvent.start_time >= start_date,
                CalendarEvent.start_time <= end_date
            ).order_by(CalendarEvent.start_time).all()
            
            return events
    
    def send_invitation(self, event_id: str, tenant_id: str, attendee_email: str, attendee_name: str = None) -> bool:
        """Send calendar invitation to attendee"""
        with db_session() as session:
            event = session.query(CalendarEvent).filter(
                CalendarEvent.id == event_id,
                CalendarEvent.tenant_id == tenant_id
            ).first()
            
            if not event:
                return False
            
            # Create invitation record
            invitation = CalendarInvitation(
                tenant_id=tenant_id,
                event_id=event.id,
                attendee_email=attendee_email,
                attendee_name=attendee_name,
                invitation_token=secrets.token_urlsafe(32),
                expires_at=event.start_time + timedelta(days=7)
            )
            
            session.add(invitation)
            session.commit()
            
            # Generate ICS file
            ics_content = self._generate_ics(event, invitation)
            
            # Send email with ICS attachment
            success = self.email_service.send_calendar_invitation(
                to_email=attendee_email,
                event=event.to_dict(),
                ics_content=ics_content,
                invitation_token=invitation.invitation_token
            )
            
            return success
    
    def process_rsvp(self, invitation_token: str, rsvp_status: str) -> bool:
        """Process RSVP response"""
        with db_session() as session:
            invitation = session.query(CalendarInvitation).filter(
                CalendarInvitation.invitation_token == invitation_token
            ).first()
            
            if not invitation:
                return False
            
            # Update RSVP status
            invitation.rsvp_status = rsvp_status
            invitation.rsvp_updated_at = datetime.utcnow()
            
            # Update event attendee status
            event = session.query(CalendarEvent).filter(
                CalendarEvent.id == invitation.event_id
            ).first()
            
            if event and event.attendees:
                for attendee in event.attendees:
                    if attendee.get('email') == invitation.attendee_email:
                        attendee['rsvp_status'] = rsvp_status
                        break
                
                session.commit()
            
            return True
    
    def import_ics(self, tenant_id: str, user_id: str, ics_content: str) -> List[CalendarEvent]:
        """Import events from ICS file"""
        events = []
        
        try:
            # Parse ICS content (simplified)
            ics_events = self._parse_ics(ics_content)
            
            with db_session() as session:
                for ics_event in ics_events:
                    event = CalendarEvent(
                        tenant_id=tenant_id,
                        title=ics_event.get('summary', 'Imported Event'),
                        description=ics_event.get('description'),
                        start_time=ics_event.get('start_time'),
                        end_time=ics_event.get('end_time'),
                        location=ics_event.get('location'),
                        organizer_email=ics_event.get('organizer'),
                        is_all_day=ics_event.get('all_day', False),
                        external_provider='ics',
                        created_by=user_id
                    )
                    
                    session.add(event)
                    events.append(event)
                
                session.commit()
            
            return events
            
        except Exception as e:
            logger.error(f"Error importing ICS: {e}")
            raise ValueError("Invalid ICS file format")
    
    def export_ics(self, tenant_id: str, start_date: datetime, end_date: datetime) -> str:
        """Export events to ICS format"""
        events = self.get_events(tenant_id, start_date, end_date)
        
        ics_content = "BEGIN:VCALENDAR\r\n"
        ics_content += "VERSION:2.0\r\n"
        ics_content += "PRODID:-//CRM/Ops//Calendar//EN\r\n"
        
        for event in events:
            ics_content += self._event_to_ics(event)
        
        ics_content += "END:VCALENDAR\r\n"
        
        return ics_content
    
    def _send_invitations(self, session: Session, event: CalendarEvent):
        """Send invitations to all attendees"""
        for attendee in event.attendees:
            if attendee.get('email'):
                invitation = CalendarInvitation(
                    tenant_id=event.tenant_id,
                    event_id=event.id,
                    attendee_email=attendee['email'],
                    attendee_name=attendee.get('name'),
                    invitation_token=secrets.token_urlsafe(32),
                    expires_at=event.start_time + timedelta(days=7)
                )
                
                session.add(invitation)
        
        session.commit()
    
    def _generate_ics(self, event: CalendarEvent, invitation: CalendarInvitation) -> str:
        """Generate ICS content for event"""
        ics = "BEGIN:VCALENDAR\r\n"
        ics += "VERSION:2.0\r\n"
        ics += "PRODID:-//CRM/Ops//Calendar//EN\r\n"
        ics += "METHOD:REQUEST\r\n"
        ics += "BEGIN:VEVENT\r\n"
        ics += f"UID:{event.id}\r\n"
        ics += f"DTSTART:{event.start_time.strftime('%Y%m%dT%H%M%SZ')}\r\n"
        ics += f"DTEND:{event.end_time.strftime('%Y%m%dT%H%M%SZ')}\r\n"
        ics += f"SUMMARY:{event.title}\r\n"
        if event.description:
            ics += f"DESCRIPTION:{event.description}\r\n"
        if event.location:
            ics += f"LOCATION:{event.location}\r\n"
        ics += f"ORGANIZER;CN={event.organizer_name or 'CRM/Ops'}:mailto:{event.organizer_email}\r\n"
        ics += f"ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE;CN={invitation.attendee_name or invitation.attendee_email}:mailto:{invitation.attendee_email}\r\n"
        ics += "END:VEVENT\r\n"
        ics += "END:VCALENDAR\r\n"
        
        return ics
    
    def _event_to_ics(self, event: CalendarEvent) -> str:
        """Convert event to ICS format"""
        ics = "BEGIN:VEVENT\r\n"
        ics += f"UID:{event.id}\r\n"
        ics += f"DTSTART:{event.start_time.strftime('%Y%m%dT%H%M%SZ')}\r\n"
        ics += f"DTEND:{event.end_time.strftime('%Y%m%dT%H%M%SZ')}\r\n"
        ics += f"SUMMARY:{event.title}\r\n"
        if event.description:
            ics += f"DESCRIPTION:{event.description}\r\n"
        if event.location:
            ics += f"LOCATION:{event.location}\r\n"
        ics += f"ORGANIZER;CN={event.organizer_name or 'CRM/Ops'}:mailto:{event.organizer_email}\r\n"
        ics += "END:VEVENT\r\n"
        
        return ics
    
    def _parse_ics(self, ics_content: str) -> List[Dict[str, Any]]:
        """Parse ICS content (simplified implementation)"""
        events = []
        current_event = {}
        
        lines = ics_content.split('\r\n')
        
        for line in lines:
            if line.startswith('BEGIN:VEVENT'):
                current_event = {}
            elif line.startswith('END:VEVENT'):
                if current_event:
                    events.append(current_event)
                current_event = {}
            elif line.startswith('SUMMARY:'):
                current_event['summary'] = line[8:]
            elif line.startswith('DESCRIPTION:'):
                current_event['description'] = line[12:]
            elif line.startswith('LOCATION:'):
                current_event['location'] = line[9:]
            elif line.startswith('DTSTART:'):
                # Parse date (simplified)
                date_str = line[8:]
                try:
                    current_event['start_time'] = datetime.strptime(date_str, '%Y%m%dT%H%M%SZ')
                except ValueError:
                    pass
            elif line.startswith('DTEND:'):
                # Parse date (simplified)
                date_str = line[6:]
                try:
                    current_event['end_time'] = datetime.strptime(date_str, '%Y%m%dT%H%M%SZ')
                except ValueError:
                    pass
        
        return events
