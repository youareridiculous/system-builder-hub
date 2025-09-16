"""
Route tests for Co-Builder API endpoints
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


def test_full_build_route_exposed(client):
    """Test that the full_build route is properly exposed (not 404)"""
    # Missing message should 400, but proves the route is bound (not 404)
    resp = client.post("/api/cobuilder/full_build",
                       data=json.dumps({}),
                       content_type="application/json",
                       headers={"X-Tenant-ID": "demo"})
    assert resp.status_code in (400, 422)
