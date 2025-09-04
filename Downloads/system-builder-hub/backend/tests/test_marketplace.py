"""
Tests for SBH Marketplace functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch
from src.marketplace.api import load_marketplace_templates


class TestMarketplaceAPI:
    """Test marketplace API functionality."""
    
    def test_load_marketplace_templates(self):
        """Test loading marketplace templates."""
        templates = load_marketplace_templates()
        
        assert len(templates) >= 5  # Should have at least 5 templates
        
        # Check for specific templates
        template_slugs = [t['slug'] for t in templates]
        assert 'flagship-crm' in template_slugs
        assert 'learning-management-system' in template_slugs
        assert 'recruiting-ats' in template_slugs
        assert 'helpdesk-support' in template_slugs
        assert 'analytics-dashboard' in template_slugs
    
    def test_template_structure(self):
        """Test template structure and required fields."""
        templates = load_marketplace_templates()
        
        for template in templates:
            # Required fields
            assert 'slug' in template
            assert 'name' in template
            assert 'description' in template
            assert 'category' in template
            assert 'tags' in template
            assert 'badges' in template
            assert 'version' in template
            assert 'author' in template
            assert 'features' in template
            assert 'plans' in template
            assert 'is_active' in template
            
            # Validate data types
            assert isinstance(template['slug'], str)
            assert isinstance(template['name'], str)
            assert isinstance(template['description'], str)
            assert isinstance(template['category'], str)
            assert isinstance(template['tags'], list)
            assert isinstance(template['badges'], list)
            assert isinstance(template['features'], list)
            assert isinstance(template['plans'], dict)
            assert isinstance(template['is_active'], bool)
    
    def test_crm_template_details(self):
        """Test flagship CRM template details."""
        templates = load_marketplace_templates()
        crm_template = next((t for t in templates if t['slug'] == 'flagship-crm'), None)
        
        assert crm_template is not None
        assert crm_template['name'] == 'Flagship CRM & Ops'
        assert crm_template['category'] == 'Sales & Ops'
        assert 'crm' in crm_template['tags']
        assert 'Multi-tenant' in crm_template['badges']
        assert 'Contact Management' in crm_template['features']
        
        # Check plans
        assert 'starter' in crm_template['plans']
        assert 'pro' in crm_template['plans']
        assert 'enterprise' in crm_template['plans']
        
        starter_plan = crm_template['plans']['starter']
        assert starter_plan['price'] == 0
        assert 'Up to 100 contacts' in starter_plan['features']
    
    def test_lms_template_details(self):
        """Test LMS template details."""
        templates = load_marketplace_templates()
        lms_template = next((t for t in templates if t['slug'] == 'learning-management-system'), None)
        
        assert lms_template is not None
        assert lms_template['name'] == 'Learning Management System'
        assert lms_template['category'] == 'Education'
        assert 'lms' in lms_template['tags']
        assert 'Course Management' in lms_template['features']
        
        # Check plans
        assert 'starter' in lms_template['plans']
        assert 'pro' in lms_template['plans']
        assert 'enterprise' in lms_template['plans']
    
    def test_recruiting_template_details(self):
        """Test recruiting template details."""
        templates = load_marketplace_templates()
        recruiting_template = next((t for t in templates if t['slug'] == 'recruiting-ats'), None)
        
        assert recruiting_template is not None
        assert recruiting_template['name'] == 'Recruiting & ATS'
        assert recruiting_template['category'] == 'HR & Recruiting'
        assert 'recruiting' in recruiting_template['tags']
        assert 'Candidate Management' in recruiting_template['features']
    
    def test_helpdesk_template_details(self):
        """Test helpdesk template details."""
        templates = load_marketplace_templates()
        helpdesk_template = next((t for t in templates if t['slug'] == 'helpdesk-support'), None)
        
        assert helpdesk_template is not None
        assert helpdesk_template['name'] == 'Helpdesk & Support'
        assert helpdesk_template['category'] == 'Customer Support'
        assert 'helpdesk' in helpdesk_template['tags']
        assert 'Ticket Management' in helpdesk_template['features']
    
    def test_analytics_template_details(self):
        """Test analytics template details."""
        templates = load_marketplace_templates()
        analytics_template = next((t for t in templates if t['slug'] == 'analytics-dashboard'), None)
        
        assert analytics_template is not None
        assert analytics_template['name'] == 'Analytics Dashboard'
        assert analytics_template['category'] == 'Analytics'
        assert 'analytics' in analytics_template['tags']
        assert 'Custom Dashboards' in analytics_template['features']


class TestMarketplaceEndpoints:
    """Test marketplace API endpoints."""
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def auth_headers(self):
        """Create authenticated headers."""
        return {
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json'
        }
    
    def test_list_templates_endpoint(self, client, auth_headers):
        """Test templates listing endpoint."""
        response = client.get('/api/marketplace/templates', headers=auth_headers)
        
        # Should return 401 if auth is required, or 200 if successful
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.get_json()
            assert 'data' in data
            assert isinstance(data['data'], list)
            assert len(data['data']) >= 5
            
            # Check meta information
            assert 'meta' in data
            assert 'categories' in data['meta']
            assert 'tags' in data['meta']
            assert 'total' in data['meta']
    
    def test_get_template_endpoint(self, client, auth_headers):
        """Test getting specific template."""
        response = client.get('/api/marketplace/templates/flagship-crm', headers=auth_headers)
        
        # Should return 401 if auth is required, or 200 if successful
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.get_json()
            assert 'data' in data
            assert data['data']['attributes']['slug'] == 'flagship-crm'
            assert data['data']['attributes']['name'] == 'Flagship CRM & Ops'
    
    def test_get_nonexistent_template(self, client, auth_headers):
        """Test getting non-existent template."""
        response = client.get('/api/marketplace/templates/nonexistent', headers=auth_headers)
        
        # Should return 401 if auth is required, or 404 if template not found
        assert response.status_code in [401, 404]
        
        if response.status_code == 404:
            data = response.get_json()
            assert 'errors' in data
            assert data['errors'][0]['code'] == 'TEMPLATE_NOT_FOUND'
    
    def test_list_categories_endpoint(self, client, auth_headers):
        """Test categories listing endpoint."""
        response = client.get('/api/marketplace/categories', headers=auth_headers)
        
        # Should return 401 if auth is required, or 200 if successful
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.get_json()
            assert 'data' in data
            assert isinstance(data['data'], list)
            
            # Check for expected categories
            categories = [cat['id'] for cat in data['data']]
            assert 'Sales & Ops' in categories
            assert 'Education' in categories
            assert 'HR & Recruiting' in categories
            assert 'Customer Support' in categories
            assert 'Analytics' in categories
    
    def test_launch_template_endpoint(self, client, auth_headers):
        """Test template launch endpoint."""
        data = {
            'tenant_name': 'Test Tenant',
            'domain': 'test.com',
            'plan': 'starter',
            'seed_demo_data': True
        }
        
        response = client.post(
            '/api/marketplace/templates/flagship-crm/launch',
            json=data,
            headers=auth_headers
        )
        
        # Should return 401 if auth is required, or 201 if successful
        assert response.status_code in [201, 401]
        
        if response.status_code == 201:
            result = response.get_json()
            assert 'data' in result
            assert result['data']['type'] == 'tenant_launch'
            assert result['data']['attributes']['template_slug'] == 'flagship-crm'
            assert result['data']['attributes']['tenant_name'] == 'Test Tenant'
    
    def test_launch_template_missing_tenant_name(self, client, auth_headers):
        """Test template launch with missing tenant name."""
        data = {
            'domain': 'test.com',
            'plan': 'starter'
        }
        
        response = client.post(
            '/api/marketplace/templates/flagship-crm/launch',
            json=data,
            headers=auth_headers
        )
        
        # Should return 401 if auth is required, or 400 if validation fails
        assert response.status_code in [400, 401]
        
        if response.status_code == 400:
            data = response.get_json()
            assert 'errors' in data
            assert data['errors'][0]['code'] == 'MISSING_TENANT_NAME'
    
    def test_launch_nonexistent_template(self, client, auth_headers):
        """Test launching non-existent template."""
        data = {
            'tenant_name': 'Test Tenant',
            'plan': 'starter'
        }
        
        response = client.post(
            '/api/marketplace/templates/nonexistent/launch',
            json=data,
            headers=auth_headers
        )
        
        # Should return 401 if auth is required, or 404 if template not found
        assert response.status_code in [401, 404]
        
        if response.status_code == 404:
            data = response.get_json()
            assert 'errors' in data
            assert data['errors'][0]['code'] == 'TEMPLATE_NOT_FOUND'


class TestMarketplaceFiltering:
    """Test marketplace filtering functionality."""
    
    def test_filter_by_category(self):
        """Test filtering templates by category."""
        templates = load_marketplace_templates()
        
        # Filter by Sales & Ops category
        sales_ops_templates = [t for t in templates if t.get('category') == 'Sales & Ops']
        assert len(sales_ops_templates) >= 1
        assert all(t['category'] == 'Sales & Ops' for t in sales_ops_templates)
        
        # Filter by Education category
        education_templates = [t for t in templates if t.get('category') == 'Education']
        assert len(education_templates) >= 1
        assert all(t['category'] == 'Education' for t in education_templates)
    
    def test_filter_by_tags(self):
        """Test filtering templates by tags."""
        templates = load_marketplace_templates()
        
        # Filter by CRM tag
        crm_templates = [t for t in templates if 'crm' in t.get('tags', [])]
        assert len(crm_templates) >= 1
        assert all('crm' in t['tags'] for t in crm_templates)
        
        # Filter by LMS tag
        lms_templates = [t for t in templates if 'lms' in t.get('tags', [])]
        assert len(lms_templates) >= 1
        assert all('lms' in t['tags'] for t in lms_templates)
    
    def test_search_functionality(self):
        """Test search functionality."""
        templates = load_marketplace_templates()
        
        # Search for "CRM"
        crm_search = [t for t in templates if 'crm' in t['name'].lower() or 'crm' in t['description'].lower()]
        assert len(crm_search) >= 1
        
        # Search for "Learning"
        learning_search = [t for t in templates if 'learning' in t['name'].lower() or 'learning' in t['description'].lower()]
        assert len(learning_search) >= 1


if __name__ == '__main__':
    pytest.main([__file__])
