#!/usr/bin/env python3
"""
Test to see what database the server is using
"""

import os
from src.db_core import get_database_url
from src.billing.service import BillingService

print("Current working directory:", os.getcwd())
print("Database URL:", get_database_url())

# Test billing service
billing = BillingService()
print("Billing service database URL:", billing.database_url)

# Check if database file exists
db_path = get_database_url().replace('sqlite:///', '')
if db_path.startswith('./'):
    db_path = db_path[2:]
print("Database file path:", db_path)
print("Database file exists:", os.path.exists(db_path))

# Check if tables exist
import sqlite3
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='billing_subscriptions'")
    result = cursor.fetchone()
    print("billing_subscriptions table exists:", result is not None)
    
    if result:
        cursor.execute("SELECT COUNT(*) FROM billing_subscriptions")
        count = cursor.fetchone()[0]
        print("Number of billing subscriptions:", count)
    
    conn.close()
except Exception as e:
    print("Error checking database:", e)
