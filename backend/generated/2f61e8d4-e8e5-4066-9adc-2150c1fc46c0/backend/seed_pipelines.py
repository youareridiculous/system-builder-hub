import sqlite3
from datetime import datetime, timedelta
import random

def seed_pipelines():
    """Seed pipeline and deal data for testing Kanban view"""
    conn = sqlite3.connect('data/app.db')
    cursor = conn.cursor()
    
    # Get existing accounts and contacts
    cursor.execute("SELECT id FROM accounts LIMIT 3")
    account_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT id FROM contacts LIMIT 5")
    contact_ids = [row[0] for row in cursor.fetchall()]
    
    if not account_ids or not contact_ids:
        print("No accounts or contacts found. Please run seed.py first.")
        return
    
    # Create a sample pipeline
    cursor.execute("""
        INSERT INTO pipelines (name, description, created_at)
        VALUES (?, ?, ?)
    """, ('Sales Pipeline', 'Main sales pipeline for tracking deals', datetime.now()))
    
    pipeline_id = cursor.lastrowid
    
    # Sample deals across different stages
    deals = [
        # Prospecting
        {
            'title': 'Acme Corp Software Deal',
            'amount': 25000,
            'stage': 'prospecting',
            'account_id': account_ids[0],
            'contact_id': contact_ids[0],
            'close_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'position': 0
        },
        {
            'title': 'TechStart Consulting',
            'amount': 15000,
            'stage': 'prospecting',
            'account_id': account_ids[1],
            'contact_id': contact_ids[1],
            'close_date': (datetime.now() + timedelta(days=45)).strftime('%Y-%m-%d'),
            'position': 1
        },
        
        # Qualification
        {
            'title': 'Global Industries CRM',
            'amount': 50000,
            'stage': 'qualification',
            'account_id': account_ids[2],
            'contact_id': contact_ids[2],
            'close_date': (datetime.now() + timedelta(days=20)).strftime('%Y-%m-%d'),
            'position': 0
        },
        {
            'title': 'StartupXYZ Platform',
            'amount': 35000,
            'stage': 'qualification',
            'account_id': account_ids[0],
            'contact_id': contact_ids[3],
            'close_date': (datetime.now() + timedelta(days=25)).strftime('%Y-%m-%d'),
            'position': 1
        },
        
        # Proposal
        {
            'title': 'Enterprise Solutions Package',
            'amount': 100000,
            'stage': 'proposal',
            'account_id': account_ids[1],
            'contact_id': contact_ids[0],
            'close_date': (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'),
            'position': 0
        },
        
        # Negotiation
        {
            'title': 'Mid-Market Integration',
            'amount': 75000,
            'stage': 'negotiation',
            'account_id': account_ids[2],
            'contact_id': contact_ids[0],
            'close_date': (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
            'position': 0
        },
        {
            'title': 'SaaS Platform License',
            'amount': 45000,
            'stage': 'negotiation',
            'account_id': account_ids[0],
            'contact_id': contact_ids[1],
            'close_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            'position': 1
        },
        
        # Closed Won
        {
            'title': 'Small Business Package',
            'amount': 12000,
            'stage': 'closed_won',
            'account_id': account_ids[1],
            'contact_id': contact_ids[2],
            'close_date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
            'position': 0
        },
        {
            'title': 'Consulting Services',
            'amount': 28000,
            'stage': 'closed_won',
            'account_id': account_ids[2],
            'contact_id': contact_ids[3],
            'close_date': (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'),
            'position': 1
        },
        
        # Closed Lost
        {
            'title': 'Legacy System Migration',
            'amount': 85000,
            'stage': 'closed_lost',
            'account_id': account_ids[0],
            'contact_id': contact_ids[0],
            'close_date': (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d'),
            'position': 0
        }
    ]
    
    # Insert deals
    for deal in deals:
        cursor.execute("""
            INSERT INTO deals 
            (title, amount, stage, account_id, contact_id, close_date, position, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            deal['title'],
            deal['amount'],
            deal['stage'],
            deal['account_id'],
            deal['contact_id'],
            deal['close_date'],
            deal['position'],
            datetime.now()
        ))
    
    conn.commit()
    conn.close()
    print(f"Seeded 1 pipeline and {len(deals)} deals")

if __name__ == "__main__":
    seed_pipelines()
