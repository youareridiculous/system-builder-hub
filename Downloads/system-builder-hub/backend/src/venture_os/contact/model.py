from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime

from pydantic import BaseModel, Field, EmailStr, validator
from venture_os.entity.model import Entity, EntityKind

class Contact(BaseModel):
    """
    Multi-tenant, exit-ready, storage-agnostic contact model.
    """

    id: str
    tenant_id: str = Field(..., description="Tenant FK")
    company_id: Optional[str] = None
    first_name: str = ""
    last_name: str = ""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    title: str = ""
    notes: str = ""
    status: str = "active"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived_at: Optional[datetime] = None

    @validator("email", pre=True)
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return v.lower().strip()
        return v

    @validator("phone", pre=True)
    def normalize_phone(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return ''.join(filter(str.isdigit, v))
        return v

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def label(self) -> str:
        return f"contact:{self.full_name() or (self.email or 'unknown')}"

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()

    def archive(self) -> None:
        self.status = "archived"
        self.archived_at = datetime.utcnow()
        self.touch()

    def to_entity(self) -> Entity:
        return Entity(
            id=self.id,
            tenant_id=self.tenant_id,
            kind=EntityKind("contact"),
            name=self.full_name() or (self.email or "contact"),
            status="archived" if self.archived_at else self.status,
            metadata={
                "company_id": self.company_id,
                "email": str(self.email) if self.email else None,
                "phone": self.phone,
                "title": self.title,
                "notes": self.notes,
                **self.metadata
            },
            created_at=self.created_at,
            updated_at=self.updated_at,
            archived_at=self.archived_at
        )

    @classmethod
    def from_entity(cls, e: Entity) -> "Contact":
        return cls(
            id=e.id,
            tenant_id=e.tenant_id,
            company_id=e.metadata.get("company_id"),
            first_name=e.metadata.get("first_name", ""),
            last_name=e.metadata.get("last_name", ""),
            email=e.metadata.get("email"),
            phone=e.metadata.get("phone"),
            title=e.metadata.get("title", ""),
            notes=e.metadata.get("notes", ""),
            status=e.status,
            metadata={k: v for k, v in e.metadata.items() if k not in {"company_id", "email", "phone", "title", "notes"}},
            created_at=e.created_at,
            updated_at=e.updated_at,
            archived_at=e.archived_at
        )
