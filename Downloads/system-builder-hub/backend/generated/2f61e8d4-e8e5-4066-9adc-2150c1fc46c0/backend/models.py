from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

# Authentication Models
class UserBase(BaseModel):
    email: str
    name: str
    tenant_id: str = "demo-tenant"

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserWithRoles(User):
    roles: List[str] = []

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserWithRoles

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    tenant_id: Optional[str] = None

# RBAC Models
class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    tenant_id: str = "demo-tenant"

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Role(RoleBase):
    id: int

    class Config:
        from_attributes = True

class PermissionBase(BaseModel):
    code: str
    description: str

class PermissionCreate(PermissionBase):
    pass

class Permission(PermissionBase):
    id: int

    class Config:
        from_attributes = True

class RoleWithPermissions(Role):
    permissions: List[str] = []

# Existing Models (keeping all existing models)
class AccountBase(BaseModel):
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    tenant_id: str = "demo-tenant"

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None

class Account(AccountBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ContactBase(BaseModel):
    account_id: Optional[int] = None
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    tenant_id: str = "demo-tenant"

class ContactCreate(ContactBase):
    pass

class ContactUpdate(BaseModel):
    account_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None

class Contact(ContactBase):
    id: int
    created_at: datetime
    account_name: Optional[str] = None

    class Config:
        from_attributes = True

class DealBase(BaseModel):
    account_id: Optional[int] = None
    contact_id: Optional[int] = None
    title: str
    amount: Optional[float] = None
    stage: str = "prospecting"
    close_date: Optional[date] = None
    position: int = 0
    tenant_id: str = "demo-tenant"

class DealCreate(DealBase):
    pass

class DealUpdate(BaseModel):
    account_id: Optional[int] = None
    contact_id: Optional[int] = None
    title: Optional[str] = None
    amount: Optional[float] = None
    stage: Optional[str] = None
    close_date: Optional[date] = None
    position: Optional[int] = None

class Deal(DealBase):
    id: int
    created_at: datetime
    account_name: Optional[str] = None
    contact_name: Optional[str] = None

    class Config:
        from_attributes = True

class PipelineBase(BaseModel):
    name: str
    description: Optional[str] = None
    tenant_id: str = "demo-tenant"

class PipelineCreate(PipelineBase):
    pass

class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Pipeline(PipelineBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ActivityBase(BaseModel):
    deal_id: Optional[int] = None
    contact_id: Optional[int] = None
    type: str
    subject: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    completed: bool = False
    tenant_id: str = "demo-tenant"

class ActivityCreate(ActivityBase):
    pass

class ActivityUpdate(BaseModel):
    deal_id: Optional[int] = None
    contact_id: Optional[int] = None
    type: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    completed: Optional[bool] = None

class Activity(ActivityBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class CommunicationProviderBase(BaseModel):
    name: str
    type: str
    provider: str
    config: str
    is_active: bool = True
    tenant_id: str = "demo-tenant"

class CommunicationProviderCreate(CommunicationProviderBase):
    pass

class CommunicationProviderUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    provider: Optional[str] = None
    config: Optional[str] = None
    is_active: Optional[bool] = None

class CommunicationProvider(CommunicationProviderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CommunicationHistoryBase(BaseModel):
    contact_id: int
    account_id: Optional[int] = None
    type: str
    direction: str
    provider: str
    provider_message_id: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    duration: Optional[int] = None
    status: str
    recording_url: Optional[str] = None
    tenant_id: str = "demo-tenant"

class CommunicationHistoryCreate(CommunicationHistoryBase):
    pass

class CommunicationHistoryUpdate(BaseModel):
    contact_id: Optional[int] = None
    account_id: Optional[int] = None
    type: Optional[str] = None
    direction: Optional[str] = None
    provider: Optional[str] = None
    provider_message_id: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    duration: Optional[int] = None
    status: Optional[str] = None
    recording_url: Optional[str] = None

class CommunicationHistory(CommunicationHistoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    account_name: Optional[str] = None

    class Config:
        from_attributes = True

class NoteBase(BaseModel):
    entity_type: str
    entity_id: int
    body: str
    pinned: bool = False
    tenant_id: str = "demo-tenant"

class NoteCreate(BaseModel):
    body: str
    pinned: bool = False

class NoteUpdate(BaseModel):
    body: Optional[str] = None
    pinned: Optional[bool] = None

class Note(NoteBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TemplateBase(BaseModel):
    name: str
    type: str = Field(pattern='^(email|sms)$')
    category: Optional[str] = None
    body: str
    subject: Optional[str] = None
    tokens_detected: Optional[str] = None
    is_archived: bool = False
    tenant_id: str = "demo-tenant"

class TemplateCreate(TemplateBase):
    pass

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = Field(None, pattern='^(email|sms)$')
    category: Optional[str] = None
    body: Optional[str] = None
    subject: Optional[str] = None
    tokens_detected: Optional[str] = None
    is_archived: Optional[bool] = None

class Template(TemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TemplateRender(BaseModel):
    template_id: int
    contact_id: Optional[int] = None
    account_id: Optional[int] = None
    deal_id: Optional[int] = None
    ad_hoc_tokens: Optional[Dict[str, str]] = None

class TemplateTestSend(BaseModel):
    template_id: int
    contact_id: Optional[int] = None
    ad_hoc_tokens: Optional[Dict[str, str]] = None

class AutomationRuleBase(BaseModel):
    name: str
    is_enabled: bool = True
    trigger: str
    conditions: Optional[str] = None
    actions: Optional[str] = None
    tenant_id: str = "demo-tenant"

class AutomationRuleCreate(AutomationRuleBase):
    pass

class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = None
    is_enabled: Optional[bool] = None
    trigger: Optional[str] = None
    conditions: Optional[str] = None
    actions: Optional[str] = None

class AutomationRule(AutomationRuleBase):
    id: int
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AutomationRunBase(BaseModel):
    rule_id: int
    payload: Optional[str] = None
    status: str = Field(pattern='^(success|failed|skipped)$')
    message: Optional[str] = None
    tenant_id: str = "demo-tenant"

class AutomationRunCreate(AutomationRunBase):
    pass

class AutomationRun(AutomationRunBase):
    id: int
    triggered_at: datetime

    class Config:
        from_attributes = True

# Communication Models
class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    contact_id: Optional[int] = None

class SMSRequest(BaseModel):
    phone_number: str
    message: str
    contact_id: Optional[int] = None

class CallRequest(BaseModel):
    phone_number: str
    contact_id: Optional[int] = None

class ProviderStatus(BaseModel):
    email: Optional[Dict[str, Any]] = None
    sms: Optional[Dict[str, Any]] = None
    voice: Optional[Dict[str, Any]] = None
