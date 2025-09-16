"""
Welcome Email Plugin
Sends welcome emails to new users and daily digest emails
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)

@hook("auth.user.created")
def send_welcome_email(event_data: Dict[str, Any], ctx) -> None:
    """Send welcome email when a new user is created"""
    try:
        user = event_data.get('user', {})
        user_email = user.get('email')
        user_name = user.get('first_name', 'User')
        
        if not user_email:
            logger.warning("No email found for user, skipping welcome email")
            return
        
        # Get welcome email template from secrets
        template = ctx.secrets.get("WELCOME_EMAIL_TEMPLATE", """
        Welcome to SBH CRM!
        
        Hi {name},
        
        Welcome to your new CRM system! We're excited to help you manage your contacts, deals, and projects.
        
        Here are some quick tips to get started:
        - Add your first contact
        - Create a deal in your pipeline
        - Set up your first project
        
        If you need help, check out our documentation or contact support.
        
        Best regards,
        The SBH Team
        """)
        
        # Send email via SES
        email_result = ctx.email.send(
            to=user_email,
            subject="Welcome to SBH CRM!",
            body=template.format(name=user_name),
            from_email="noreply@sbh.com"
        )
        
        logger.info(f"Welcome email sent to {user_email}: {email_result}")
        
        # Track analytics
        ctx.analytics.track("welcome_email.sent", {
            "user_id": user.get('id'),
            "email": user_email,
            "tenant_id": ctx.tenant_id
        })
        
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}")
        raise

@route("/ping", methods=["GET"])
def ping(ctx) -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok", "plugin": "welcome-email", "timestamp": datetime.utcnow().isoformat()}

@job("daily_digest")
def send_daily_digest(ctx) -> None:
    """Send daily digest email to users"""
    try:
        # Get digest template from secrets
        template = ctx.secrets.get("DIGEST_EMAIL_TEMPLATE", """
        Daily CRM Digest
        
        Hi {name},
        
        Here's your daily CRM summary:
        
        New Contacts: {new_contacts}
        New Deals: {new_deals}
        Tasks Due Today: {tasks_due}
        
        View your dashboard: {dashboard_url}
        
        Best regards,
        SBH CRM
        """)
        
        # Get user data for digest
        users = ctx.db.query("SELECT id, email, first_name FROM users WHERE tenant_id = %s", [ctx.tenant_id])
        
        for user in users:
            # Get daily stats
            stats = ctx.db.query("""
                SELECT 
                    COUNT(DISTINCT c.id) as new_contacts,
                    COUNT(DISTINCT d.id) as new_deals,
                    COUNT(DISTINCT t.id) as tasks_due
                FROM contacts c
                LEFT JOIN deals d ON d.tenant_id = c.tenant_id
                LEFT JOIN tasks t ON t.tenant_id = c.tenant_id
                WHERE c.tenant_id = %s 
                AND c.created_at >= %s
                AND d.created_at >= %s
                AND t.due_date = %s
            """, [ctx.tenant_id, datetime.utcnow().date(), datetime.utcnow().date(), datetime.utcnow().date()])
            
            if stats:
                stat = stats[0]
                
                # Send digest email
                email_result = ctx.email.send(
                    to=user['email'],
                    subject="Daily CRM Digest",
                    body=template.format(
                        name=user['first_name'],
                        new_contacts=stat['new_contacts'],
                        new_deals=stat['new_deals'],
                        tasks_due=stat['tasks_due'],
                        dashboard_url=f"https://app.sbh.com/dashboard"
                    ),
                    from_email="digest@sbh.com"
                )
                
                logger.info(f"Daily digest sent to {user['email']}: {email_result}")
        
    except Exception as e:
        logger.error(f"Error sending daily digest: {e}")
        raise

@hook("plugin.installed")
def on_install(ctx) -> None:
    """Plugin installation hook"""
    logger.info(f"Welcome Email plugin installed for tenant {ctx.tenant_id}")
    
    # Set default secrets if not provided
    if not ctx.secrets.get("WELCOME_EMAIL_TEMPLATE"):
        ctx.secrets.set("WELCOME_EMAIL_TEMPLATE", """
        Welcome to SBH CRM!
        
        Hi {name},
        
        Welcome to your new CRM system! We're excited to help you manage your contacts, deals, and projects.
        
        Here are some quick tips to get started:
        - Add your first contact
        - Create a deal in your pipeline
        - Set up your first project
        
        If you need help, check out our documentation or contact support.
        
        Best regards,
        The SBH Team
        """)
    
    if not ctx.secrets.get("DIGEST_EMAIL_TEMPLATE"):
        ctx.secrets.set("DIGEST_EMAIL_TEMPLATE", """
        Daily CRM Digest
        
        Hi {name},
        
        Here's your daily CRM summary:
        
        New Contacts: {new_contacts}
        New Deals: {new_deals}
        Tasks Due Today: {tasks_due}
        
        View your dashboard: {dashboard_url}
        
        Best regards,
        SBH CRM
        """)

@hook("plugin.uninstalled")
def on_uninstall(ctx) -> None:
    """Plugin uninstallation hook"""
    logger.info(f"Welcome Email plugin uninstalled for tenant {ctx.tenant_id}")
    
    # Clean up any plugin-specific data
    # (In this case, no cleanup needed)
