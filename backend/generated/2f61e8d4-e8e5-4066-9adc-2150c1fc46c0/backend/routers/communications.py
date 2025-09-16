from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
from pydantic import BaseModel, constr, Field, validator
from enum import Enum
from db import get_db
from providers.provider_factory import ProviderFactory
from routers.auth import check_permission, UserWithRoles

# Enums for validation
class CommunicationType(str, Enum):
    email = "email"
    sms = "sms"
    call = "call"

class CommunicationStatus(str, Enum):
    queued = "queued"
    sent = "sent"
    delivered = "delivered"
    failed = "failed"
    initiated = "initiated"
    completed = "completed"
    missed = "missed"
    recording_ready = "recording_ready"

# Request models with proper validation
class EmailRequest(BaseModel):
    to_email: str = Field(..., description="Recipient email address")
    subject: constr(min_length=1, max_length=200) = Field(..., description="Email subject")
    body: constr(min_length=1) = Field(..., description="Email body content")
    contact_id: int = Field(..., description="Contact ID")
    template_id: Optional[int] = Field(None, description="Optional template ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional template context")
    
    @validator('to_email')
    def validate_email(cls, v):
        if '@' not in v or '.' not in v:
            raise ValueError('Invalid email format')
        return v

class SMSRequest(BaseModel):
    to_phone: str = Field(..., description="Recipient phone number")
    message: constr(min_length=1, max_length=1000) = Field(..., description="SMS message content")
    contact_id: int = Field(..., description="Contact ID")
    template_id: Optional[int] = Field(None, description="Optional template ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional template context")
    
    @validator('to_phone')
    def validate_phone(cls, v):
        import re
        if not re.match(r'^\+?[1-9]\d{6,15}$', v):
            raise ValueError('Invalid phone number format')
        return v

class CallRequest(BaseModel):
    to_phone: str = Field(..., description="Recipient phone number")
    contact_id: int = Field(..., description="Contact ID")
    from_phone: Optional[str] = Field(None, description="Optional caller phone number")
    record: bool = Field(True, description="Whether to record the call")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional call metadata")
    
    @validator('to_phone')
    def validate_phone(cls, v):
        import re
        if not re.match(r'^\+?[1-9]\d{6,15}$', v):
            raise ValueError('Invalid phone number format')
        return v

router = APIRouter(tags=["communications"])

# Communication History
@router.get("/history")
async def get_communication_history(
    contact_id: Optional[int] = None,
    account_id: Optional[int] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 25,
    offset: int = 0,
    current_user: UserWithRoles = Depends(check_permission("communications.read"))
):
    """Get communication history with optional filters"""
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT ch.*, c.first_name, c.last_name, a.name as account_name
        FROM communication_history ch
        LEFT JOIN contacts c ON ch.contact_id = c.id
        LEFT JOIN accounts a ON ch.account_id = a.id
        WHERE 1=1
    """
    params = []
    
    if contact_id:
        query += " AND ch.contact_id = ?"
        params.append(contact_id)
    if account_id:
        query += " AND ch.account_id = ?"
        params.append(account_id)
    if type:
        query += " AND ch.type = ?"
        params.append(type)
    if status:
        query += " AND ch.status = ?"
        params.append(status)
    if date_from:
        query += " AND DATE(ch.created_at) >= ?"
        params.append(date_from)
    if date_to:
        query += " AND DATE(ch.created_at) <= ?"
        params.append(date_to)
    
    query += " ORDER BY ch.created_at DESC LIMIT ? OFFSET ?"
    params.append(limit)
    params.append(offset)
    
    cursor.execute(query, params)
    
    history = []
    for row in cursor.fetchall():
        item = dict(row)
        history.append(item)
    
    conn.close()
    return history

@router.post("/send-email")
async def send_email(
    request: EmailRequest,
    current_user: UserWithRoles = Depends(check_permission("communications.send"))
):
    """Send an email using configured provider"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get the email provider
    email_provider = ProviderFactory.get_email_provider()
    
    # Send the email
    result = email_provider.send_email(
        to_email=request.to_email,
        subject=request.subject,
        body=request.body
    )
    
    # Record the communication
    cursor.execute("""
        INSERT INTO communication_history 
        (contact_id, type, direction, provider, subject, content, status, provider_message_id)
        VALUES (?, 'email', 'outbound', ?, ?, ?, ?, ?)
    """, (
        request.contact_id, 
        ProviderFactory.get_provider_status()['email'],
        request.subject, 
        request.body, 
        result['status'],
        result.get('provider_message_id')
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "provider_message_id": "mock_email_123",
        "status": "sent"
    }

@router.post("/initiate-call")
async def initiate_call(
    request: CallRequest,
    current_user: UserWithRoles = Depends(check_permission("communications.send"))
):
    """Initiate a call using configured provider"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get the voice provider
    voice_provider = ProviderFactory.get_voice_provider()
    
    # Initiate the call
    result = voice_provider.initiate_call(
        to_number=request.to_phone
    )
    
    # Record the communication
    cursor.execute("""
        INSERT INTO communication_history 
        (contact_id, type, direction, provider, status, provider_message_id)
        VALUES (?, 'call', 'outbound', ?, ?, ?)
    """, (
        request.contact_id,
        ProviderFactory.get_provider_status()['voice'],
        result['status'],
        result.get('provider_message_id')
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "provider_message_id": "mock_call_123",
        "status": "initiated"
    }

@router.post("/send-sms")
async def send_sms(
    request: SMSRequest,
    current_user: UserWithRoles = Depends(check_permission("communications.send"))
):
    """Send an SMS using configured provider"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get the SMS provider
    sms_provider = ProviderFactory.get_sms_provider()
    
    # Send the SMS
    result = sms_provider.send_sms(
        to_number=request.to_phone,
        message=request.message
    )
    
    # Record the communication
    cursor.execute("""
        INSERT INTO communication_history 
        (contact_id, type, direction, provider, content, status, provider_message_id)
        VALUES (?, 'sms', 'outbound', ?, ?, ?, ?)
    """, (
        request.contact_id,
        ProviderFactory.get_provider_status()['sms'],
        request.message,
        result['status'],
        result.get('provider_message_id')
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "provider_message_id": "mock_sms_123",
        "status": "sent"
    }

@router.get("/provider-status")
async def get_provider_status():
    """Get the status of all communication providers"""
    return ProviderFactory.get_provider_status()
