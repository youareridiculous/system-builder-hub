import sqlite3
from datetime import datetime, timedelta
import random

def seed_communications():
    """Seed communication history with sample data"""
    conn = sqlite3.connect('data/app.db')
    cursor = conn.cursor()
    
    # Get existing contacts and accounts
    cursor.execute("SELECT id FROM contacts LIMIT 5")
    contact_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT id FROM accounts LIMIT 3")
    account_ids = [row[0] for row in cursor.fetchall()]
    
    if not contact_ids or not account_ids:
        print("No contacts or accounts found. Please run seed.py first.")
        return
    
    # Sample communication data
    communications = [
        # Emails
        {
            'contact_id': contact_ids[0],
            'account_id': account_ids[0],
            'type': 'email',
            'direction': 'outbound',
            'provider': 'sendgrid',
            'subject': 'Welcome to our platform',
            'content': 'Thank you for choosing our services. We look forward to working with you.',
            'status': 'delivered',
            'created_at': datetime.now() - timedelta(days=1)
        },
        {
            'contact_id': contact_ids[0],
            'account_id': account_ids[0],
            'type': 'email',
            'direction': 'inbound',
            'provider': 'sendgrid',
            'subject': 'Re: Welcome to our platform',
            'content': 'Thank you! I am excited to get started.',
            'status': 'delivered',
            'created_at': datetime.now() - timedelta(hours=12)
        },
        # Calls
        {
            'contact_id': contact_ids[1],
            'account_id': account_ids[0],
            'type': 'call',
            'direction': 'outbound',
            'provider': 'twilio',
            'status': 'completed',
            'duration': 180,
            'created_at': datetime.now() - timedelta(days=2)
        },
        {
            'contact_id': contact_ids[1],
            'account_id': account_ids[0],
            'type': 'call',
            'direction': 'inbound',
            'provider': 'twilio',
            'status': 'completed',
            'duration': 240,
            'created_at': datetime.now() - timedelta(hours=6)
        },
        # SMS
        {
            'contact_id': contact_ids[2],
            'account_id': account_ids[1],
            'type': 'sms',
            'direction': 'outbound',
            'provider': 'twilio',
            'content': 'Your meeting is scheduled for tomorrow at 2 PM.',
            'status': 'delivered',
            'created_at': datetime.now() - timedelta(days=3)
        },
        {
            'contact_id': contact_ids[2],
            'account_id': account_ids[1],
            'type': 'sms',
            'direction': 'inbound',
            'provider': 'twilio',
            'content': 'Perfect, see you then!',
            'status': 'delivered',
            'created_at': datetime.now() - timedelta(days=3, minutes=5)
        },
        # More varied data
        {
            'contact_id': contact_ids[3],
            'account_id': account_ids[2],
            'type': 'email',
            'direction': 'outbound',
            'provider': 'sendgrid',
            'subject': 'Proposal for Q4',
            'content': 'Please find attached our proposal for Q4 services.',
            'status': 'sent',
            'created_at': datetime.now() - timedelta(hours=2)
        },
        {
            'contact_id': contact_ids[0],
            'account_id': account_ids[2],
            'type': 'call',
            'direction': 'outbound',
            'provider': 'twilio',
            'status': 'missed',
            'created_at': datetime.now() - timedelta(hours=1)
        },
        {
            'contact_id': contact_ids[0],
            'account_id': account_ids[0],
            'type': 'sms',
            'direction': 'outbound',
            'provider': 'twilio',
            'content': 'Quick reminder: Your demo is in 30 minutes.',
            'status': 'delivered',
            'created_at': datetime.now() - timedelta(minutes=30)
        },
        {
            'contact_id': contact_ids[1],
            'account_id': account_ids[1],
            'type': 'email',
            'direction': 'outbound',
            'provider': 'sendgrid',
            'subject': 'Contract Renewal',
            'content': 'Your contract is up for renewal. Let\'s discuss options.',
            'status': 'failed',
            'created_at': datetime.now() - timedelta(minutes=15)
        }
    ]
    
    # Insert communications
    for comm in communications:
        cursor.execute("""
            INSERT INTO communication_history 
            (contact_id, account_id, type, direction, provider, subject, content, 
             status, duration, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            comm['contact_id'],
            comm['account_id'],
            comm['type'],
            comm['direction'],
            comm['provider'],
            comm.get('subject'),
            comm.get('content'),
            comm['status'],
            comm.get('duration'),
            comm['created_at'],
            comm['created_at']
        ))
    
    conn.commit()
    conn.close()
    print(f"Seeded {len(communications)} communications")

if __name__ == "__main__":
    seed_communications()
