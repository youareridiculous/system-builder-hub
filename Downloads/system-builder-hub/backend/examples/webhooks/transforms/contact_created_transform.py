"""
Transform for contact.created webhook
Normalizes and renames fields for external CRM
"""
from typing import Dict, Any
import re

def transform(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform contact.created event data for external CRM
    
    Args:
        event_data: Original event data from SBH CRM
        
    Returns:
        Transformed data for external CRM
    """
    contact = event_data.get('contact', {})
    
    # Normalize phone number
    phone = contact.get('phone', '')
    if phone:
        # Remove all non-digit characters
        phone = re.sub(r'[^\d]', '', phone)
        # Format as (XXX) XXX-XXXX if 10 digits
        if len(phone) == 10:
            phone = f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
    
    # Transform to external CRM format
    transformed = {
        "lead_id": contact.get('id'),
        "first_name": contact.get('first_name', '').strip(),
        "last_name": contact.get('last_name', '').strip(),
        "email_address": contact.get('email', '').lower().strip(),
        "phone_number": phone,
        "company_name": contact.get('company', '').strip(),
        "job_title": contact.get('job_title', '').strip(),
        "lead_source": "SBH CRM",
        "lead_status": "New",
        "tags": contact.get('tags', []),
        "custom_fields": {
            "sbh_contact_id": contact.get('id'),
            "linkedin_url": contact.get('linkedin_url'),
            "notes": contact.get('notes')
        },
        "created_date": contact.get('created_at'),
        "last_modified": contact.get('updated_at')
    }
    
    # Add metadata
    transformed["metadata"] = {
        "source_system": "SBH CRM",
        "tenant_id": event_data.get('tenant_id'),
        "created_by": event_data.get('user_id'),
        "event_timestamp": event_data.get('timestamp')
    }
    
    return transformed
