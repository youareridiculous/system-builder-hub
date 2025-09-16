"""
Tests for full build progress tracking
"""
import json
import time
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


def test_full_build_creates_build_record(client):
    """Test that POST /full_build creates a build record and returns 202"""
    resp = client.post("/api/cobuilder/full_build",
                       data=json.dumps({"message": "Create /studio directory"}),
                       content_type="application/json",
                       headers={"X-Tenant-ID": "demo"})
    
    assert resp.status_code == 202
    data = resp.get_json()
    assert "data" in data
    assert "build_id" in data["data"]
    assert data["data"]["ok"] is True
    
    # Store build_id for other tests to use
    test_full_build_creates_build_record.build_id = data["data"]["build_id"]


def test_progress_endpoint_returns_build_info(client):
    """Test that progress endpoint returns build info (not 'Build not found')"""
    # First create a build
    test_full_build_creates_build_record(client)
    build_id = test_full_build_creates_build_record.build_id
    
    # Wait a moment for the build to be registered
    time.sleep(0.1)
    
    # Check progress
    resp = client.get(f"/api/cobuilder/full_build/{build_id}/progress",
                      headers={"X-Tenant-ID": "demo"})
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert "data" in data
    
    # Should not be "Build not found"
    assert "error" not in data["data"] or data["data"]["error"] != "Build not found"
    
    # Should have build info
    if "build" in data["data"]:
        build_info = data["data"]["build"]
        assert "build_id" in build_info
        assert "status" in build_info
        assert build_info["build_id"] == build_id


def test_list_builds_endpoint(client):
    """Test that list builds endpoint returns the new build"""
    # First create a build
    test_full_build_creates_build_record(client)
    build_id = test_full_build_creates_build_record.build_id
    
    # Wait a moment for the build to be registered
    time.sleep(0.1)
    
    # List builds
    resp = client.get("/api/cobuilder/builds",
                      headers={"X-Tenant-ID": "demo"})
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert "data" in data
    assert "builds" in data["data"]
    
    # Should contain our build
    builds = data["data"]["builds"]
    build_ids = [build["build_id"] for build in builds]
    assert build_id in build_ids
