#!/usr/bin/env python3
"""
Pagination and Ordering Utilities for System Builder Hub
Standardized pagination with consistent envelopes and deterministic ordering.
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from flask import request, jsonify
from config import config

class PaginationParams:
    """Pagination parameters from request"""
    
    def __init__(self, page: int = 1, page_size: int = None, order_by: str = None, order_dir: str = 'asc'):
        self.page = max(1, page)
        self.page_size = min(
            max(1, page_size or config.DEFAULT_PAGE_SIZE),
            config.MAX_PAGE_SIZE
        )
        self.order_by = order_by
        self.order_dir = order_dir.lower() if order_dir else 'asc'
        
        if self.order_dir not in ['asc', 'desc']:
            self.order_dir = 'asc'
    
    @classmethod
    def from_request(cls) -> 'PaginationParams':
        """Create pagination params from request"""
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', config.DEFAULT_PAGE_SIZE, type=int)
        order_by = request.args.get('order_by')
        order_dir = request.args.get('order_dir', 'asc')
        
        return cls(page, page_size, order_by, order_dir)
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit for database queries"""
        return self.page_size

class PaginatedResponse:
    """Standardized paginated response envelope"""
    
    def __init__(self, items: List[Any], total: int, pagination: PaginationParams, 
                 base_url: str = None):
        self.items = items
        self.total = total
        self.pagination = pagination
        self.base_url = base_url or request.base_url
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        total_pages = math.ceil(self.total / self.pagination.page_size)
        
        response = {
            'items': self.items,
            'page': self.pagination.page,
            'page_size': self.pagination.page_size,
            'total': self.total,
            'total_pages': total_pages,
            'order_by': self.pagination.order_by,
            'order_dir': self.pagination.order_dir
        }
        
        # Add navigation links
        if self.pagination.page > 1:
            response['prev'] = self._build_url(self.pagination.page - 1)
        
        if self.pagination.page < total_pages:
            response['next'] = self._build_url(self.pagination.page + 1)
        
        response['first'] = self._build_url(1)
        response['last'] = self._build_url(total_pages) if total_pages > 0 else None
        
        return response
    
    def _build_url(self, page: int) -> str:
        """Build URL for specific page"""
        from urllib.parse import urlencode
        
        params = request.args.copy()
        params['page'] = page
        params['page_size'] = self.pagination.page_size
        
        if self.pagination.order_by:
            params['order_by'] = self.pagination.order_by
        if self.pagination.order_dir != 'asc':
            params['order_dir'] = self.pagination.order_dir
        
        return f"{self.base_url}?{urlencode(params)}"
    
    def to_json_response(self):
        """Convert to Flask JSON response"""
        return jsonify(self.to_dict())

def paginate_query(query, pagination: PaginationParams, order_columns: Dict[str, str] = None) -> Tuple[List[Any], int]:
    """Apply pagination and ordering to a database query"""
    # Apply ordering
    if pagination.order_by and order_columns:
        order_column = order_columns.get(pagination.order_by)
        if order_column:
            if pagination.order_dir == 'desc':
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    items = query.offset(pagination.offset).limit(pagination.limit).all()
    
    return items, total

def paginate_list(items: List[Any], pagination: PaginationParams) -> Tuple[List[Any], int]:
    """Apply pagination to a list of items"""
    total = len(items)
    
    # Apply ordering if specified
    if pagination.order_by:
        try:
            reverse = pagination.order_dir == 'desc'
            items = sorted(items, key=lambda x: getattr(x, pagination.order_by, ''), reverse=reverse)
        except (AttributeError, TypeError):
            # Fallback to string sorting
            items = sorted(items, key=lambda x: str(getattr(x, pagination.order_by, '')), reverse=reverse)
    
    # Apply pagination
    start = pagination.offset
    end = start + pagination.page_size
    paginated_items = items[start:end]
    
    return paginated_items, total

def create_paginated_response(items: List[Any], total: int, pagination: PaginationParams, 
                            base_url: str = None) -> PaginatedResponse:
    """Create a paginated response"""
    return PaginatedResponse(items, total, pagination, base_url)

def paginated_endpoint(order_columns: Dict[str, str] = None):
    """Decorator to add pagination to endpoints"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            pagination = PaginationParams.from_request()
            
            # Call the original function with pagination params
            result = f(*args, pagination=pagination, **kwargs)
            
            # If result is already a PaginatedResponse, return it
            if isinstance(result, PaginatedResponse):
                return result.to_json_response()
            
            # If result is a tuple (items, total), create PaginatedResponse
            if isinstance(result, tuple) and len(result) == 2:
                items, total = result
                paginated_response = create_paginated_response(items, total, pagination)
                return paginated_response.to_json_response()
            
            # Otherwise, assume it's a list and paginate it
            if isinstance(result, list):
                paginated_items, total = paginate_list(result, pagination)
                paginated_response = create_paginated_response(paginated_items, total, pagination)
                return paginated_response.to_json_response()
            
            # If it's not a list, return as is
            return result
        
        return decorated_function
    return decorator

# Common order columns for different entities
PROJECT_ORDER_COLUMNS = {
    'id': 'id',
    'name': 'name',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'status': 'status'
}

SYSTEM_ORDER_COLUMNS = {
    'id': 'id',
    'name': 'name',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'version': 'version',
    'status': 'status'
}

USER_ORDER_COLUMNS = {
    'id': 'id',
    'username': 'username',
    'email': 'email',
    'created_at': 'created_at',
    'last_login': 'last_login'
}

# Utility functions for common pagination patterns
def get_pagination_info(pagination: PaginationParams, total: int) -> Dict[str, Any]:
    """Get pagination information"""
    total_pages = math.ceil(total / pagination.page_size)
    
    return {
        'current_page': pagination.page,
        'page_size': pagination.page_size,
        'total_items': total,
        'total_pages': total_pages,
        'has_next': pagination.page < total_pages,
        'has_prev': pagination.page > 1,
        'order_by': pagination.order_by,
        'order_dir': pagination.order_dir
    }

def validate_order_by(order_by: str, allowed_columns: List[str]) -> bool:
    """Validate order_by parameter"""
    if not order_by:
        return True
    
    return order_by in allowed_columns

def sanitize_order_by(order_by: str, allowed_columns: List[str], default: str = None) -> str:
    """Sanitize order_by parameter"""
    if not order_by:
        return default
    
    if order_by in allowed_columns:
        return order_by
    
    return default
