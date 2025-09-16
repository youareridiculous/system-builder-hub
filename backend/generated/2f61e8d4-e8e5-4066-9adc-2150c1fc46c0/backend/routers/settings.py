import os
import json
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from db import get_db
from routers.auth import check_permission, UserWithRoles, get_current_user
from cryptography.fernet import Fernet
import base64
from seed import initialize_database
from seed_auth import seed_auth_data

router = APIRouter(tags=["settings"])

def get_encryption_key():
    """Get encryption key from AUTH_SECRET"""
    auth_secret = os.getenv('AUTH_SECRET', 'default-secret-key')
    # Derive a 32-byte key from AUTH_SECRET
    key = base64.urlsafe_b64encode(auth_secret.encode()[:32].ljust(32, b'0'))
    return key

def encrypt_value(value: str) -> str:
    """Encrypt a value using AUTH_SECRET"""
    if not value:
        return ""
    key = get_encryption_key()
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()

def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a value using AUTH_SECRET"""
    if not encrypted_value:
        return ""
    try:
        key = get_encryption_key()
        f = Fernet(key)
        return f.decrypt(encrypted_value.encode()).decode()
    except:
        return ""

@router.get("/provider-status")
async def get_provider_status(
    current_user: UserWithRoles = Depends(check_permission("settings.read"))
):
    """Get current provider configuration status"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get provider configs
    cursor.execute("SELECT * FROM provider_configs WHERE tenant_id = ?", (current_user.tenant_id,))
    configs = cursor.fetchall()
    
    conn.close()
    
    # Check environment variables
    sendgrid_key = os.getenv('SENDGRID_API_KEY')
    twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
    twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
    
    status = {
        'email': {
            'mode': 'mock' if not sendgrid_key else 'sendgrid',
            'configured': bool(sendgrid_key),
            'test_available': True
        },
        'sms': {
            'mode': 'mock' if not twilio_sid else 'twilio',
            'configured': bool(twilio_sid and twilio_token),
            'test_available': True
        },
        'voice': {
            'mode': 'mock' if not twilio_sid else 'twilio',
            'configured': bool(twilio_sid and twilio_token),
            'test_available': True
        }
    }
    
    return status

@router.post("/providers/email")
async def update_email_provider(
    api_key: str = Form(...),
    current_user: UserWithRoles = Depends(check_permission("settings.write"))
):
    """Update email provider configuration"""
    # Validate API key (simple check)
    if not api_key.startswith('SG.'):
        raise HTTPException(status_code=400, detail="Invalid SendGrid API key format")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Store encrypted config
    encrypted_key = encrypt_value(api_key)
    
    cursor.execute("""
        INSERT OR REPLACE INTO provider_configs 
        (tenant_id, provider_type, config_key, config_value) 
        VALUES (?, ?, ?, ?)
    """, (current_user.tenant_id, 'email', 'sendgrid_api_key', encrypted_key))
    
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": "Email provider configured successfully"}

@router.post("/providers/sms")
async def update_sms_provider(
    account_sid: str = Form(...),
    auth_token: str = Form(...),
    current_user: UserWithRoles = Depends(check_permission("settings.write"))
):
    """Update SMS provider configuration"""
    # Validate credentials
    if not account_sid.startswith('AC') or not auth_token:
        raise HTTPException(status_code=400, detail="Invalid Twilio credentials")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Store encrypted configs
    encrypted_sid = encrypt_value(account_sid)
    encrypted_token = encrypt_value(auth_token)
    
    cursor.execute("""
        INSERT OR REPLACE INTO provider_configs 
        (tenant_id, provider_type, config_key, config_value) 
        VALUES (?, ?, ?, ?)
    """, (current_user.tenant_id, 'sms', 'twilio_account_sid', encrypted_sid))
    
    cursor.execute("""
        INSERT OR REPLACE INTO provider_configs 
        (tenant_id, provider_type, config_key, config_value) 
        VALUES (?, ?, ?, ?)
    """, (current_user.tenant_id, 'sms', 'twilio_auth_token', encrypted_token))
    
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": "SMS provider configured successfully"}



@router.get("/roles")
async def get_roles(
    current_user: UserWithRoles = Depends(check_permission("settings.read"))
):
    """Get available roles and permissions"""
    return {
        "roles": [
            {
                "name": "Owner",
                "permissions": ["*"]
            },
            {
                "name": "Admin", 
                "permissions": [
                    "accounts.read", "accounts.write",
                    "contacts.read", "contacts.write", 
                    "deals.read", "deals.write",
                    "pipelines.read", "pipelines.write",
                    "activities.read", "activities.write",
                    "communications.read", "communications.write",
                    "templates.read", "templates.write",
                    "automations.read", "automations.write", "automations.run_test",
                    "analytics.read",
                    "settings.read", "settings.write",
                    "webhooks.read", "webhooks.replay"
                ]
            },
            {
                "name": "Manager",
                "permissions": [
                    "accounts.read", "accounts.write",
                    "contacts.read", "contacts.write",
                    "deals.read", "deals.write", 
                    "pipelines.read",
                    "activities.read", "activities.write",
                    "communications.read", "communications.write",
                    "templates.read",
                    "automations.read",
                    "analytics.read"
                ]
            },
            {
                "name": "Sales",
                "permissions": [
                    "contacts.read", "contacts.write",
                    "deals.read", "deals.write",
                    "activities.read", "activities.write",
                    "communications.read", "communications.write",
                    "templates.read",
                    "analytics.read"
                ]
            },
            {
                "name": "ReadOnly",
                "permissions": [
                    "accounts.read",
                    "contacts.read",
                    "deals.read",
                    "pipelines.read",
                    "activities.read",
                    "communications.read",
                    "templates.read",
                    "analytics.read"
                ]
            }
        ]
    }

@router.get("/users")
async def get_users(
    current_user: UserWithRoles = Depends(check_permission("settings.read"))
):
    """Get all users for the current tenant"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT u.id, u.email, u.name, u.is_active,
                   GROUP_CONCAT(r.name) as roles
            FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.tenant_id = ?
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """, (current_user.tenant_id,))
        
        users = []
        for row in cursor.fetchall():
            roles = row['roles'].split(',') if row['roles'] else []
            # Split name into first and last name
            name_parts = row['name'].split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            users.append({
                'id': row['id'],
                'email': row['email'],
                'first_name': first_name,
                'last_name': last_name,
                'is_active': bool(row['is_active']),
                'roles': roles
            })
        
        return users
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")
    finally:
        conn.close()

@router.post("/users/invite")
async def invite_user(
    email: str = Form(...),
    role: str = Form(...),
    current_user: UserWithRoles = Depends(check_permission("settings.write"))
):
    """Invite a new user (dev mode only)"""
    # Check if user has permission to invite
    if not any(perm in current_user.permissions for perm in ["settings.write", "*"]):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create user with temporary password
    import hashlib
    import secrets
    
    temp_password = secrets.token_urlsafe(8)
    hashed_password = hashlib.sha256(temp_password.encode()).hexdigest()
    
    cursor.execute("""
        INSERT INTO users (email, password_hash, first_name, last_name, tenant_id, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (email, hashed_password, "New", "User", current_user.tenant_id, True))
    
    user_id = cursor.lastrowid
    
    # Assign role
    cursor.execute("""
        INSERT INTO user_roles (user_id, role_name)
        VALUES (?, ?)
    """, (user_id, role))
    
    conn.commit()
    conn.close()
    
    return {
        "status": "success",
        "message": f"User invited successfully. Temporary password: {temp_password}",
        "user_id": user_id
    }

@router.get("/branding")
async def get_branding(
    current_user: UserWithRoles = Depends(check_permission("settings.read"))
):
    """Get tenant branding configuration"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT config_key, config_value 
        FROM tenant_configs 
        WHERE tenant_id = ?
    """, (current_user.tenant_id,))
    
    branding = {
        'tenant_name': 'Demo CRM',
        'logo_url': None,
        'primary_color': '#3b82f6',
        'login_subtitle': 'Your complete CRM solution'
    }
    
    for row in cursor.fetchall():
        if row['config_key'] == 'tenant_name':
            branding['tenant_name'] = row['config_value']
        elif row['config_key'] == 'logo_url':
            branding['logo_url'] = row['config_value']
        elif row['config_key'] == 'primary_color':
            branding['primary_color'] = row['config_value']
        elif row['config_key'] == 'login_subtitle':
            branding['login_subtitle'] = row['config_value']
    
    conn.close()
    return branding

@router.post("/branding")
async def update_branding(
    tenant_name: str = Form(...),
    primary_color: str = Form(...),
    login_subtitle: str = Form(...),
    logo: Optional[UploadFile] = File(None),
    current_user: UserWithRoles = Depends(check_permission("settings.write"))
):
    """Update tenant branding"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Handle logo upload
    logo_url = None
    if logo:
        # In a real app, upload to cloud storage
        # For demo, just store the filename
        logo_url = f"/uploads/{logo.filename}"
    
    # Update branding configs
    configs = [
        ('tenant_name', tenant_name),
        ('primary_color', primary_color),
        ('login_subtitle', login_subtitle)
    ]
    
    if logo_url:
        configs.append(('logo_url', logo_url))
    
    for key, value in configs:
        cursor.execute("""
            INSERT OR REPLACE INTO tenant_configs 
            (tenant_id, config_key, config_value) 
            VALUES (?, ?, ?)
        """, (current_user.tenant_id, key, value))
    
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": "Branding updated successfully"}

@router.get("/environment")
async def get_environment_info(
    current_user: UserWithRoles = Depends(check_permission("settings.read"))
):
    """Get environment information"""
    return {
        "feature_flags": {
            "providers_mode": "mock" if not os.getenv('SENDGRID_API_KEY') else "real",
            "auth_secret_present": bool(os.getenv('AUTH_SECRET')),
            "debug_mode": os.getenv('DEBUG', 'false').lower() == 'true'
        },
        "backend_version": "1.0.0",
        "build_id": os.getenv('BUILD_ID', 'dev'),
        "environment": os.getenv('ENVIRONMENT', 'development')
    }

@router.post("/admin/reset-demo")
async def reset_demo_data(
    current_user: UserWithRoles = Depends(check_permission("settings.write"))
):
    """Reset demo data for the current tenant (Owner/Admin only)"""
    # Check if user is Owner or Admin
    if not any(role in ['Owner', 'Admin'] for role in current_user.roles):
        raise HTTPException(
            status_code=403, 
            detail="Only Owner and Admin users can reset demo data"
        )
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Clear all tenant data except users and roles
        tables_to_clear = [
            'communication_history', 'activities', 'notes', 'deals', 
            'contacts', 'accounts', 'webhook_events', 'automation_runs'
        ]
        
        counts = {}
        for table in tables_to_clear:
            cursor.execute(f"DELETE FROM {table} WHERE tenant_id = ?", (current_user.tenant_id,))
            counts[table] = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        # Re-seed the database with fresh connection
        initialize_database()
        seed_auth_data()
        
        return {
            "status": "success",
            "message": "Demo data reset successfully",
            "cleared_records": counts
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        raise HTTPException(status_code=500, detail=f"Failed to reset demo data: {str(e)}")

@router.post("/checklist-complete")
async def mark_checklist_complete(
    request: dict,
    current_user: UserWithRoles = Depends(check_permission("settings.write"))
):
    item_id = request.get("item_id")
    completed = request.get("completed", False)
    """Mark a checklist item as complete for the current tenant"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO tenant_configs 
            (tenant_id, config_key, config_value) 
            VALUES (?, ?, ?)
        """, (current_user.tenant_id, f"checklist_{item_id}", str(completed).lower()))
        
        conn.commit()
        
        return {
            "status": "success",
            "message": f"Checklist item '{item_id}' marked as {'complete' if completed else 'incomplete'}"
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update checklist: {str(e)}")
    finally:
        conn.close()

@router.get("/checklist-status")
async def get_checklist_status(
    current_user: UserWithRoles = Depends(check_permission("settings.read"))
):
    """Get checklist completion status for the current tenant"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT config_key, config_value 
            FROM tenant_configs 
            WHERE tenant_id = ? AND config_key LIKE 'checklist_%'
        """, (current_user.tenant_id,))
        
        checklist_items = {}
        for row in cursor.fetchall():
            item_id = row['config_key'].replace('checklist_', '')
            checklist_items[item_id] = row['config_value'] == 'true'
        
        return {
            "checklist_items": checklist_items
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get checklist status: {str(e)}")
    finally:
        conn.close()

@router.get("/branding")
async def get_branding(
    current_user: UserWithRoles = Depends(check_permission("settings.read"))
):
    """Get branding settings for the current tenant"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT config_key, config_value 
            FROM tenant_configs 
            WHERE tenant_id = ? AND config_key IN ('tenant_name', 'logo_url', 'primary_color')
        """, (current_user.tenant_id,))
        
        branding = {
            'tenant_name': '',
            'logo_url': '',
            'primary_color': '#3b82f6'
        }
        
        for row in cursor.fetchall():
            if row['config_key'] == 'tenant_name':
                branding['tenant_name'] = row['config_value'] or ''
            elif row['config_key'] == 'logo_url':
                branding['logo_url'] = row['config_value'] or ''
            elif row['config_key'] == 'primary_color':
                branding['primary_color'] = row['config_value'] or '#3b82f6'
        
        return branding
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get branding settings: {str(e)}")
    finally:
        conn.close()

@router.post("/branding")
async def update_branding(
    request: dict,
    current_user: UserWithRoles = Depends(check_permission("settings.write"))
):
    """Update branding settings for the current tenant"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Validate input
        tenant_name = request.get('tenant_name', '')
        logo_url = request.get('logo_url', '')
        primary_color = request.get('primary_color', '#3b82f6')
        
        # Basic validation
        if primary_color and not primary_color.startswith('#'):
            raise HTTPException(status_code=400, detail="Primary color must be a valid hex color")
        
        # Update branding settings
        branding_configs = [
            ('tenant_name', tenant_name),
            ('logo_url', logo_url),
            ('primary_color', primary_color)
        ]
        
        for config_key, config_value in branding_configs:
            cursor.execute("""
                INSERT OR REPLACE INTO tenant_configs 
                (tenant_id, config_key, config_value) 
                VALUES (?, ?, ?)
            """, (current_user.tenant_id, config_key, config_value))
        
        conn.commit()
        
        return {
            "status": "success",
            "message": "Branding settings updated successfully"
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update branding settings: {str(e)}")
    finally:
        conn.close()
