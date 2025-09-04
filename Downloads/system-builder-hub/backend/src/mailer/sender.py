"""
Email sender service
"""
import os
import logging
import boto3
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from src.db_core import get_session
from src.integrations.models import EmailOutbound
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

class EmailSender:
    """Email sender service"""
    
    def __init__(self):
        self.env = os.environ.get('ENV', 'development')
        self.ses_region = os.environ.get('SES_REGION', 'us-east-1')
        self.from_address = os.environ.get('SES_FROM_ADDRESS', 'no-reply@myapp.com')
        self.dev_echo = os.environ.get('DEV_EMAIL_ECHO', 'true').lower() == 'true'
        
        # Initialize SES client for production
        if self.env == 'production':
            try:
                self.ses_client = boto3.client('ses', region_name=self.ses_region)
            except Exception as e:
                logger.warning(f"Failed to initialize SES client: {e}")
                self.ses_client = None
        else:
            self.ses_client = None
        
        # Initialize Jinja2 template environment
        template_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'email')
        if os.path.exists(template_dir):
            self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        else:
            self.jinja_env = None
            logger.warning("Email templates directory not found")
    
    def send_email(self, tenant_id: str, to_email: str, template: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send email using template"""
        try:
            session = get_session()
            
            # Create email record
            email = EmailOutbound(
                tenant_id=tenant_id,
                to_email=to_email,
                template=template,
                payload=payload or {},
                status='queued'
            )
            
            session.add(email)
            session.commit()
            session.refresh(email)
            
            # Send email
            success = self._send_email_internal(email, to_email, template, payload)
            
            if success:
                email.status = 'sent'
                logger.info(f"Email sent successfully: {email.id} to {to_email}")
            else:
                email.status = 'failed'
                logger.error(f"Email failed to send: {email.id} to {to_email}")
            
            session.commit()
            
            return {
                'id': str(email.id),
                'to_email': email.to_email,
                'template': email.template,
                'status': email.status,
                'provider_message_id': email.provider_message_id,
                'error': email.error,
                'created_at': email.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    def _send_email_internal(self, email: EmailOutbound, to_email: str, template: str, payload: Dict[str, Any]) -> bool:
        """Internal email sending logic"""
        try:
            # Render template
            html_content, text_content, subject = self._render_template(template, payload)
            
            if not html_content:
                email.error = 'Template not found or rendering failed'
                return False
            
            # Development mode
            if self.env != 'production' or self.dev_echo:
                logger.info(f"DEV EMAIL ECHO - To: {to_email}, Subject: {subject}")
                logger.info(f"DEV EMAIL ECHO - HTML: {html_content[:200]}...")
                email.provider_message_id = f"dev_echo_{email.id}"
                return True
            
            # Production mode with SES
            if self.ses_client:
                response = self.ses_client.send_email(
                    Source=self.from_address,
                    Destination={'ToAddresses': [to_email]},
                    Message={
                        'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                        'Body': {
                            'Html': {'Data': html_content, 'Charset': 'UTF-8'},
                            'Text': {'Data': text_content, 'Charset': 'UTF-8'}
                        }
                    }
                )
                
                email.provider_message_id = response['MessageId']
                return True
            
            else:
                email.error = 'SES client not available'
                return False
                
        except Exception as e:
            email.error = str(e)
            logger.error(f"Error in email sending: {e}")
            return False
    
    def _render_template(self, template: str, payload: Dict[str, Any]) -> tuple:
        """Render email template"""
        if not self.jinja_env:
            return None, None, "Email Template"
        
        try:
            # Load template
            template_obj = self.jinja_env.get_template(f"{template}.html")
            
            # Render with payload
            html_content = template_obj.render(**payload)
            
            # Extract subject from template or use default
            subject = payload.get('subject', f"SBH - {template.title()}")
            
            # Generate text version (simple HTML to text conversion)
            text_content = self._html_to_text(html_content)
            
            return html_content, text_content, subject
            
        except Exception as e:
            logger.error(f"Error rendering template {template}: {e}")
            return None, None, "Email Template"
    
    def _html_to_text(self, html_content: str) -> str:
        """Simple HTML to text conversion"""
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def get_email_templates(self) -> Dict[str, str]:
        """Get available email templates"""
        if not self.jinja_env:
            return {}
        
        templates = {}
        for template_name in self.jinja_env.list_templates():
            if template_name.endswith('.html'):
                template_name = template_name[:-5]  # Remove .html extension
                templates[template_name] = f"Email template: {template_name}"
        
        return templates
    
    def list_emails(self, tenant_id: str, limit: int = 50) -> list:
        """List recent emails for tenant"""
        try:
            session = get_session()
            
            emails = session.query(EmailOutbound).filter(
                EmailOutbound.tenant_id == tenant_id
            ).order_by(EmailOutbound.created_at.desc()).limit(limit).all()
            
            result = []
            for email in emails:
                result.append({
                    'id': str(email.id),
                    'to_email': email.to_email,
                    'template': email.template,
                    'status': email.status,
                    'provider_message_id': email.provider_message_id,
                    'error': email.error,
                    'created_at': email.created_at.isoformat()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing emails for tenant {tenant_id}: {e}")
            return []
