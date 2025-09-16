import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_create_activity():
    """Test creating a new activity"""
    activity_data = {
        "type": "call",
        "subject": "Test Call",
        "description": "A test activity",
        "completed": False
    }
    
    response = client.post("/api/activities/", json=activity_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["type"] == activity_data["type"]
    assert data["subject"] == activity_data["subject"]
    assert data["completed"] == activity_data["completed"]
    assert "id" in data

def test_get_activity():
    """Test getting a specific activity"""
    # First create an activity
    activity_data = {"type": "email", "subject": "Test Email"}
    create_response = client.post("/api/activities/", json=activity_data)
    activity_id = create_response.json()["id"]
    
    # Then get it
    response = client.get(f"/api/activities/{activity_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["type"] == activity_data["type"]
    assert data["id"] == activity_id

def test_update_activity():
    """Test updating an activity"""
    # First create an activity
    activity_data = {"type": "meeting", "subject": "Original Meeting"}
    create_response = client.post("/api/activities/", json=activity_data)
    activity_id = create_response.json()["id"]
    
    # Then update it
    update_data = {"subject": "Updated Meeting", "completed": True}
    response = client.put(f"/api/activities/{activity_id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["subject"] == update_data["subject"]
    assert data["completed"] == update_data["completed"]

def test_delete_activity():
    """Test deleting an activity"""
    # First create an activity
    activity_data = {"type": "task", "subject": "To Delete"}
    create_response = client.post("/api/activities/", json=activity_data)
    activity_id = create_response.json()["id"]
    
    # Then delete it
    response = client.delete(f"/api/activities/{activity_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Activity deleted successfully"
    
    # Verify it's gone
    get_response = client.get(f"/api/activities/{activity_id}")
    assert get_response.status_code == 404

def test_create_activity_validation():
    """Test activity creation validation"""
    # Test missing required field
    activity_data = {"subject": "No type"}
    response = client.post("/api/activities/", json=activity_data)
    assert response.status_code == 422
