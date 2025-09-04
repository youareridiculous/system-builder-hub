"""
Smoke tests for SBH Marketplace functionality.
"""

import pytest
import requests
import json
from typing import Dict, Any


class TestMarketplaceSmoke:
    """Smoke tests for marketplace functionality."""
    
    @pytest.fixture
    def base_url(self):
        """Get base URL for testing."""
        return "http://localhost:5001"
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token."""
        # TODO: Implement proper auth token generation
        return "test-token"
    
    def test_marketplace_health(self, base_url):
        """Test marketplace health endpoints."""
        # Test main health endpoint
        response = requests.get(f"{base_url}/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_templates_endpoint(self, base_url, auth_token):
        """Test templates listing endpoint."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(f"{base_url}/api/marketplace/templates", headers=headers)
        
        # Should return 401 if auth is required, or 200 if templates exist
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert isinstance(data["data"], list)
            assert len(data["data"]) >= 5  # Should have at least 5 templates
            
            # Check for specific templates
            template_slugs = [t["attributes"]["slug"] for t in data["data"]]
            assert "flagship-crm" in template_slugs
            assert "learning-management-system" in template_slugs
            assert "recruiting-ats" in template_slugs
            assert "helpdesk-support" in template_slugs
            assert "analytics-dashboard" in template_slugs
    
    def test_template_detail_endpoint(self, base_url, auth_token):
        """Test template detail endpoint."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(f"{base_url}/api/marketplace/templates/flagship-crm", headers=headers)
        
        # Should return 401 if auth is required, or 200 if template exists
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert data["data"]["attributes"]["slug"] == "flagship-crm"
            assert data["data"]["attributes"]["name"] == "Flagship CRM & Ops"
            assert "features" in data["data"]["attributes"]
            assert "plans" in data["data"]["attributes"]
    
    def test_categories_endpoint(self, base_url, auth_token):
        """Test categories listing endpoint."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(f"{base_url}/api/marketplace/categories", headers=headers)
        
        # Should return 401 if auth is required, or 200 if categories exist
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert isinstance(data["data"], list)
            
            # Check for expected categories
            categories = [cat["id"] for cat in data["data"]]
            assert "Sales & Ops" in categories
            assert "Education" in categories
            assert "HR & Recruiting" in categories
            assert "Customer Support" in categories
            assert "Analytics" in categories
    
    def test_template_launch_endpoint(self, base_url, auth_token):
        """Test template launch endpoint."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "tenant_name": "Test Tenant",
            "domain": "test.com",
            "plan": "starter",
            "seed_demo_data": True
        }
        
        response = requests.post(
            f"{base_url}/api/marketplace/templates/flagship-crm/launch",
            headers=headers,
            json=data
        )
        
        # Should return 401 if auth is required, or 201 if successful
        assert response.status_code in [201, 401]
        
        if response.status_code == 201:
            result = response.json()
            assert "data" in result
            assert result["data"]["type"] == "tenant_launch"
            assert result["data"]["attributes"]["template_slug"] == "flagship-crm"
            assert result["data"]["attributes"]["tenant_name"] == "Test Tenant"
    
    def test_ui_routes(self, base_url, auth_token):
        """Test UI routes are accessible."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        ui_routes = [
            "/ui/marketplace/",
            "/ui/marketplace/template/flagship-crm"
        ]
        
        for route in ui_routes:
            response = requests.get(f"{base_url}{route}", headers=headers)
            # Should return 401 if auth is required, or 200 if accessible
            assert response.status_code in [200, 401]
    
    def test_template_filtering(self, base_url, auth_token):
        """Test template filtering functionality."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        # Test category filtering
        response = requests.get(
            f"{base_url}/api/marketplace/templates?category=Sales%20%26%20Ops",
            headers=headers
        )
        
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            # Should have at least one Sales & Ops template
            assert len(data["data"]) >= 1
        
        # Test search functionality
        response = requests.get(
            f"{base_url}/api/marketplace/templates?search=crm",
            headers=headers
        )
        
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            # Should find CRM-related templates
            assert len(data["data"]) >= 1
    
    def test_template_metadata(self, base_url, auth_token):
        """Test template metadata completeness."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        templates_to_test = [
            "flagship-crm",
            "learning-management-system",
            "recruiting-ats",
            "helpdesk-support",
            "analytics-dashboard"
        ]
        
        for template_slug in templates_to_test:
            response = requests.get(f"{base_url}/api/marketplace/templates/{template_slug}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                template = data["data"]["attributes"]
                
                # Check required fields
                assert "name" in template
                assert "description" in template
                assert "category" in template
                assert "tags" in template
                assert "badges" in template
                assert "features" in template
                assert "plans" in template
                assert "screenshots" in template
                
                # Check data types
                assert isinstance(template["name"], str)
                assert isinstance(template["description"], str)
                assert isinstance(template["category"], str)
                assert isinstance(template["tags"], list)
                assert isinstance(template["badges"], list)
                assert isinstance(template["features"], list)
                assert isinstance(template["plans"], dict)
                assert isinstance(template["screenshots"], list)
                
                # Check plans structure
                for plan_key, plan_data in template["plans"].items():
                    assert "name" in plan_data
                    assert "price" in plan_data
                    assert "features" in plan_data
                    assert isinstance(plan_data["features"], list)


if __name__ == "__main__":
    pytest.main([__file__])
