"""
Saved views service for CRM/Ops Template
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.database import db_session
from src.crm_ops.collaboration.models import SavedView

logger = logging.getLogger(__name__)

class SavedViewsService:
    """Service for saved views operations"""
    
    def __init__(self):
        pass
    
    def create_saved_view(self, tenant_id: str, user_id: str, name: str, entity_type: str, filters_json: Dict[str, Any], columns: List[str] = None, sort: Dict[str, Any] = None, is_shared: bool = False, is_default: bool = False) -> SavedView:
        """Create a saved view"""
        with db_session() as session:
            # If this is a default view, unset other default views for this entity type
            if is_default:
                session.query(SavedView).filter(
                    SavedView.tenant_id == tenant_id,
                    SavedView.entity_type == entity_type,
                    SavedView.is_default == True
                ).update({'is_default': False})
            
            saved_view = SavedView(
                tenant_id=tenant_id,
                user_id=user_id,
                name=name,
                entity_type=entity_type,
                filters_json=filters_json,
                columns=columns or [],
                sort=sort or {},
                is_shared=is_shared,
                is_default=is_default
            )
            
            session.add(saved_view)
            session.commit()
            
            return saved_view
    
    def get_saved_views(self, tenant_id: str, user_id: str, entity_type: str = None) -> List[SavedView]:
        """Get saved views for a user"""
        with db_session() as session:
            query = session.query(SavedView).filter(
                SavedView.tenant_id == tenant_id,
                and_(
                    or_(
                        SavedView.user_id == user_id,
                        SavedView.is_shared == True
                    )
                )
            )
            
            if entity_type:
                query = query.filter(SavedView.entity_type == entity_type)
            
            saved_views = query.order_by(SavedView.is_default.desc(), SavedView.name).all()
            
            return saved_views
    
    def get_saved_view(self, view_id: str, tenant_id: str, user_id: str) -> Optional[SavedView]:
        """Get a specific saved view"""
        with db_session() as session:
            saved_view = session.query(SavedView).filter(
                SavedView.id == view_id,
                SavedView.tenant_id == tenant_id,
                and_(
                    or_(
                        SavedView.user_id == user_id,
                        SavedView.is_shared == True
                    )
                )
            ).first()
            
            return saved_view
    
    def update_saved_view(self, view_id: str, tenant_id: str, user_id: str, updates: Dict[str, Any]) -> Optional[SavedView]:
        """Update a saved view"""
        with db_session() as session:
            saved_view = session.query(SavedView).filter(
                SavedView.id == view_id,
                SavedView.tenant_id == tenant_id,
                SavedView.user_id == user_id
            ).first()
            
            if not saved_view:
                return None
            
            # Update fields
            if 'name' in updates:
                saved_view.name = updates['name']
            if 'description' in updates:
                saved_view.description = updates['description']
            if 'filters_json' in updates:
                saved_view.filters_json = updates['filters_json']
            if 'columns' in updates:
                saved_view.columns = updates['columns']
            if 'sort' in updates:
                saved_view.sort = updates['sort']
            if 'is_shared' in updates:
                saved_view.is_shared = updates['is_shared']
            if 'is_default' in updates:
                saved_view.is_default = updates['is_default']
                
                # If setting as default, unset other defaults for this entity type
                if updates['is_default']:
                    session.query(SavedView).filter(
                        SavedView.tenant_id == tenant_id,
                        SavedView.entity_type == saved_view.entity_type,
                        SavedView.id != view_id,
                        SavedView.is_default == True
                    ).update({'is_default': False})
            
            saved_view.updated_at = datetime.utcnow()
            session.commit()
            
            return saved_view
    
    def delete_saved_view(self, view_id: str, tenant_id: str, user_id: str) -> bool:
        """Delete a saved view"""
        with db_session() as session:
            saved_view = session.query(SavedView).filter(
                SavedView.id == view_id,
                SavedView.tenant_id == tenant_id,
                SavedView.user_id == user_id
            ).first()
            
            if not saved_view:
                return False
            
            session.delete(saved_view)
            session.commit()
            
            return True
    
    def get_default_view(self, tenant_id: str, entity_type: str) -> Optional[SavedView]:
        """Get the default view for an entity type"""
        with db_session() as session:
            default_view = session.query(SavedView).filter(
                SavedView.tenant_id == tenant_id,
                SavedView.entity_type == entity_type,
                SavedView.is_default == True
            ).first()
            
            return default_view
    
    def duplicate_saved_view(self, view_id: str, tenant_id: str, user_id: str, new_name: str) -> Optional[SavedView]:
        """Duplicate a saved view"""
        with db_session() as session:
            original_view = session.query(SavedView).filter(
                SavedView.id == view_id,
                SavedView.tenant_id == tenant_id,
                and_(
                    or_(
                        SavedView.user_id == user_id,
                        SavedView.is_shared == True
                    )
                )
            ).first()
            
            if not original_view:
                return None
            
            # Create duplicate
            duplicated_view = SavedView(
                tenant_id=tenant_id,
                user_id=user_id,
                name=new_name,
                description=original_view.description,
                entity_type=original_view.entity_type,
                filters_json=original_view.filters_json,
                columns=original_view.columns,
                sort=original_view.sort,
                is_shared=False,  # Duplicates are always private
                is_default=False  # Duplicates are never default
            )
            
            session.add(duplicated_view)
            session.commit()
            
            return duplicated_view
    
    def share_saved_view(self, view_id: str, tenant_id: str, user_id: str) -> bool:
        """Share a saved view with the team"""
        with db_session() as session:
            saved_view = session.query(SavedView).filter(
                SavedView.id == view_id,
                SavedView.tenant_id == tenant_id,
                SavedView.user_id == user_id
            ).first()
            
            if not saved_view:
                return False
            
            saved_view.is_shared = True
            saved_view.updated_at = datetime.utcnow()
            session.commit()
            
            return True
    
    def unshare_saved_view(self, view_id: str, tenant_id: str, user_id: str) -> bool:
        """Unshare a saved view"""
        with db_session() as session:
            saved_view = session.query(SavedView).filter(
                SavedView.id == view_id,
                SavedView.tenant_id == tenant_id,
                SavedView.user_id == user_id
            ).first()
            
            if not saved_view:
                return False
            
            saved_view.is_shared = False
            saved_view.updated_at = datetime.utcnow()
            session.commit()
            
            return True
