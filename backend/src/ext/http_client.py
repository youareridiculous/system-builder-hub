"""
Plugin HTTP client with allowlist
"""
import logging
import requests
from typing import Dict, Any, Optional
from src.security.residency import residency_manager

logger = logging.getLogger(__name__)

class HTTPClient:
    """Plugin HTTP client with domain allowlist"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.session = requests.Session()
        
        # Default allowlist
        self.default_allowlist = {
            'jsonplaceholder.typicode.com',
            'api.stripe.com',
            'api.github.com',
            'api.openai.com',
            'api.anthropic.com'
        }
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, 
            headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make GET request"""
        return self._make_request('GET', url, params=params, headers=headers)
    
    def post(self, url: str, data: Optional[Dict[str, Any]] = None,
             json: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make POST request"""
        return self._make_request('POST', url, data=data, json=json, headers=headers)
    
    def put(self, url: str, data: Optional[Dict[str, Any]] = None,
            json: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make PUT request"""
        return self._make_request('PUT', url, data=data, json=json, headers=headers)
    
    def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make DELETE request"""
        return self._make_request('DELETE', url, headers=headers)
    
    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with allowlist check"""
        try:
            # Parse URL to get domain
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Check allowlist
            if not self._is_domain_allowed(domain):
                raise ValueError(f"Domain {domain} not in allowlist")
            
            # Make request
            response = self.session.request(method, url, **kwargs)
            
            # Track request
            self._track_request(method, url, response.status_code)
            
            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'text': response.text,
                'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            }
            
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return {
                'status_code': 0,
                'error': str(e),
                'text': '',
                'json': None
            }
    
    def _is_domain_allowed(self, domain: str) -> bool:
        """Check if domain is in allowlist"""
        # Check default allowlist
        if domain in self.default_allowlist:
            return True
        
        # Check tenant-specific allowlist (if implemented)
        # In a real implementation, this would check tenant configuration
        
        return False
    
    def _track_request(self, method: str, url: str, status_code: int):
        """Track HTTP request for audit"""
        try:
            from src.analytics.service import AnalyticsService
            analytics = AnalyticsService()
            
            analytics.track(
                tenant_id=self.tenant_id,
                event='plugin.http_request',
                user_id='system',
                source='plugin',
                props={
                    'method': method,
                    'url': url,
                    'status_code': status_code
                }
            )
            
        except Exception as e:
            logger.error(f"Error tracking HTTP request: {e}")
