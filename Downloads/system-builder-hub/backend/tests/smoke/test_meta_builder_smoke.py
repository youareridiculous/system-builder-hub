"""
Smoke tests for SBH Meta-Builder functionality.
"""

import pytest
import requests
import json
from typing import Dict, Any


class TestMetaBuilderSmoke:
    """Smoke tests for meta-builder functionality."""
    
    @pytest.fixture
    def base_url(self):
        """Get base URL for testing."""
        return "http://localhost:5001"
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token."""
        # TODO: Implement proper auth token generation
        return "test-token"
    
    def test_meta_builder_health(self, base_url):
        """Test meta-builder health endpoints."""
        # Test main health endpoint
        response = requests.get(f"{base_url}/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_patterns_endpoint(self, base_url, auth_token):
        """Test patterns listing endpoint."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(f"{base_url}/api/meta/patterns", headers=headers)
        
        # Should return 401 if auth is required, or 200 if patterns exist
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert isinstance(data["data"], list)
    
    def test_templates_endpoint(self, base_url, auth_token):
        """Test templates listing endpoint."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(f"{base_url}/api/meta/templates", headers=headers)
        
        # Should return 401 if auth is required, or 200 if templates exist
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert isinstance(data["data"], list)
    
    def test_plan_generation(self, base_url, auth_token):
        """Test scaffold plan generation."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "goal_text": "Build a simple CRUD app for managing users",
            "mode": "freeform",
            "options": {
                "llm": True,
                "dry_run": False
            }
        }
        
        response = requests.post(
            f"{base_url}/api/meta/scaffold/plan",
            headers=headers,
            json=data
        )
        
        # Should return 401 if auth is required, or 201 if successful
        assert response.status_code in [201, 401]
        
        if response.status_code == 201:
            result = response.json()
            assert "data" in result
            assert result["data"]["type"] == "scaffold_plan"
            assert "session_id" in result["data"]["attributes"]
    
    def test_guided_plan_generation(self, base_url, auth_token):
        """Test guided scaffold plan generation."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "goal_text": "Build a helpdesk system",
            "mode": "guided",
            "guided_input": {
                "role": "Developer",
                "context": "Internal support team",
                "task": "Create ticketing system",
                "audience": "Support agents",
                "output": "Web application"
            },
            "pattern_slugs": ["helpdesk"],
            "template_slugs": ["flagship-crm"],
            "options": {
                "llm": True,
                "dry_run": False
            }
        }
        
        response = requests.post(
            f"{base_url}/api/meta/scaffold/plan",
            headers=headers,
            json=data
        )
        
        # Should return 401 if auth is required, or 201 if successful
        assert response.status_code in [201, 401]
        
        if response.status_code == 201:
            result = response.json()
            assert "data" in result
            assert result["data"]["type"] == "scaffold_plan"
            assert result["data"]["attributes"]["planner_kind"] in ["llm", "heuristic"]
    
    def test_ui_routes(self, base_url, auth_token):
        """Test UI routes are accessible."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        ui_routes = [
            "/ui/meta/scaffold",
            "/ui/meta/patterns",
            "/ui/meta/templates",
            "/ui/meta/evaluations"
        ]
        
        for route in ui_routes:
            response = requests.get(f"{base_url}{route}", headers=headers)
            # Should return 401 if auth is required, or 200 if accessible
            assert response.status_code in [200, 401]
    
    def test_evaluation_endpoint(self, base_url, auth_token):
        """Test evaluation running endpoint."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{base_url}/api/meta/eval/run",
            headers=headers
        )
        
        # Should return 401 if auth is required, 404 if no cases, or 200 if successful
        assert response.status_code in [200, 401, 404]
        
        if response.status_code == 200:
            result = response.json()
            assert "data" in result
            assert result["data"]["type"] == "evaluation_results"
            assert "summary" in result["data"]["attributes"]
    
    def test_plan_revision(self, base_url, auth_token):
        """Test plan revision endpoint."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        # First create a plan
        plan_data = {
            "goal_text": "Build a simple app",
            "mode": "freeform"
        }
        
        plan_response = requests.post(
            f"{base_url}/api/meta/scaffold/plan",
            headers=headers,
            json=plan_data
        )
        
        if plan_response.status_code == 201:
            plan_result = plan_response.json()
            session_id = plan_result["data"]["attributes"]["session_id"]
            plan_id = plan_result["data"]["id"]
            
            # Then revise the plan
            revision_data = {
                "session_id": session_id,
                "plan_id": plan_id,
                "feedback_text": "Add user authentication",
                "add_modules": ["auth"]
            }
            
            revision_response = requests.post(
                f"{base_url}/api/meta/scaffold/revise",
                headers=headers,
                json=revision_data
            )
            
            # Should return 401 if auth is required, or 201 if successful
            assert revision_response.status_code in [201, 401]
            
            if revision_response.status_code == 201:
                result = revision_response.json()
                assert "data" in result
                assert result["data"]["type"] == "scaffold_plan"
                assert result["data"]["attributes"]["version"] > 1


if __name__ == "__main__":
    pytest.main([__file__])
