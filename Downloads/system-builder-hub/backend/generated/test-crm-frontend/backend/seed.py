import sqlite3
import os
from pathlib import Path
from db import get_db, init_db, DB_PATH

def create_schema():
    """Create database schema"""
    init_db()

def seed_data():
    """Seed database with demo data"""
    # Ensure schema exists
    create_schema()
    
    conn = get_db()
    
    # Insert demo accounts
    conn.executemany("""
        INSERT OR IGNORE INTO accounts (name, industry, website)
        VALUES (?, ?, ?)
    """, [
        ("Acme Corp", "Technology", "https://acme.com"),
        ("Global Industries", "Manufacturing", "https://global.com"),
        ("StartupXYZ", "SaaS", "https://startupxyz.com"),
        ("Enterprise Solutions", "Consulting", "https://enterprise.com")
    ])
    
    # Insert demo contacts
    conn.executemany("""
        INSERT OR IGNORE INTO contacts (account_id, first_name, last_name, email, title)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (1, "John", "Smith", "john@acme.com", "CEO"),
        (1, "Jane", "Doe", "jane@acme.com", "CTO"),
        (2, "Bob", "Johnson", "bob@global.com", "VP Sales"),
        (3, "Alice", "Brown", "alice@startupxyz.com", "Founder")
    ])
    
    # Insert demo deals
    conn.executemany("""
        INSERT OR IGNORE INTO deals (account_id, contact_id, title, amount, stage)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (1, 1, "Enterprise License", 50000.0, "negotiation"),
        (2, 3, "Annual Contract", 25000.0, "prospecting"),
        (3, 4, "Seed Investment", 100000.0, "closed_won")
    ])
    
    # Insert demo pipelines
    conn.executemany("""
        INSERT OR IGNORE INTO pipelines (name, description)
        VALUES (?, ?)
    """, [
        ("Sales Pipeline", "Standard sales process"),
        ("Enterprise Pipeline", "Enterprise sales process")
    ])
    
    # Insert demo activities
    conn.executemany("""
        INSERT OR IGNORE INTO activities (deal_id, contact_id, type, subject, description)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (1, 1, "call", "Follow-up Call", "Discuss contract terms"),
        (2, 3, "meeting", "Product Demo", "Show product features"),
        (3, 4, "email", "Contract Review", "Review investment terms")
    ])
    
    conn.commit()
    conn.close()
    print(f"Database initialized with seed data at {DB_PATH}")

def initialize_database():
    """Initialize database with schema and seed data"""
    seed_data()

if __name__ == "__main__":
    initialize_database()
