from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime

# Account Models
class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    industry: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=200)

class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    industry: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=200)

# Contact Models
class ContactCreate(BaseModel):
    account_id: Optional[int] = None
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    title: Optional[str] = Field(None, max_length=100)

class ContactUpdate(BaseModel):
    account_id: Optional[int] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    title: Optional[str] = Field(None, max_length=100)

# Deal Models
class DealCreate(BaseModel):
    account_id: Optional[int] = None
    contact_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    amount: Optional[float] = Field(None, ge=0)
    stage: str = Field(default="prospecting", max_length=50)
    close_date: Optional[date] = None

class DealUpdate(BaseModel):
    account_id: Optional[int] = None
    contact_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    amount: Optional[float] = Field(None, ge=0)
    stage: Optional[str] = Field(None, max_length=50)
    close_date: Optional[date] = None

# Pipeline Models
class PipelineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class PipelineUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

# Activity Models
class ActivityCreate(BaseModel):
    deal_id: Optional[int] = None
    contact_id: Optional[int] = None
    type: str = Field(..., max_length=50)
    subject: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    due_date: Optional[date] = None
    completed: bool = Field(default=False)

class ActivityUpdate(BaseModel):
    deal_id: Optional[int] = None
    contact_id: Optional[int] = None
    type: Optional[str] = Field(None, max_length=50)
    subject: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    due_date: Optional[date] = None
    completed: Optional[bool] = None
