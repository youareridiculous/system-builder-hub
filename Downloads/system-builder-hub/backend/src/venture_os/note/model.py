from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from datetime import datetime

from pydantic import BaseModel, Field, validator
from venture_os.entity.model import Entity, EntityKind

NoteFormat = Literal["plain", "markdown", "html"]

class Note(BaseModel):
    id: str
    tenant_id: str = Field(..., description="Tenant FK")
    title: str = ""  # short heading; optional
    body: str  # content; markdown by default
    format: NoteFormat = "markdown"
    related_entity_id: Optional[str] = None  # link to any Entity id
    mentions: List[str] = Field(default_factory=list)  # user ids, optional
    tags: List[str] = Field(default_factory=list)
    pinned: bool = False
    status: str = "active"  # active | archived
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived_at: Optional[datetime] = None

    @validator("format", pre=True)
    def validate_format(cls, v):
        return v.lower().strip() if v else "markdown" if v in {"plain", "markdown", "html"} else "markdown"

    @validator("title", "body", pre=True)
    def validate_str(cls, v):
        return str(v).strip() if v else ""

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()

    def archive(self) -> None:
        self.status = "archived"
        self.archived_at = datetime.utcnow()
        self.touch()

    def label(self) -> str:
        return f"note:{self.title}" if self.title else (self.body[:24] + "…") if len(self.body) > 24 else self.body

    def to_entity(self) -> Entity:
        return Entity(
            id=self.id,
            tenant_id=self.tenant_id,
            kind=EntityKind("note"),
            name=self.title or (self.body[:24] + "…") if len(self.body) > 24 else self.body,
            status="archived" if self.archived_at else self.status,
            metadata={
                "format": self.format,
                "related_entity_id": self.related_entity_id,
                "mentions": self.mentions,
                "tags": self.tags,
                "pinned": self.pinned,
                **self.metadata,
            },
            created_at=self.created_at,
            updated_at=self.updated_at,
            archived_at=self.archived_at,
        )

    @classmethod
    def from_entity(cls, e: Entity) -> "Note":
        return cls(
            id=e.id,
            tenant_id=e.tenant_id,
            title=e.name,
            body=e.metadata.get("body", ""),
            format=e.metadata.get("format", "markdown"),
            related_entity_id=e.metadata.get("related_entity_id"),
            mentions=e.metadata.get("mentions", []),
            tags=e.metadata.get("tags", []),
            pinned=e.metadata.get("pinned", False),
            status=e.status,
            created_at=e.created_at,
            updated_at=e.updated_at,
            archived_at=e.archived_at,
        )
