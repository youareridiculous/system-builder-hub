"""
Email service for CRM/Ops Template
"""
import logging
import boto3
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader
from src.config import get_config

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending transactional emails"""
    
    def __init__(self):
        self.config = get_config()
        self.ses_client = boto3.client(
            'ses',
            region_name=self.config.AWS_REGION,
            aws_access_key_id=self.config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.config.AWS_SECRET_ACCESS_KEY
        )
        
        # Setup Jinja2 template environment
        self.template_env = Environment(
            loader=FileSystemLoader('src/templates/mailer')
        )
    
    def send_welcome_email(self, user: Dict[str, Any], login_url: str) -> bool:
        """Send welcome email to new user"""
        try:
            template = self.template_env.get_template('welcome_user.html')
            html_content = template.render(
                user=user,
                login_url=login_url
            )
            
            # Also create text version
            text_content = f"""
Welcome to CRM/Ops!

Hi {user['first_name']},

Welcome to your new CRM/Ops workspace! We're excited to help you manage your customer relationships and operations more effectively.

What you can do now:
- Add your first contacts and deals
- Create projects and tasks
- Invite team members to collaborate
- Explore analytics and insights

Get started: {login_url}

If you have any questions, feel free to reach out to our support team.

Best regards,
The CRM/Ops Team
            """
            
            return self._send_email(
                to_email=user['email'],
                subject='Welcome to CRM/Ops!',
                html_content=html_content,
                text_content=text_content
            )
            
        except Exception as e:
            logger.error(f"Error sending welcome email to {user['email']}: {e}")
            return False
    
    def send_invitation_email(self, email: str, inviter_name: str, company_name: str, role: str, invite_url: str) -> bool:
        """Send invitation email to new team member"""
        try:
            template = self.template_env.get_template('invite_user.html')
            html_content = template.render(
                email=email,
                inviter_name=inviter_name,
                company_name=company_name,
                role=role,
                invite_url=invite_url
            )
            
            # Also create text version
            text_content = f"""
You're Invited to Join CRM/Ops!

Hi there,

{inviter_name} has invited you to join their CRM/Ops workspace at {company_name}.

You'll be joining as a {role} with the following permissions:
- Can view and manage contacts, deals, and projects
- Can collaborate with team members
- Can access analytics and insights

Accept invitation: {invite_url}

This invitation will expire in 7 days. If you have any questions, please contact {inviter_name}.

Best regards,
The CRM/Ops Team
            """
            
            return self._send_email(
                to_email=email,
                subject=f'You\'re Invited to Join {company_name} on CRM/Ops',
                html_content=html_content,
                text_content=text_content
            )
            
        except Exception as e:
            logger.error(f"Error sending invitation email to {email}: {e}")
            return False
    
    def send_deal_won_notification(self, user: Dict[str, Any], deal: Dict[str, Any], contact: Dict[str, Any], total_pipeline_value: float) -> bool:
        """Send deal won notification"""
        try:
            template = self.template_env.get_template('deal_won_notification.html')
            html_content = template.render(
                user=user,
                deal=deal,
                contact=contact,
                total_pipeline_value=total_pipeline_value
            )
            
            # Also create text version
            text_content = f"""
🎉 Deal Won!

Congratulations!

The deal "{deal['title']}" has been marked as won!

Deal Details:
- Value: ${deal['value']:,}
- Contact: {contact['first_name']} {contact['last_name']}
- Company: {contact['company']}
- Closed Date: {deal['closed_at']}

Great work on closing this deal! This brings your total pipeline value to ${total_pipeline_value:,}.

Keep up the excellent work!

Best regards,
The CRM/Ops Team
            """
            
            return self._send_email(
                to_email=user['email'],
                subject=f'Deal Won - {deal["title"]}',
                html_content=html_content,
                text_content=text_content
            )
            
        except Exception as e:
            logger.error(f"Error sending deal won notification to {user['email']}: {e}")
            return False
    
    def send_weekly_digest(self, user: Dict[str, Any], metrics: Dict[str, Any], top_deals: List[Dict], upcoming_activities: List[Dict], dashboard_url: str) -> bool:
        """Send weekly digest email"""
        try:
            template = self.template_env.get_template('weekly_digest.html')
            html_content = template.render(
                user=user,
                metrics=metrics,
                top_deals=top_deals,
                upcoming_activities=upcoming_activities,
                dashboard_url=dashboard_url
            )
            
            # Also create text version
            text_content = f"""
Weekly CRM/Ops Digest

Hi {user['first_name']},

Here's your weekly summary of CRM/Ops activity:

New Contacts: {metrics['contacts_added']}
Deals Won: {metrics['deals_won']}
Total Value: ${metrics['total_deal_value']:,}
Tasks Completed: {metrics['tasks_completed']}

Top Performing Deals:
{chr(10).join([f"- {deal['title']} - ${deal['value']:,}" for deal in top_deals])}

Upcoming Activities:
{chr(10).join([f"- {activity['title']} - {activity['due_date']}" for activity in upcoming_activities])}

View Dashboard: {dashboard_url}

Keep up the great work!

Best regards,
The CRM/Ops Team
            """
            
            return self._send_email(
                to_email=user['email'],
                subject='Weekly CRM/Ops Digest',
                html_content=html_content,
                text_content=text_content
            )
            
        except Exception as e:
            logger.error(f"Error sending weekly digest to {user['email']}: {e}")
            return False
    
    def _send_email(self, to_email: str, subject: str, html_content: str, text_content: str) -> bool:
        """Send email via SES"""
        try:
            response = self.ses_client.send_email(
                Source=self.config.SES_FROM_EMAIL,
                Destination={
                    'ToAddresses': [to_email]
                },
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Html': {
                            'Data': html_content,
                            'Charset': 'UTF-8'
                        },
                        'Text': {
                            'Data': text_content,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )
            
            logger.info(f"Email sent successfully to {to_email}: {response['MessageId']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False
