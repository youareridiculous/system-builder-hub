import sqlite3
import json
from passlib.context import CryptContext
from db import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed_auth_data():
    """Seed authentication and RBAC data"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Create permissions
    permissions = [
        ("contacts.read", "Read contacts"),
        ("contacts.write", "Create and edit contacts"),
        ("contacts.delete", "Delete contacts"),
        ("accounts.read", "Read accounts"),
        ("accounts.write", "Create and edit accounts"),
        ("accounts.delete", "Delete accounts"),
        ("deals.read", "Read deals"),
        ("deals.write", "Create and edit deals"),
        ("deals.delete", "Delete deals"),
        ("pipelines.read", "Read pipelines"),
        ("pipelines.write", "Create and edit pipelines"),
        ("activities.read", "Read activities"),
        ("activities.write", "Create and edit activities"),
        ("activities.delete", "Delete activities"),
        ("notes.read", "Read notes"),
        ("notes.write", "Create and edit notes"),
        ("notes.delete", "Delete notes"),
        ("communications.read", "Read communications"),
        ("communications.send", "Send communications (email/sms/call)"),
        ("templates.read", "Read templates"),
        ("templates.write", "Create and edit templates"),
        ("templates.delete", "Delete templates"),
        ("automations.read", "Read automations"),
        ("automations.write", "Create and edit automations"),
        ("automations.delete", "Delete automations"),
        ("analytics.read", "Read analytics"),
        ("settings.read", "Read settings"),
        ("settings.write", "Edit settings"),
        ("webhooks.read", "Read webhook events"),
        ("webhooks.replay", "Replay webhook events"),
        ("users.manage", "Manage users and roles"),
        ("roles.read", "Read roles"),
        ("roles.write", "Create and edit roles"),
        ("permissions.read", "Read permissions"),
    ]
    
    for code, description in permissions:
        cursor.execute("""
            INSERT OR IGNORE INTO permissions (code, description)
            VALUES (?, ?)
        """, (code, description))
    
    # Create roles
    roles = [
        ("Owner", "Full system access", [
            "contacts.read", "contacts.write", "contacts.delete",
            "accounts.read", "accounts.write", "accounts.delete",
            "deals.read", "deals.write", "deals.delete",
            "pipelines.read", "pipelines.write",
            "activities.read", "activities.write", "activities.delete",
            "notes.read", "notes.write", "notes.delete",
            "communications.read", "communications.send",
            "templates.read", "templates.write", "templates.delete",
            "automations.read", "automations.write", "automations.delete",
            "analytics.read",
            "settings.read", "settings.write",
            "webhooks.read", "webhooks.replay",
            "users.manage",
            "roles.read", "roles.write",
            "permissions.read"
        ]),
        ("Admin", "Administrative access", [
            "contacts.read", "contacts.write", "contacts.delete",
            "accounts.read", "accounts.write", "accounts.delete",
            "deals.read", "deals.write", "deals.delete",
            "pipelines.read", "pipelines.write",
            "activities.read", "activities.write", "activities.delete",
            "notes.read", "notes.write", "notes.delete",
            "communications.read", "communications.send",
            "templates.read", "templates.write", "templates.delete",
            "automations.read", "automations.write", "automations.delete",
            "analytics.read",
            "settings.read", "settings.write",
            "webhooks.read", "webhooks.replay",
            "users.manage",
            "roles.read", "roles.write",
            "permissions.read"
        ]),
        ("Manager", "Management access", [
            "contacts.read", "contacts.write",
            "accounts.read", "accounts.write",
            "deals.read", "deals.write",
            "pipelines.read", "pipelines.write",
            "activities.read", "activities.write",
            "notes.read", "notes.write",
            "communications.read", "communications.send",
            "templates.read", "templates.write",
            "automations.read", "automations.write",
            "analytics.read"
        ]),
        ("Sales", "Sales access", [
            "contacts.read", "contacts.write",
            "accounts.read",
            "deals.read", "deals.write",
            "pipelines.read",
            "activities.read", "activities.write",
            "notes.read", "notes.write",
            "communications.read", "communications.send",
            "templates.read"
        ]),
        ("ReadOnly", "Read-only access", [
            "contacts.read",
            "accounts.read",
            "deals.read",
            "pipelines.read",
            "activities.read",
            "notes.read",
            "communications.read",
            "templates.read"
        ])
    ]
    
    role_ids = {}
    for role_name, description, permissions_list in roles:
        cursor.execute("""
            INSERT OR IGNORE INTO roles (name, description, tenant_id)
            VALUES (?, ?, 'demo-tenant')
        """, (role_name, description))
        
        cursor.execute("SELECT id FROM roles WHERE name = ? AND tenant_id = 'demo-tenant'", (role_name,))
        role_id = cursor.fetchone()[0]
        role_ids[role_name] = role_id
        
        # Assign permissions to role
        for permission_code in permissions_list:
            cursor.execute("SELECT id FROM permissions WHERE code = ?", (permission_code,))
            permission_result = cursor.fetchone()
            if permission_result:
                permission_id = permission_result[0]
                cursor.execute("""
                    INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                    VALUES (?, ?)
                """, (role_id, permission_id))
    
    # Create users
    users = [
        ("owner@sbh.dev", "Owner", "Owner!123", ["Owner"]),
        ("admin@sbh.dev", "Admin", "Admin!123", ["Admin"]),
        ("manager@sbh.dev", "Manager", "Manager!123", ["Manager"]),
        ("sales@sbh.dev", "Sales", "Sales!123", ["Sales"]),
        ("readonly@sbh.dev", "ReadOnly", "Read!123", ["ReadOnly"])
    ]
    
    for email, name, password, role_names in users:
        # Hash password
        password_hash = pwd_context.hash(password)
        
        # Create user
        cursor.execute("""
            INSERT OR IGNORE INTO users (email, name, password_hash, tenant_id)
            VALUES (?, ?, ?, 'demo-tenant')
        """, (email, name, password_hash))
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user_id = cursor.fetchone()[0]
        
        # Assign roles to user
        for role_name in role_names:
            role_id = role_ids[role_name]
            cursor.execute("""
                INSERT OR IGNORE INTO user_roles (user_id, role_id)
                VALUES (?, ?)
            """, (user_id, role_id))
    
    conn.commit()
    conn.close()
    
    print("Authentication data seeded successfully!")
    print("\nTest users created:")
    for email, name, password, roles in users:
        print(f"  {email} / {password} ({', '.join(roles)})")

if __name__ == "__main__":
    seed_auth_data()
