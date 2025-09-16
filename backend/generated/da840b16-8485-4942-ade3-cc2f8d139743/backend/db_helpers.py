import sqlite3
from typing import Dict, Any, Optional, List
from db import get_db

def create_account(data: Dict[str, Any]) -> int:
    """Create a new account"""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO accounts (name, industry, website) VALUES (?, ?, ?)",
        (data['name'], data.get('industry'), data.get('website'))
    )
    account_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return account_id

def update_account(account_id: int, data: Dict[str, Any]) -> bool:
    """Update an account"""
    conn = get_db()
    updates = []
    values = []
    
    for key, value in data.items():
        if value is not None:
            updates.append(f"{key} = ?")
            values.append(value)
    
    if not updates:
        conn.close()
        return False
    
    values.append(account_id)
    query = f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?"
    cursor = conn.execute(query, values)
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def delete_account(account_id: int) -> bool:
    """Delete an account"""
    conn = get_db()
    cursor = conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def create_contact(data: Dict[str, Any]) -> int:
    """Create a new contact"""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO contacts (account_id, first_name, last_name, email, phone, title) VALUES (?, ?, ?, ?, ?, ?)",
        (data.get('account_id'), data['first_name'], data['last_name'], 
         data.get('email'), data.get('phone'), data.get('title'))
    )
    contact_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return contact_id

def update_contact(contact_id: int, data: Dict[str, Any]) -> bool:
    """Update a contact"""
    conn = get_db()
    updates = []
    values = []
    
    for key, value in data.items():
        if value is not None:
            updates.append(f"{key} = ?")
            values.append(value)
    
    if not updates:
        conn.close()
        return False
    
    values.append(contact_id)
    query = f"UPDATE contacts SET {', '.join(updates)} WHERE id = ?"
    cursor = conn.execute(query, values)
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def delete_contact(contact_id: int) -> bool:
    """Delete a contact"""
    conn = get_db()
    cursor = conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def create_deal(data: Dict[str, Any]) -> int:
    """Create a new deal"""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO deals (account_id, contact_id, title, amount, stage, close_date) VALUES (?, ?, ?, ?, ?, ?)",
        (data.get('account_id'), data.get('contact_id'), data['title'],
         data.get('amount'), data.get('stage', 'prospecting'), data.get('close_date'))
    )
    deal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return deal_id

def update_deal(deal_id: int, data: Dict[str, Any]) -> bool:
    """Update a deal"""
    conn = get_db()
    updates = []
    values = []
    
    for key, value in data.items():
        if value is not None:
            updates.append(f"{key} = ?")
            values.append(value)
    
    if not updates:
        conn.close()
        return False
    
    values.append(deal_id)
    query = f"UPDATE deals SET {', '.join(updates)} WHERE id = ?"
    cursor = conn.execute(query, values)
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def delete_deal(deal_id: int) -> bool:
    """Delete a deal"""
    conn = get_db()
    cursor = conn.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def create_pipeline(data: Dict[str, Any]) -> int:
    """Create a new pipeline"""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO pipelines (name, description) VALUES (?, ?)",
        (data['name'], data.get('description'))
    )
    pipeline_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return pipeline_id

def update_pipeline(pipeline_id: int, data: Dict[str, Any]) -> bool:
    """Update a pipeline"""
    conn = get_db()
    updates = []
    values = []
    
    for key, value in data.items():
        if value is not None:
            updates.append(f"{key} = ?")
            values.append(value)
    
    if not updates:
        conn.close()
        return False
    
    values.append(pipeline_id)
    query = f"UPDATE pipelines SET {', '.join(updates)} WHERE id = ?"
    cursor = conn.execute(query, values)
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def delete_pipeline(pipeline_id: int) -> bool:
    """Delete a pipeline"""
    conn = get_db()
    cursor = conn.execute("DELETE FROM pipelines WHERE id = ?", (pipeline_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def create_activity(data: Dict[str, Any]) -> int:
    """Create a new activity"""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO activities (deal_id, contact_id, type, subject, description, due_date, completed) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data.get('deal_id'), data.get('contact_id'), data['type'], data['subject'],
         data.get('description'), data.get('due_date'), data.get('completed', False))
    )
    activity_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return activity_id

def update_activity(activity_id: int, data: Dict[str, Any]) -> bool:
    """Update an activity"""
    conn = get_db()
    updates = []
    values = []
    
    for key, value in data.items():
        if value is not None:
            updates.append(f"{key} = ?")
            values.append(value)
    
    if not updates:
        conn.close()
        return False
    
    values.append(activity_id)
    query = f"UPDATE activities SET {', '.join(updates)} WHERE id = ?"
    cursor = conn.execute(query, values)
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def delete_activity(activity_id: int) -> bool:
    """Delete an activity"""
    conn = get_db()
    cursor = conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
