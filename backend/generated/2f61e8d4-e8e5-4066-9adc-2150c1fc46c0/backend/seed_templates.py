import sqlite3
import json
from datetime import datetime

def seed_templates():
    """Seed the database with sample templates"""
    conn = sqlite3.connect('data/app.db')
    cursor = conn.cursor()
    
    # Sample email templates
    email_templates = [
        {
            'name': 'Welcome Email',
            'type': 'email',
            'category': 'Onboarding',
            'subject': 'Welcome to {account.name}, {contact.first_name}!',
            'body': '''Hi {contact.first_name},

Welcome to {account.name}! We're excited to have you on board.

Your account details:
- Account: {account.name}
- Industry: {account.industry}
- Website: {account.website}

If you have any questions, please don't hesitate to reach out.

Best regards,
{user.name}
CRM Team''',
            'tokens_detected': json.dumps([
                'contact.first_name', 'account.name', 'account.industry', 
                'account.website', 'user.name'
            ])
        },
        {
            'name': 'Deal Follow-up',
            'type': 'email',
            'category': 'Sales',
            'subject': 'Following up on {deal.title}',
            'body': '''Hi {contact.first_name},

I wanted to follow up on our discussion about {deal.title}.

Deal Details:
- Deal: {deal.title}
- Amount: ${deal.amount}
- Stage: {deal.stage}

Please let me know if you have any questions or if there's anything else I can help you with.

Best regards,
{user.name}''',
            'tokens_detected': json.dumps([
                'contact.first_name', 'deal.title', 'deal.amount', 
                'deal.stage', 'user.name'
            ])
        },
        {
            'name': 'Contract Renewal',
            'type': 'email',
            'category': 'Retention',
            'subject': 'Contract Renewal - {account.name}',
            'body': '''Dear {contact.first_name},

Your contract with {account.name} is up for renewal on {date}.

We value our partnership and would love to discuss renewal options with you.

Please let me know when would be a good time to schedule a call.

Best regards,
{user.name}
Account Manager''',
            'tokens_detected': json.dumps([
                'contact.first_name', 'account.name', 'date', 'user.name'
            ])
        }
    ]
    
    # Sample SMS templates
    sms_templates = [
        {
            'name': 'Quick Follow-up',
            'type': 'sms',
            'category': 'Sales',
            'subject': None,
            'body': 'Hi {contact.first_name}, following up on {deal.title}. Call me at your convenience.',
            'tokens_detected': json.dumps(['contact.first_name', 'deal.title'])
        },
        {
            'name': 'Meeting Reminder',
            'type': 'sms',
            'category': 'Scheduling',
            'subject': None,
            'body': 'Reminder: Meeting with {contact.first_name} at {time} today. See you there!',
            'tokens_detected': json.dumps(['contact.first_name', 'time'])
        },
        {
            'name': 'Welcome SMS',
            'type': 'sms',
            'category': 'Onboarding',
            'subject': None,
            'body': 'Welcome {contact.first_name}! Your account with {account.name} is now active. Reply HELP for support.',
            'tokens_detected': json.dumps(['contact.first_name', 'account.name'])
        }
    ]
    
    # Insert email templates
    for template in email_templates:
        cursor.execute("""
            INSERT INTO templates (name, type, category, subject, body, tokens_detected, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template['name'],
            template['type'],
            template['category'],
            template['subject'],
            template['body'],
            template['tokens_detected'],
            datetime.now(),
            datetime.now()
        ))
    
    # Insert SMS templates
    for template in sms_templates:
        cursor.execute("""
            INSERT INTO templates (name, type, category, subject, body, tokens_detected, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template['name'],
            template['type'],
            template['category'],
            template['subject'],
            template['body'],
            template['tokens_detected'],
            datetime.now(),
            datetime.now()
        ))
    
    conn.commit()
    conn.close()
    print("✅ Templates seeded successfully!")

if __name__ == "__main__":
    seed_templates()
