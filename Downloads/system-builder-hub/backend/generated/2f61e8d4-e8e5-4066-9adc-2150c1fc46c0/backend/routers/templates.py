import re
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from db import get_db
from models import Template, TemplateCreate, TemplateUpdate, TemplateRender, TemplateTestSend, UserWithRoles
from routers.auth import check_permission, get_current_user
from providers.provider_factory import ProviderFactory

router = APIRouter(tags=["templates"])

def extract_tokens(text: str) -> List[str]:
    """Extract tokens like {contact.first_name} from text"""
    pattern = r'\{([^}]+)\}'
    tokens = re.findall(pattern, text)
    return list(set(tokens))  # Remove duplicates

def render_template(template_body: str, template_subject: str, context: dict) -> tuple[str, str]:
    """Render template with token substitution"""
    rendered_body = template_body
    rendered_subject = template_subject or ""
    
    # Replace tokens with context values
    for token, value in context.items():
        placeholder = f"{{{token}}}"
        rendered_body = rendered_body.replace(placeholder, str(value) if value is not None else "")
        rendered_subject = rendered_subject.replace(placeholder, str(value) if value is not None else "")
    
    return rendered_subject, rendered_body

def build_context(contact_id: Optional[int] = None, account_id: Optional[int] = None, 
                  deal_id: Optional[int] = None, ad_hoc_tokens: Optional[dict] = None) -> dict:
    """Build context dictionary for template rendering"""
    context = {}
    
    # Add ad-hoc tokens first
    if ad_hoc_tokens:
        context.update(ad_hoc_tokens)
    
    # Add contact data
    if contact_id:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT first_name, last_name, email, phone, title FROM contacts WHERE id = ?", (contact_id,))
        contact = cursor.fetchone()
        if contact:
            context.update({
                'contact.first_name': contact['first_name'],
                'contact.last_name': contact['last_name'],
                'contact.email': contact['email'],
                'contact.phone': contact['phone'],
                'contact.title': contact['title'],
                'contact.full_name': f"{contact['first_name']} {contact['last_name']}"
            })
    
    # Add account data
    if account_id:
        cursor.execute("SELECT name, industry, website FROM accounts WHERE id = ?", (account_id,))
        account = cursor.fetchone()
        if account:
            context.update({
                'account.name': account['name'],
                'account.industry': account['industry'],
                'account.website': account['website']
            })
    
    # Add deal data
    if deal_id:
        cursor.execute("SELECT title, amount, stage, close_date FROM deals WHERE id = ?", (deal_id,))
        deal = cursor.fetchone()
        if deal:
            context.update({
                'deal.title': deal['title'],
                'deal.amount': f"${deal['amount']:,.2f}" if deal['amount'] else "N/A",
                'deal.stage': deal['stage'],
                'deal.close_date': deal['close_date']
            })
    
    # Add user/tenant data
    context.update({
        'user.name': 'Current User',  # Would come from auth context
        'tenant.name': 'Demo Tenant',
        'date.today': '2025-01-15',  # Would be dynamic
        'date.now': '2025-01-15 10:30:00'
    })
    
    return context

@router.get("/tokens")
def get_available_tokens(current_user: UserWithRoles = Depends(check_permission("templates.read"))):
    """Get list of available tokens with examples"""
    tokens = {
        "contact": {
            "contact.first_name": "John",
            "contact.last_name": "Doe", 
            "contact.email": "john.doe@example.com",
            "contact.phone": "+1234567890",
            "contact.title": "Sales Manager",
            "contact.full_name": "John Doe"
        },
        "account": {
            "account.name": "Acme Corp",
            "account.industry": "Technology",
            "account.website": "https://acme.com"
        },
        "deal": {
            "deal.title": "Enterprise License",
            "deal.amount": "$50,000.00",
            "deal.stage": "proposal",
            "deal.close_date": "2025-02-15"
        },
        "user": {
            "user.name": "Current User"
        },
        "tenant": {
            "tenant.name": "Demo Tenant"
        },
        "date": {
            "date.today": "2025-01-15",
            "date.now": "2025-01-15 10:30:00"
        }
    }
    
    return {
        "tokens": tokens,
        "example_context": build_context(1, 1, 1)  # Example with sample data
    }

@router.get("/")
def list_templates(
    search: Optional[str] = None,
    type_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    include_archived: bool = False,
    current_user: UserWithRoles = Depends(check_permission("templates.read"))
):
    """List templates with filtering"""
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT * FROM templates 
        WHERE tenant_id = ?
    """
    params = [current_user.tenant_id]
    
    if not include_archived:
        query += " AND is_archived = 0"
    
    if search:
        query += " AND (name LIKE ? OR body LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    
    if type_filter:
        query += " AND type = ?"
        params.append(type_filter)
    
    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)
    
    query += " ORDER BY created_at DESC"
    
    cursor.execute(query, params)
    templates = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return templates

@router.get("/{template_id}")
def get_template(
    template_id: int,
    current_user: UserWithRoles = Depends(check_permission("templates.read"))
):
    """Get a specific template"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM templates WHERE id = ? AND tenant_id = ?", 
        (template_id, current_user.tenant_id)
    )
    template = cursor.fetchone()
    conn.close()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return dict(template)

@router.post("/")
def create_template(
    template: TemplateCreate,
    current_user: UserWithRoles = Depends(check_permission("templates.write"))
):
    """Create a new template"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Extract tokens from body and subject
    tokens = extract_tokens(template.body)
    if template.subject:
        tokens.extend(extract_tokens(template.subject))
    tokens = list(set(tokens))  # Remove duplicates
    
    cursor.execute("""
        INSERT INTO templates (name, type, category, body, subject, tokens_detected, tenant_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        template.name, template.type, template.category, template.body, 
        template.subject, json.dumps(tokens), current_user.tenant_id
    ))
    
    template_id = cursor.lastrowid
    conn.commit()
    
    # Return created template
    cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
    created_template = cursor.fetchone()
    conn.close()
    
    return dict(created_template)

@router.put("/{template_id}")
def update_template(
    template_id: int,
    template: TemplateUpdate,
    current_user: UserWithRoles = Depends(check_permission("templates.write"))
):
    """Update a template"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if template exists and belongs to tenant
    cursor.execute(
        "SELECT * FROM templates WHERE id = ? AND tenant_id = ?", 
        (template_id, current_user.tenant_id)
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Build update query
    update_fields = []
    params = []
    
    if template.name is not None:
        update_fields.append("name = ?")
        params.append(template.name)
    
    if template.type is not None:
        update_fields.append("type = ?")
        params.append(template.type)
    
    if template.category is not None:
        update_fields.append("category = ?")
        params.append(template.category)
    
    if template.body is not None:
        update_fields.append("body = ?")
        params.append(template.body)
    
    if template.subject is not None:
        update_fields.append("subject = ?")
        params.append(template.subject)
    
    if template.is_archived is not None:
        update_fields.append("is_archived = ?")
        params.append(template.is_archived)
    
    if update_fields:
        # Extract tokens if body or subject changed
        if template.body is not None or template.subject is not None:
            # Get current template to extract tokens
            cursor.execute("SELECT body, subject FROM templates WHERE id = ?", (template_id,))
            current = cursor.fetchone()
            body = template.body if template.body is not None else current['body']
            subject = template.subject if template.subject is not None else current['subject']
            
            tokens = extract_tokens(body)
            if subject:
                tokens.extend(extract_tokens(subject))
            tokens = list(set(tokens))
            
            update_fields.append("tokens_detected = ?")
            params.append(json.dumps(tokens))
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(template_id)
        
        query = f"UPDATE templates SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
    
    # Return updated template
    cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
    updated_template = cursor.fetchone()
    conn.close()
    
    return dict(updated_template)

@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    current_user: UserWithRoles = Depends(check_permission("templates.write"))
):
    """Soft delete (archive) a template"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE templates SET is_archived = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND tenant_id = ?",
        (template_id, current_user.tenant_id)
    )
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Template not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "Template archived successfully"}

@router.post("/{template_id}/restore")
def restore_template(
    template_id: int,
    current_user: UserWithRoles = Depends(check_permission("templates.write"))
):
    """Restore an archived template"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE templates SET is_archived = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND tenant_id = ?",
        (template_id, current_user.tenant_id)
    )
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Template not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "Template restored successfully"}

@router.post("/{template_id}/clone")
def clone_template(
    template_id: int,
    current_user: UserWithRoles = Depends(check_permission("templates.write"))
):
    """Clone a template"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM templates WHERE id = ? AND tenant_id = ?", 
        (template_id, current_user.tenant_id)
    )
    template = cursor.fetchone()
    
    if not template:
        conn.close()
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Create clone
    cursor.execute("""
        INSERT INTO templates (name, type, category, body, subject, tokens_detected, tenant_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        f"{template['name']} (Copy)", template['type'], template['category'], 
        template['body'], template['subject'], template['tokens_detected'], 
        current_user.tenant_id
    ))
    
    new_template_id = cursor.lastrowid
    conn.commit()
    
    # Return cloned template
    cursor.execute("SELECT * FROM templates WHERE id = ?", (new_template_id,))
    cloned_template = cursor.fetchone()
    conn.close()
    
    return dict(cloned_template)

@router.post("/render")
def render_template_endpoint(
    request: TemplateRender,
    current_user: UserWithRoles = Depends(check_permission("templates.read"))
):
    """Render a template with context"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM templates WHERE id = ? AND tenant_id = ?", 
        (request.template_id, current_user.tenant_id)
    )
    template = cursor.fetchone()
    
    if not template:
        conn.close()
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Build context
    context = build_context(
        request.contact_id, 
        request.account_id, 
        request.deal_id, 
        request.ad_hoc_tokens
    )
    
    # Render template
    rendered_subject, rendered_body = render_template(
        template['body'], 
        template['subject'] or "", 
        context
    )
    
    conn.close()
    
    return {
        "subject": rendered_subject,
        "body": rendered_body,
        "context": context,
        "missing_tokens": [token for token in extract_tokens(template['body']) if token not in context]
    }

@router.post("/test-email")
def test_send_email(
    request: TemplateTestSend,
    current_user: UserWithRoles = Depends(check_permission("templates.send_test"))
):
    """Send a test email using the template"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM templates WHERE id = ? AND tenant_id = ? AND type = 'email'", 
        (request.template_id, current_user.tenant_id)
    )
    template = cursor.fetchone()
    
    if not template:
        conn.close()
        raise HTTPException(status_code=404, detail="Email template not found")
    
    # Build context
    context = build_context(request.contact_id, None, None, request.ad_hoc_tokens)
    
    # Render template
    rendered_subject, rendered_body = render_template(
        template['body'], 
        template['subject'] or "", 
        context
    )
    
    # Send via provider
    try:
        provider = ProviderFactory.get_email_provider()
        result = provider.send_email(
            to=context.get('contact.email', 'test@example.com'),
            subject=rendered_subject,
            body=rendered_body
        )
        
        # Log to communication history
        cursor.execute("""
            INSERT INTO communication_history 
            (contact_id, type, direction, provider, subject, content, status, tenant_id)
            VALUES (?, 'email', 'outbound', ?, ?, ?, 'sent', ?)
        """, (
            request.contact_id, 
            provider.__class__.__name__, 
            rendered_subject, 
            rendered_body, 
            current_user.tenant_id
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Test email sent successfully",
            "provider_result": result
        }
        
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Failed to send test email: {str(e)}")

@router.post("/test-sms")
def test_send_sms(
    request: TemplateTestSend,
    current_user: UserWithRoles = Depends(check_permission("templates.send_test"))
):
    """Send a test SMS using the template"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM templates WHERE id = ? AND tenant_id = ? AND type = 'sms'", 
        (request.template_id, current_user.tenant_id)
    )
    template = cursor.fetchone()
    
    if not template:
        conn.close()
        raise HTTPException(status_code=404, detail="SMS template not found")
    
    # Build context
    context = build_context(request.contact_id, None, None, request.ad_hoc_tokens)
    
    # Render template
    rendered_subject, rendered_body = render_template(
        template['body'], 
        "", 
        context
    )
    
    # Send via provider
    try:
        provider = ProviderFactory.get_sms_provider()
        result = provider.send_sms(
            phone_number=context.get('contact.phone', '+1234567890'),
            message=rendered_body
        )
        
        # Log to communication history
        cursor.execute("""
            INSERT INTO communication_history 
            (contact_id, type, direction, provider, content, status, tenant_id)
            VALUES (?, 'sms', 'outbound', ?, ?, 'sent', ?)
        """, (
            request.contact_id, 
            provider.__class__.__name__, 
            rendered_body, 
            current_user.tenant_id
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Test SMS sent successfully",
            "provider_result": result
        }
        
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Failed to send test SMS: {str(e)}")
