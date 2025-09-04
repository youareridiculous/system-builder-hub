import sqlite3
import json
from datetime import datetime

def seed_automations():
    """Seed the database with sample automation rules"""
    conn = sqlite3.connect('data/app.db')
    cursor = conn.cursor()
    
    # Get template IDs for reference
    cursor.execute("SELECT id, name FROM templates WHERE type = 'email' LIMIT 1")
    email_template = cursor.fetchone()
    email_template_id = email_template[0] if email_template else 1
    
    cursor.execute("SELECT id, name FROM templates WHERE type = 'sms' LIMIT 1")
    sms_template = cursor.fetchone()
    sms_template_id = sms_template[0] if sms_template else 1
    
    # Sample automation rules
    automation_rules = [
        {
            'name': 'Deal Stage Change - Send Follow-up',
            'trigger': 'deal.stage_changed',
            'conditions': json.dumps({
                'stage': 'proposal',
                'stage_operator': 'equals'
            }),
            'actions': json.dumps([
                {
                    'type': 'send_email_template',
                    'template_id': email_template_id,
                    'contact_id': '{contact_id}'
                },
                {
                    'type': 'create_activity',
                    'activity_type': 'call',
                    'subject': 'Follow-up call after proposal',
                    'description': 'Call to discuss proposal and answer questions',
                    'due_date_offset': '2d'
                }
            ])
        },
        {
            'name': 'New Contact - Welcome Sequence',
            'trigger': 'contact.created',
            'conditions': json.dumps({
                'contact_has_email': True
            }),
            'actions': json.dumps([
                {
                    'type': 'send_email_template',
                    'template_id': email_template_id,
                    'contact_id': '{contact_id}'
                },
                {
                    'type': 'create_activity',
                    'activity_type': 'task',
                    'subject': 'Schedule welcome call',
                    'description': 'Schedule a welcome call with the new contact',
                    'due_date_offset': '3d'
                }
            ])
        },
        {
            'name': 'Communication Failed - Retry Logic',
            'trigger': 'communication.status_updated',
            'conditions': json.dumps({
                'status': 'failed'
            }),
            'actions': json.dumps([
                {
                    'type': 'send_sms_template',
                    'template_id': sms_template_id,
                    'contact_id': '{contact_id}'
                }
            ])
        },
        {
            'name': 'Deal Won - Celebration',
            'trigger': 'deal.stage_changed',
            'conditions': json.dumps({
                'stage': 'closed_won',
                'stage_operator': 'equals'
            }),
            'actions': json.dumps([
                {
                    'type': 'send_email_template',
                    'template_id': email_template_id,
                    'contact_id': '{contact_id}'
                },
                {
                    'type': 'create_activity',
                    'activity_type': 'meeting',
                    'subject': 'Onboarding kickoff',
                    'description': 'Schedule onboarding meeting for new customer',
                    'due_date_offset': '1d'
                }
            ])
        }
    ]
    
    # Insert automation rules
    for rule in automation_rules:
        cursor.execute("""
            INSERT INTO automation_rules (name, trigger, conditions, actions, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            rule['name'],
            rule['trigger'],
            rule['conditions'],
            rule['actions'],
            datetime.now(),
            datetime.now()
        ))
    
    conn.commit()
    conn.close()
    print("✅ Automation rules seeded successfully!")

if __name__ == "__main__":
    seed_automations()
