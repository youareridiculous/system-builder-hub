#!/usr/bin/env python3
"""
API Versioning Policy for System Builder Hub
Deprecation warnings, compatibility middleware, and version management.
"""

import logging
from typing import Dict, Any, Optional, List
from functools import wraps
from datetime import datetime, timedelta

from flask import request, jsonify, current_app, g
from config import config

logger = logging.getLogger(__name__)

class APIVersion:
    """API version information"""
    
    def __init__(self, version: str, release_date: datetime, sunset_date: Optional[datetime] = None):
        self.version = version
        self.release_date = release_date
        self.sunset_date = sunset_date
    
    @property
    def is_deprecated(self) -> bool:
        """Check if version is deprecated"""
        if not self.sunset_date:
            return False
        return datetime.now() > self.sunset_date
    
    @property
    def is_sunset(self) -> bool:
        """Check if version is sunset (past sunset date)"""
        if not self.sunset_date:
            return False
        return datetime.now() > self.sunset_date
    
    @property
    def days_until_sunset(self) -> Optional[int]:
        """Days until sunset date"""
        if not self.sunset_date:
            return None
        delta = self.sunset_date - datetime.now()
        return max(0, delta.days)

class APIVersionManager:
    """Manages API versions and deprecation policies"""
    
    def __init__(self):
        self.versions: Dict[str, APIVersion] = {}
        self.deprecated_endpoints: Dict[str, Dict[str, Any]] = {}
        self._initialize_versions()
    
    def _initialize_versions(self):
        """Initialize API versions"""
        # Current stable version
        self.versions['v1'] = APIVersion(
            version='v1',
            release_date=datetime(2024, 1, 1),
            sunset_date=None  # No sunset date for current version
        )
        
        # Future versions (for planning)
        self.versions['v2'] = APIVersion(
            version='v2',
            release_date=datetime(2024, 6, 1),
            sunset_date=None
        )
    
    def get_version(self, version: str) -> Optional[APIVersion]:
        """Get API version information"""
        return self.versions.get(version)
    
    def get_current_version(self) -> str:
        """Get current stable API version"""
        return 'v1'
    
    def get_latest_version(self) -> str:
        """Get latest API version"""
        return max(self.versions.keys())
    
    def is_version_supported(self, version: str) -> bool:
        """Check if API version is supported"""
        if version not in self.versions:
            return False
        
        api_version = self.versions[version]
        return not api_version.is_sunset
    
    def mark_endpoint_deprecated(self, endpoint: str, version: str, 
                                sunset_date: datetime, replacement: str = None):
        """Mark an endpoint as deprecated"""
        self.deprecated_endpoints[endpoint] = {
            'version': version,
            'sunset_date': sunset_date,
            'replacement': replacement,
            'marked_deprecated': datetime.now()
        }
        logger.info(f"Marked endpoint {endpoint} as deprecated in {version}")
    
    def is_endpoint_deprecated(self, endpoint: str) -> bool:
        """Check if endpoint is deprecated"""
        return endpoint in self.deprecated_endpoints
    
    def get_deprecation_info(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Get deprecation information for endpoint"""
        return self.deprecated_endpoints.get(endpoint)
    
    def get_all_deprecated_endpoints(self) -> List[Dict[str, Any]]:
        """Get all deprecated endpoints"""
        deprecated = []
        for endpoint, info in self.deprecated_endpoints.items():
            deprecated.append({
                'endpoint': endpoint,
                **info
            })
        return deprecated

# Global API version manager
api_version_manager = APIVersionManager()

def deprecated_endpoint(version: str, sunset_date: datetime, replacement: str = None):
    """Decorator to mark an endpoint as deprecated"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            endpoint = f"{request.method} {request.path}"
            
            # Mark as deprecated if not already
            if not api_version_manager.is_endpoint_deprecated(endpoint):
                api_version_manager.mark_endpoint_deprecated(endpoint, version, sunset_date, replacement)
            
            # Check if endpoint is sunset
            deprecation_info = api_version_manager.get_deprecation_info(endpoint)
            if deprecation_info and deprecation_info['sunset_date'] < datetime.now():
                return jsonify({
                    'error': 'This endpoint has been sunset',
                    'code': 'ENDPOINT_SUNSET',
                    'endpoint': endpoint,
                    'sunset_date': deprecation_info['sunset_date'].isoformat(),
                    'replacement': deprecation_info.get('replacement')
                }), 410  # Gone
            
            # Add deprecation headers if enabled
            response = f(*args, **kwargs)
            
            if config.ENABLE_DEPRECATION_WARNINGS and deprecation_info:
                if hasattr(response, 'headers'):
                    response.headers['Deprecation'] = 'true'
                    response.headers['Sunset'] = deprecation_info['sunset_date'].isoformat()
                    
                    if deprecation_info.get('replacement'):
                        response.headers['Link'] = f'<{deprecation_info["replacement"]}>; rel="successor-version"'
                    
                    # Add warning header
                    warning_msg = f'299 - "This endpoint is deprecated and will be sunset on {deprecation_info["sunset_date"].strftime("%Y-%m-%d")}"'
                    response.headers['Warning'] = warning_msg
            
            return response
        
        return decorated_function
    return decorator

def require_api_version(min_version: str = None, max_version: str = None):
    """Decorator to require specific API version"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract version from URL path
            path_parts = request.path.split('/')
            if len(path_parts) >= 3 and path_parts[1] == 'api':
                version = path_parts[2]
            else:
                version = 'v1'  # Default version
            
            # Check version constraints
            if min_version and version < min_version:
                return jsonify({
                    'error': f'API version {version} is not supported. Minimum version required: {min_version}',
                    'code': 'VERSION_TOO_OLD',
                    'current_version': version,
                    'minimum_version': min_version
                }), 400
            
            if max_version and version > max_version:
                return jsonify({
                    'error': f'API version {version} is not supported. Maximum version allowed: {max_version}',
                    'code': 'VERSION_TOO_NEW',
                    'current_version': version,
                    'maximum_version': max_version
                }), 400
            
            # Check if version is supported
            if not api_version_manager.is_version_supported(version):
                return jsonify({
                    'error': f'API version {version} is not supported',
                    'code': 'VERSION_NOT_SUPPORTED',
                    'current_version': version,
                    'supported_versions': list(api_version_manager.versions.keys())
                }), 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def version_specific(version_handlers: Dict[str, callable]):
    """Decorator to provide version-specific implementations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract version from URL path
            path_parts = request.path.split('/')
            if len(path_parts) >= 3 and path_parts[1] == 'api':
                version = path_parts[2]
            else:
                version = 'v1'  # Default version
            
            # Use version-specific handler if available
            if version in version_handlers:
                return version_handlers[version](*args, **kwargs)
            
            # Fall back to default implementation
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def add_version_headers(response):
    """Add version headers to response"""
    if not config.ENABLE_DEPRECATION_WARNINGS:
        return response
    
    # Add API version header
    if hasattr(response, 'headers'):
        response.headers['X-API-Version'] = api_version_manager.get_current_version()
        response.headers['X-API-Latest-Version'] = api_version_manager.get_latest_version()
    
    return response

# Predefined deprecation decorators for common patterns
def deprecated_v1_endpoint(sunset_date: datetime, replacement: str = None):
    """Mark a v1 endpoint as deprecated"""
    return deprecated_endpoint('v1', sunset_date, replacement)

def deprecated_v2_endpoint(sunset_date: datetime, replacement: str = None):
    """Mark a v2 endpoint as deprecated"""
    return deprecated_endpoint('v2', sunset_date, replacement)

# Utility functions
def get_api_version_info() -> Dict[str, Any]:
    """Get API version information"""
    return {
        'current_version': api_version_manager.get_current_version(),
        'latest_version': api_version_manager.get_latest_version(),
        'supported_versions': [
            {
                'version': version,
                'release_date': api_version.release_date.isoformat(),
                'sunset_date': api_version.sunset_date.isoformat() if api_version.sunset_date else None,
                'is_deprecated': api_version.is_deprecated,
                'is_sunset': api_version.is_sunset,
                'days_until_sunset': api_version.days_until_sunset
            }
            for version, api_version in api_version_manager.versions.items()
        ],
        'deprecated_endpoints': api_version_manager.get_all_deprecated_endpoints()
    }

def check_version_compatibility(client_version: str, server_version: str = None) -> Dict[str, Any]:
    """Check version compatibility"""
    if not server_version:
        server_version = api_version_manager.get_current_version()
    
    # Simple version comparison (assumes semantic versioning)
    def version_to_tuple(version: str) -> tuple:
        return tuple(int(x) for x in version.lstrip('v').split('.'))
    
    client_tuple = version_to_tuple(client_version)
    server_tuple = version_to_tuple(server_version)
    
    return {
        'client_version': client_version,
        'server_version': server_version,
        'compatible': client_tuple[0] == server_tuple[0],  # Major version must match
        'upgrade_recommended': client_tuple < server_tuple,
        'downgrade_recommended': client_tuple > server_tuple
    }

# Initialize deprecation warnings for existing endpoints
def initialize_deprecation_warnings():
    """Initialize deprecation warnings for existing endpoints"""
    # Example: Mark some endpoints as deprecated
    # api_version_manager.mark_endpoint_deprecated(
    #     'GET /api/v1/old-endpoint',
    #     'v1',
    #     datetime(2024, 12, 31),
    #     '/api/v1/new-endpoint'
    # )
    pass
