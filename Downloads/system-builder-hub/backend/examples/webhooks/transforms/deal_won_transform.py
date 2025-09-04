"""
Transform for deal.won webhook
Formats deal data for Zapier integration
"""
from typing import Dict, Any

def transform(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform deal.won event data for Zapier
    
    Args:
        event_data: Original event data from SBH CRM
        
    Returns:
        Transformed data for Zapier
    """
    deal = event_data.get('deal', {})
    
    # Transform to Zapier-friendly format
    transformed = {
        "event_type": "deal.won",
        "deal_id": deal.get('id'),
        "deal_title": deal.get('title'),
        "deal_value": deal.get('value'),
        "deal_stage": deal.get('pipeline_stage'),
        "owner_id": deal.get('owner_id'),
        "owner_name": deal.get('owner_name'),
        "contact_id": deal.get('contact_id'),
        "contact_name": deal.get('contact_name'),
        "company": deal.get('company'),
        "won_at": deal.get('closed_at'),
        "created_at": deal.get('created_at'),
        "updated_at": deal.get('updated_at'),
        "custom_fields": deal.get('custom_fields', {}),
        "tags": deal.get('tags', [])
    }
    
    # Add metadata
    transformed["metadata"] = {
        "source": "SBH CRM",
        "tenant_id": event_data.get('tenant_id'),
        "user_id": event_data.get('user_id'),
        "timestamp": event_data.get('timestamp')
    }
    
    return transformed
