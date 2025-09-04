"""
Slack Notifier Plugin
Sends notifications to Slack channels for important CRM events
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

@hook("deal.won")
def notify_deal_won(event_data: Dict[str, Any], ctx) -> None:
    """Notify Slack when a deal is won"""
    try:
        deal = event_data.get('deal', {})
        deal_id = deal.get('id')
        deal_title = deal.get('title', 'Untitled Deal')
        deal_value = deal.get('value', 0)
        owner_name = deal.get('owner_name', 'Unknown')
        
        webhook_url = ctx.secrets.get("SLACK_WEBHOOK_URL")
        channel = ctx.secrets.get("SLACK_CHANNEL", "#sales")
        
        if not webhook_url:
            logger.warning("No Slack webhook URL configured, skipping notification")
            return
        
        # Create Slack message
        message = {
            "channel": channel,
            "text": f"🎉 *Deal Won!*",
            "attachments": [
                {
                    "color": "good",
                    "fields": [
                        {
                            "title": "Deal",
                            "value": deal_title,
                            "short": True
                        },
                        {
                            "title": "Value",
                            "value": f"${deal_value:,.0f}",
                            "short": True
                        },
                        {
                            "title": "Owner",
                            "value": owner_name,
                            "short": True
                        },
                        {
                            "title": "Won At",
                            "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                            "short": True
                        }
                    ],
                    "footer": "SBH CRM",
                    "footer_icon": "https://sbh.com/favicon.ico"
                }
            ]
        }
        
        # Send to Slack
        response = ctx.http.post(
            webhook_url,
            json=message,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            logger.info(f"Slack notification sent for deal {deal_id}")
        else:
            logger.error(f"Failed to send Slack notification: {response.status_code}")
        
        # Track analytics
        ctx.analytics.track("slack_notification.sent", {
            "event_type": "deal.won",
            "deal_id": deal_id,
            "tenant_id": ctx.tenant_id,
            "slack_channel": channel
        })
        
    except Exception as e:
        logger.error(f"Error sending Slack notification for deal won: {e}")
        raise

@hook("deal.lost")
def notify_deal_lost(event_data: Dict[str, Any], ctx) -> None:
    """Notify Slack when a deal is lost"""
    try:
        deal = event_data.get('deal', {})
        deal_id = deal.get('id')
        deal_title = deal.get('title', 'Untitled Deal')
        deal_value = deal.get('value', 0)
        owner_name = deal.get('owner_name', 'Unknown')
        loss_reason = deal.get('loss_reason', 'No reason provided')
        
        webhook_url = ctx.secrets.get("SLACK_WEBHOOK_URL")
        channel = ctx.secrets.get("SLACK_CHANNEL", "#sales")
        
        if not webhook_url:
            logger.warning("No Slack webhook URL configured, skipping notification")
            return
        
        # Create Slack message
        message = {
            "channel": channel,
            "text": f"❌ *Deal Lost*",
            "attachments": [
                {
                    "color": "danger",
                    "fields": [
                        {
                            "title": "Deal",
                            "value": deal_title,
                            "short": True
                        },
                        {
                            "title": "Value",
                            "value": f"${deal_value:,.0f}",
                            "short": True
                        },
                        {
                            "title": "Owner",
                            "value": owner_name,
                            "short": True
                        },
                        {
                            "title": "Loss Reason",
                            "value": loss_reason,
                            "short": False
                        }
                    ],
                    "footer": "SBH CRM",
                    "footer_icon": "https://sbh.com/favicon.ico"
                }
            ]
        }
        
        # Send to Slack
        response = ctx.http.post(
            webhook_url,
            json=message,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            logger.info(f"Slack notification sent for lost deal {deal_id}")
        else:
            logger.error(f"Failed to send Slack notification: {response.status_code}")
        
    except Exception as e:
        logger.error(f"Error sending Slack notification for deal lost: {e}")
        raise

@hook("contact.created")
def notify_new_contact(event_data: Dict[str, Any], ctx) -> None:
    """Notify Slack when a new contact is created"""
    try:
        contact = event_data.get('contact', {})
        contact_id = contact.get('id')
        contact_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        contact_email = contact.get('email', 'No email')
        contact_company = contact.get('company', 'No company')
        
        webhook_url = ctx.secrets.get("SLACK_WEBHOOK_URL")
        channel = ctx.secrets.get("SLACK_CHANNEL", "#leads")
        
        if not webhook_url:
            logger.warning("No Slack webhook URL configured, skipping notification")
            return
        
        # Create Slack message
        message = {
            "channel": channel,
            "text": f"👤 *New Contact Added*",
            "attachments": [
                {
                    "color": "good",
                    "fields": [
                        {
                            "title": "Name",
                            "value": contact_name,
                            "short": True
                        },
                        {
                            "title": "Email",
                            "value": contact_email,
                            "short": True
                        },
                        {
                            "title": "Company",
                            "value": contact_company,
                            "short": True
                        },
                        {
                            "title": "Added By",
                            "value": ctx.user_id,
                            "short": True
                        }
                    ],
                    "footer": "SBH CRM",
                    "footer_icon": "https://sbh.com/favicon.ico"
                }
            ]
        }
        
        # Send to Slack
        response = ctx.http.post(
            webhook_url,
            json=message,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            logger.info(f"Slack notification sent for new contact {contact_id}")
        else:
            logger.error(f"Failed to send Slack notification: {response.status_code}")
        
    except Exception as e:
        logger.error(f"Error sending Slack notification for new contact: {e}")
        raise

@hook("task.overdue")
def notify_overdue_task(event_data: Dict[str, Any], ctx) -> None:
    """Notify Slack when a task is overdue"""
    try:
        task = event_data.get('task', {})
        task_id = task.get('id')
        task_title = task.get('title', 'Untitled Task')
        assignee_name = task.get('assignee_name', 'Unassigned')
        due_date = task.get('due_date', 'Unknown')
        
        webhook_url = ctx.secrets.get("SLACK_WEBHOOK_URL")
        channel = ctx.secrets.get("SLACK_CHANNEL", "#ops")
        
        if not webhook_url:
            logger.warning("No Slack webhook URL configured, skipping notification")
            return
        
        # Create Slack message
        message = {
            "channel": channel,
            "text": f"⚠️ *Overdue Task*",
            "attachments": [
                {
                    "color": "warning",
                    "fields": [
                        {
                            "title": "Task",
                            "value": task_title,
                            "short": True
                        },
                        {
                            "title": "Assignee",
                            "value": assignee_name,
                            "short": True
                        },
                        {
                            "title": "Due Date",
                            "value": due_date,
                            "short": True
                        },
                        {
                            "title": "Priority",
                            "value": task.get('priority', 'Medium'),
                            "short": True
                        }
                    ],
                    "footer": "SBH CRM",
                    "footer_icon": "https://sbh.com/favicon.ico"
                }
            ]
        }
        
        # Send to Slack
        response = ctx.http.post(
            webhook_url,
            json=message,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            logger.info(f"Slack notification sent for overdue task {task_id}")
        else:
            logger.error(f"Failed to send Slack notification: {response.status_code}")
        
    except Exception as e:
        logger.error(f"Error sending Slack notification for overdue task: {e}")
        raise

@route("/ping", methods=["GET"])
def ping(ctx) -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok", "plugin": "slack-notifier", "timestamp": datetime.utcnow().isoformat()}

@route("/test", methods=["POST"])
def test_notification(ctx) -> Dict[str, Any]:
    """Test Slack notification endpoint"""
    try:
        webhook_url = ctx.secrets.get("SLACK_WEBHOOK_URL")
        channel = ctx.secrets.get("SLACK_CHANNEL", "#general")
        
        if not webhook_url:
            return {"error": "No Slack webhook URL configured"}
        
        # Send test message
        message = {
            "channel": channel,
            "text": "🧪 *Test Notification*",
            "attachments": [
                {
                    "color": "good",
                    "text": "This is a test notification from SBH CRM Slack Notifier plugin.",
                    "footer": "SBH CRM",
                    "footer_icon": "https://sbh.com/favicon.ico"
                }
            ]
        }
        
        response = ctx.http.post(
            webhook_url,
            json=message,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return {"success": True, "message": "Test notification sent successfully"}
        else:
            return {"error": f"Failed to send test notification: {response.status_code}"}
        
    except Exception as e:
        return {"error": f"Error sending test notification: {str(e)}"}

@job("daily_slack_summary")
def send_daily_summary(ctx) -> None:
    """Send daily summary to Slack"""
    try:
        webhook_url = ctx.secrets.get("SLACK_WEBHOOK_URL")
        channel = ctx.secrets.get("SLACK_CHANNEL", "#daily-summary")
        
        if not webhook_url:
            logger.warning("No Slack webhook URL configured, skipping daily summary")
            return
        
        # Get daily stats
        stats = ctx.db.query("""
            SELECT 
                COUNT(DISTINCT c.id) as new_contacts,
                COUNT(DISTINCT d.id) as new_deals,
                COUNT(DISTINCT CASE WHEN d.status = 'won' THEN d.id END) as won_deals,
                COUNT(DISTINCT t.id) as completed_tasks
            FROM contacts c
            LEFT JOIN deals d ON d.tenant_id = c.tenant_id AND DATE(d.created_at) = CURDATE()
            LEFT JOIN tasks t ON t.tenant_id = c.tenant_id AND DATE(t.completed_at) = CURDATE()
            WHERE c.tenant_id = %s AND DATE(c.created_at) = CURDATE()
        """, [ctx.tenant_id])
        
        if stats:
            stat = stats[0]
            
            # Create summary message
            message = {
                "channel": channel,
                "text": f"📊 *Daily Summary - {datetime.utcnow().strftime('%Y-%m-%d')}*",
                "attachments": [
                    {
                        "color": "good",
                        "fields": [
                            {
                                "title": "New Contacts",
                                "value": str(stat['new_contacts']),
                                "short": True
                            },
                            {
                                "title": "New Deals",
                                "value": str(stat['new_deals']),
                                "short": True
                            },
                            {
                                "title": "Won Deals",
                                "value": str(stat['won_deals']),
                                "short": True
                            },
                            {
                                "title": "Completed Tasks",
                                "value": str(stat['completed_tasks']),
                                "short": True
                            }
                        ],
                        "footer": "SBH CRM",
                        "footer_icon": "https://sbh.com/favicon.ico"
                    }
                ]
            }
            
            # Send to Slack
            response = ctx.http.post(
                webhook_url,
                json=message,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info("Daily Slack summary sent successfully")
            else:
                logger.error(f"Failed to send daily Slack summary: {response.status_code}")
        
    except Exception as e:
        logger.error(f"Error sending daily Slack summary: {e}")
        raise

@hook("plugin.installed")
def on_install(ctx) -> None:
    """Plugin installation hook"""
    logger.info(f"Slack Notifier plugin installed for tenant {ctx.tenant_id}")
    
    # Set default channel if not provided
    if not ctx.secrets.get("SLACK_CHANNEL"):
        ctx.secrets.set("SLACK_CHANNEL", "#general")

@hook("plugin.uninstalled")
def on_uninstall(ctx) -> None:
    """Plugin uninstallation hook"""
    logger.info(f"Slack Notifier plugin uninstalled for tenant {ctx.tenant_id}")
    
    # Clean up any plugin-specific data
    # (In this case, no cleanup needed)
