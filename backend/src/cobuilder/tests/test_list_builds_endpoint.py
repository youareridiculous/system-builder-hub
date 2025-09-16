"""
Tests for list builds endpoint
"""
import json
import pytest
from flask import Flask


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    from src.app import create_app
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


def test_list_builds_endpoint(client):
    """Test that the list builds endpoint returns proper JSON"""
    # ensure endpoint returns JSON (even when empty)
    resp = client.get("/api/cobuilder/builds?limit=5", headers={"X-Tenant-ID": "demo"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "data" in data
    assert "success" in data and data["success"] is True
    assert "tenant_id" in data
