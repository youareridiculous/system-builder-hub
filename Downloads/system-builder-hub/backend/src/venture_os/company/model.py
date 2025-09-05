from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
from venture_os.entity.model import Entity, EntityKind

class Company(BaseModel):
    """
    Multi-tenant, exit-ready, storage-agnostic Company model.
    """

    id: str
    tenant_id: str = Field(..., description="Foreign key to tenant")
    name: str
    domain: Optional[str] = None  # e.g., acme.com
    ein: Optional[str] = None  # US tax ID; string, not parsed
    stage: str = "active"  # e.g., idea | operating | scaling | paused | exited
    tags: List[str] = Field(default_factory=list)
    primary_email: Optional[EmailStr] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived_at: Optional[datetime] = None

    @validator("domain")
    def normalize_domain(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.strip().lower()
        return v

    def to_entity(self) -> Entity:
        return Entity(
            id=self.id,
            tenant_id=self.tenant_id,
            kind=EntityKind("company"),
            name=self.name,
            status="archived" if self.archived_at else self.stage,
            metadata={
                "domain": self.domain,
                "ein": self.ein,
                "tags": self.tags,
                "primary_email": self.primary_email,
            },
        )

    @classmethod
    def from_entity(cls, e: Entity) -> "Company":
        return cls(
            id=e.id,
            tenant_id=e.tenant_id,
            name=e.name,
            domain=e.metadata.get("domain"),
            ein=e.metadata.get("ein"),
            stage=e.status,
            tags=e.metadata.get("tags", []),
            primary_email=e.metadata.get("primary_email"),
            metadata=e.metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            archived_at=e.metadata.get("archived_at"),
        )

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()

    def archive(self) -> None:
        self.stage = "archived"
        self.archived_at = datetime.utcnow()
        self.touch()

    def label(self) -> str:
        return f"company:{self.name} ({self.domain or 'no-domain'})"