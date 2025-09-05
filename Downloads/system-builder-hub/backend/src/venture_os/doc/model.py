from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, List, Optional
import hashlib

from pydantic import BaseModel, Field, validator
from venture_os.entity.model import Entity, EntityKind

class Doc(BaseModel):
    id: str
    tenant_id: str = Field(..., description="Tenant FK")
    name: str  # human title, e.g., “MSA — Acme 2025”
    mime_type: str = "application/pdf"  # freeform but validated
    storage_ref: str = ""  # path, URI, or object key — storage agnostic
    source: str = "uploaded"  # allowed: uploaded, generated, url
    version: str = "1.0.0"
    checksum_sha256: Optional[str] = None  # hex string; optional if external
    size_bytes: Optional[int] = None
    related_entity_id: Optional[str] = None  # link to company/deal/task/etc.
    tags: List[str] = Field(default_factory=list)
    signing_status: str = "none"  # allowed: none, pending, signed, declined, expired
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    retention_policy: str = ""  # e.g., “7y-finance”, “forever”, etc.
    status: str = "active"  # active | archived
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived_at: Optional[datetime] = None

    @validator("mime_type", pre=True)
    def validate_mime_type(cls, v: str) -> str:
        return v.lower().strip() or "application/octet-stream"

    @validator("source", "signing_status", pre=True)
    def validate_source_signing_status(cls, v: str) -> str:
        allowed_values = {"uploaded", "generated", "url", "none", "pending", "signed", "declined", "expired"}
        return v.lower().strip() if v.lower().strip() in allowed_values else "none"

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()

    def archive(self) -> None:
        self.status = "archived"
        self.archived_at = datetime.utcnow()
        self.touch()

    def bump_version(self, major: bool = False, minor: bool = True, patch: bool = False) -> None:
        version_parts = list(map(int, self.version.split(".")));
        if major:
            version_parts[0] += 1
            version_parts[1] = 0
            version_parts[2] = 0
        elif minor:
            version_parts[1] += 1
            version_parts[2] = 0
        elif patch:
            version_parts[2] += 1
        self.version = ".".join(map(str, version_parts))
        self.touch()

    @staticmethod
    def sha256_hex(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def ensure_checksum(self, content: Optional[bytes] = None) -> None:
        if self.checksum_sha256 is None and content is not None:
            self.checksum_sha256 = self.sha256_hex(content)
            self.touch()

    def label(self) -> str:
        return f"doc:{self.name} ({self.mime_type})"

    def to_entity(self) -> Entity:
        return Entity(
            id=self.id,
            tenant_id=self.tenant_id,
            kind=EntityKind("doc"),
            name=self.name,
            status="archived" if self.archived_at else self.status,
            metadata={
                "mime_type": self.mime_type,
                "storage_ref": self.storage_ref,
                "source": self.source,
                "version": self.version,
                "checksum_sha256": self.checksum_sha256,
                "size_bytes": self.size_bytes,
                "related_entity_id": self.related_entity_id,
                "tags": self.tags,
                "signing_status": self.signing_status,
                "effective_date": self.effective_date.isoformat() if self.effective_date else None,
                "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
                "retention_policy": self.retention_policy,
                **self.metadata,
            },
            created_at=self.created_at,
            updated_at=self.updated_at,
            archived_at=self.archived_at
        )

    @classmethod
    def from_entity(cls, e: Entity) -> "Doc":
        return cls(
            id=e.id,
            tenant_id=e.tenant_id,
            name=e.name,
            status=e.status,
            mime_type=e.metadata.get("mime_type", "application/pdf"),
            storage_ref=e.metadata.get("storage_ref", ""),
            source=e.metadata.get("source", "uploaded"),
            version=e.metadata.get("version", "1.0.0"),
            checksum_sha256=e.metadata.get("checksum_sha256"),
            size_bytes=e.metadata.get("size_bytes"),
            related_entity_id=e.metadata.get("related_entity_id"),
            tags=e.metadata.get("tags", []),
            signing_status=e.metadata.get("signing_status", "none"),
            effective_date=date.fromisoformat(e.metadata["effective_date"]) if "effective_date" in e.metadata else None,
            expiration_date=date.fromisoformat(e.metadata["expiration_date"]) if "expiration_date" in e.metadata else None,
            retention_policy=e.metadata.get("retention_policy", ""),
            created_at=e.created_at,
            updated_at=e.updated_at,
            archived_at=e.archived_at
        )