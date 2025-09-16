"""
Marketplace models
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from src.db_core import Base

class Template(Base):
    """Template model"""
    __tablename__ = 'templates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    short_desc = Column(Text, nullable=True)
    long_desc = Column(Text, nullable=True)
    category = Column(String(100), nullable=False, index=True)
    tags = Column(JSONB, nullable=True)
    price_cents = Column(Integer, nullable=True)
    requires_plan = Column(String(50), nullable=True)
    author_user_id = Column(String(255), nullable=False, index=True)
    is_public = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    variants = relationship("TemplateVariant", back_populates="template")
    assets = relationship("TemplateAssets", back_populates="template", uselist=False)
    guided_schema = relationship("TemplateGuidedSchema", back_populates="template", uselist=False)
    builder_states = relationship("TemplateBuilderState", back_populates="template")
    
    __table_args__ = (
        Index('idx_templates_category_public', 'category', 'is_public'),
    )
    
    def __repr__(self):
        return f"<Template(id={self.id}, slug='{self.slug}', name='{self.name}')>"

class TemplateVariant(Base):
    """Template variant model"""
    __tablename__ = 'template_variants'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey('templates.id'), nullable=False)
    version = Column(String(50), nullable=False)
    default = Column(Boolean, nullable=False, default=False)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    template = relationship("Template", back_populates="variants")
    builder_states = relationship("TemplateBuilderState", back_populates="variant")
    
    def __repr__(self):
        return f"<TemplateVariant(id={self.id}, template_id={self.template_id}, version='{self.version}')>"

class TemplateAssets(Base):
    """Template assets model"""
    __tablename__ = 'template_assets'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey('templates.id'), nullable=False)
    cover_image_url = Column(Text, nullable=True)
    gallery = Column(JSONB, nullable=True)
    sample_screens = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    template = relationship("Template", back_populates="assets")
    
    def __repr__(self):
        return f"<TemplateAssets(id={self.id}, template_id={self.template_id})>"

class TemplateGuidedSchema(Base):
    """Template guided schema model"""
    __tablename__ = 'template_guided_schemas'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey('templates.id'), nullable=False)
    schema = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    template = relationship("Template", back_populates="guided_schema")
    
    def __repr__(self):
        return f"<TemplateGuidedSchema(id={self.id}, template_id={self.template_id})>"

class TemplateBuilderState(Base):
    """Template builder state model"""
    __tablename__ = 'template_builder_states'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey('templates.id'), nullable=False)
    variant_id = Column(UUID(as_uuid=True), ForeignKey('template_variants.id'), nullable=True)
    builder_state = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    template = relationship("Template", back_populates="builder_states")
    variant = relationship("TemplateVariant", back_populates="builder_states")
    
    def __repr__(self):
        return f"<TemplateBuilderState(id={self.id}, template_id={self.template_id})>"
