"""
Search API for CRM/Ops Template
"""
import logging
from typing import Dict, Any
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Role
from src.tenancy.context import get_current_tenant_id
from src.crm_ops.collaboration.search_service import SearchService
from src.crm_ops.collaboration.saved_views_service import SavedViewsService
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, handle_api_errors
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

bp = Blueprint('search', __name__, url_prefix='/api')

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

class SearchAPI(CRMOpsAPIBase):
    """Search API implementation"""
    
    def __init__(self):
        super().__init__(None, 'search')
        self.search_service = SearchService()
        self.saved_views_service = SavedViewsService()
    
    @handle_api_errors
    @limiter.limit("20 per minute")
    def global_search(self) -> tuple:
        """Perform global search"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        query = data.get('query', '')
        entity_types = data.get('entity_types', ['contact', 'deal', 'task', 'project'])
        limit = data.get('limit', 50)
        
        if not query:
            raise ValidationError("query is required", "query")
        
        try:
            results = self.search_service.global_search(tenant_id, query, entity_types, limit)
            
            # Log audit event
            self.log_audit_event('read', 'global_search', new_values={
                'query': query,
                'entity_types': entity_types,
                'results_count': sum(len(results.get(key, [])) for key in results)
            })
            
            return jsonify({
                'data': {
                    'type': 'search_results',
                    'attributes': {
                        'query': query,
                        'results': results
                    }
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error performing global search: {e}")
            raise CRMOpsAPIError("Failed to perform search", 500, "SEARCH_ERROR")
    
    @handle_api_errors
    @limiter.limit("20 per minute")
    def advanced_search(self) -> tuple:
        """Perform advanced search with filters"""
        tenant_id = get_current_tenant_id()
        data = request.get_json()
        
        entity_type = data.get('entity_type')
        filters = data.get('filters', {})
        limit = data.get('limit', 50)
        
        if not entity_type:
            raise ValidationError("entity_type is required", "entity_type")
        
        try:
            results = self.search_service.advanced_search(tenant_id, filters, entity_type, limit)
            
            # Log audit event
            self.log_audit_event('read', 'advanced_search', new_values={
                'entity_type': entity_type,
                'filters': filters,
                'results_count': len(results)
            })
            
            return jsonify({
                'data': [
                    {
                        'id': result.get('id'),
                        'type': entity_type,
                        'attributes': result
                    }
                    for result in results
                ]
            }), 200
            
        except Exception as e:
            logger.error(f"Error performing advanced search: {e}")
            raise CRMOpsAPIError("Failed to perform advanced search", 500, "ADVANCED_SEARCH_ERROR")
    
    @handle_api_errors
    def get_faceted_search(self, entity_type: str) -> tuple:
        """Get faceted search data"""
        tenant_id = get_current_tenant_id()
        
        try:
            facets = self.search_service.get_faceted_search(tenant_id, entity_type)
            
            return jsonify({
                'data': {
                    'type': 'search_facets',
                    'attributes': {
                        'entity_type': entity_type,
                        'facets': facets
                    }
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error getting faceted search: {e}")
            raise CRMOpsAPIError("Failed to get faceted search", 500, "FACETED_SEARCH_ERROR")
    
    @handle_api_errors
    @limiter.limit("20 per minute")
    def create_saved_view(self) -> tuple:
        """Create a saved view"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            raise ValidationError("name is required", "name")
        if not data.get('entity_type'):
            raise ValidationError("entity_type is required", "entity_type")
        if not data.get('filters_json'):
            raise ValidationError("filters_json is required", "filters_json")
        
        try:
            saved_view = self.saved_views_service.create_saved_view(
                tenant_id=tenant_id,
                user_id=user_id,
                name=data['name'],
                entity_type=data['entity_type'],
                filters_json=data['filters_json'],
                columns=data.get('columns', []),
                sort=data.get('sort', {}),
                is_shared=data.get('is_shared', False),
                is_default=data.get('is_default', False)
            )
            
            # Log audit event
            self.log_audit_event('create', str(saved_view.id), new_values={
                'name': saved_view.name,
                'entity_type': saved_view.entity_type,
                'is_shared': saved_view.is_shared
            })
            
            return jsonify({
                'data': {
                    'id': str(saved_view.id),
                    'type': 'saved_view',
                    'attributes': saved_view.to_dict()
                }
            }), 201
            
        except Exception as e:
            logger.error(f"Error creating saved view: {e}")
            raise CRMOpsAPIError("Failed to create saved view", 500, "SAVED_VIEW_CREATE_ERROR")
    
    @handle_api_errors
    def get_saved_views(self) -> tuple:
        """Get saved views"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        entity_type = request.args.get('entity_type')
        
        try:
            saved_views = self.saved_views_service.get_saved_views(tenant_id, user_id, entity_type)
            
            return jsonify({
                'data': [
                    {
                        'id': str(view.id),
                        'type': 'saved_view',
                        'attributes': view.to_dict()
                    }
                    for view in saved_views
                ]
            }), 200
            
        except Exception as e:
            logger.error(f"Error getting saved views: {e}")
            raise CRMOpsAPIError("Failed to get saved views", 500, "SAVED_VIEW_GET_ERROR")
    
    @handle_api_errors
    def get_saved_view(self, view_id: str) -> tuple:
        """Get a specific saved view"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        try:
            saved_view = self.saved_views_service.get_saved_view(view_id, tenant_id, user_id)
            
            if not saved_view:
                raise CRMOpsAPIError("Saved view not found", 404, "SAVED_VIEW_NOT_FOUND")
            
            return jsonify({
                'data': {
                    'id': str(saved_view.id),
                    'type': 'saved_view',
                    'attributes': saved_view.to_dict()
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error getting saved view: {e}")
            raise CRMOpsAPIError("Failed to get saved view", 500, "SAVED_VIEW_GET_ERROR")
    
    @handle_api_errors
    @limiter.limit("20 per minute")
    def update_saved_view(self, view_id: str) -> tuple:
        """Update a saved view"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        data = request.get_json()
        
        try:
            saved_view = self.saved_views_service.update_saved_view(view_id, tenant_id, user_id, data)
            
            if not saved_view:
                raise CRMOpsAPIError("Saved view not found or access denied", 404, "SAVED_VIEW_NOT_FOUND")
            
            # Log audit event
            self.log_audit_event('update', str(saved_view.id), new_values=data)
            
            return jsonify({
                'data': {
                    'id': str(saved_view.id),
                    'type': 'saved_view',
                    'attributes': saved_view.to_dict()
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error updating saved view: {e}")
            raise CRMOpsAPIError("Failed to update saved view", 500, "SAVED_VIEW_UPDATE_ERROR")
    
    @handle_api_errors
    def delete_saved_view(self, view_id: str) -> tuple:
        """Delete a saved view"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        try:
            success = self.saved_views_service.delete_saved_view(view_id, tenant_id, user_id)
            
            if not success:
                raise CRMOpsAPIError("Saved view not found or access denied", 404, "SAVED_VIEW_NOT_FOUND")
            
            # Log audit event
            self.log_audit_event('delete', view_id)
            
            return jsonify({
                'data': {
                    'type': 'saved_view',
                    'attributes': {
                        'deleted': True,
                        'view_id': view_id
                    }
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error deleting saved view: {e}")
            raise CRMOpsAPIError("Failed to delete saved view", 500, "SAVED_VIEW_DELETE_ERROR")

# Initialize API
search_api = SearchAPI()

# Route handlers
@bp.route('/search', methods=['POST'])
@require_tenant_context
def global_search():
    """Global search"""
    return search_api.global_search()

@bp.route('/search/advanced', methods=['POST'])
@require_tenant_context
def advanced_search():
    """Advanced search"""
    return search_api.advanced_search()

@bp.route('/search/facets/<entity_type>', methods=['GET'])
@require_tenant_context
def get_faceted_search(entity_type):
    """Get faceted search"""
    return search_api.get_faceted_search(entity_type)

@bp.route('/saved-views', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def create_saved_view():
    """Create saved view"""
    return search_api.create_saved_view()

@bp.route('/saved-views', methods=['GET'])
@require_tenant_context
def get_saved_views():
    """Get saved views"""
    return search_api.get_saved_views()

@bp.route('/saved-views/<view_id>', methods=['GET'])
@require_tenant_context
def get_saved_view(view_id):
    """Get saved view"""
    return search_api.get_saved_view(view_id)

@bp.route('/saved-views/<view_id>', methods=['PUT'])
@require_tenant_context
@require_role(Role.MEMBER)
def update_saved_view(view_id):
    """Update saved view"""
    return search_api.update_saved_view(view_id)

@bp.route('/saved-views/<view_id>', methods=['DELETE'])
@require_tenant_context
@require_role(Role.MEMBER)
def delete_saved_view(view_id):
    """Delete saved view"""
    return search_api.delete_saved_view(view_id)
