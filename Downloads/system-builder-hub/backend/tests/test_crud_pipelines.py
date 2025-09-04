import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_create_pipeline():
    """Test creating a new pipeline"""
    pipeline_data = {
        "name": "Test Pipeline",
        "description": "A test pipeline"
    }
    
    response = client.post("/api/pipelines/", json=pipeline_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == pipeline_data["name"]
    assert data["description"] == pipeline_data["description"]
    assert "id" in data

def test_get_pipeline():
    """Test getting a specific pipeline"""
    # First create a pipeline
    pipeline_data = {"name": "Test Pipeline"}
    create_response = client.post("/api/pipelines/", json=pipeline_data)
    pipeline_id = create_response.json()["id"]
    
    # Then get it
    response = client.get(f"/api/pipelines/{pipeline_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == pipeline_data["name"]
    assert data["id"] == pipeline_id

def test_update_pipeline():
    """Test updating a pipeline"""
    # First create a pipeline
    pipeline_data = {"name": "Original Pipeline"}
    create_response = client.post("/api/pipelines/", json=pipeline_data)
    pipeline_id = create_response.json()["id"]
    
    # Then update it
    update_data = {"name": "Updated Pipeline", "description": "Updated description"}
    response = client.put(f"/api/pipelines/{pipeline_id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]

def test_delete_pipeline():
    """Test deleting a pipeline"""
    # First create a pipeline
    pipeline_data = {"name": "To Delete"}
    create_response = client.post("/api/pipelines/", json=pipeline_data)
    pipeline_id = create_response.json()["id"]
    
    # Then delete it
    response = client.delete(f"/api/pipelines/{pipeline_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Pipeline deleted successfully"
    
    # Verify it's gone
    get_response = client.get(f"/api/pipelines/{pipeline_id}")
    assert get_response.status_code == 404

def test_create_pipeline_validation():
    """Test pipeline creation validation"""
    # Test missing required field
    pipeline_data = {"description": "No name"}
    response = client.post("/api/pipelines/", json=pipeline_data)
    assert response.status_code == 422
