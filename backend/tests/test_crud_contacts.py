import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_create_contact():
    """Test creating a new contact"""
    contact_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone": "123-456-7890",
        "title": "Manager"
    }
    
    response = client.post("/api/contacts/", json=contact_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["first_name"] == contact_data["first_name"]
    assert data["last_name"] == contact_data["last_name"]
    assert data["email"] == contact_data["email"]
    assert "id" in data

def test_get_contact():
    """Test getting a specific contact"""
    # First create a contact
    contact_data = {"first_name": "Jane", "last_name": "Smith"}
    create_response = client.post("/api/contacts/", json=contact_data)
    contact_id = create_response.json()["id"]
    
    # Then get it
    response = client.get(f"/api/contacts/{contact_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["first_name"] == contact_data["first_name"]
    assert data["id"] == contact_id

def test_update_contact():
    """Test updating a contact"""
    # First create a contact
    contact_data = {"first_name": "Original", "last_name": "Name"}
    create_response = client.post("/api/contacts/", json=contact_data)
    contact_id = create_response.json()["id"]
    
    # Then update it
    update_data = {"first_name": "Updated", "email": "updated@example.com"}
    response = client.put(f"/api/contacts/{contact_id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["first_name"] == update_data["first_name"]
    assert data["email"] == update_data["email"]

def test_delete_contact():
    """Test deleting a contact"""
    # First create a contact
    contact_data = {"first_name": "To", "last_name": "Delete"}
    create_response = client.post("/api/contacts/", json=contact_data)
    contact_id = create_response.json()["id"]
    
    # Then delete it
    response = client.delete(f"/api/contacts/{contact_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Contact deleted successfully"
    
    # Verify it's gone
    get_response = client.get(f"/api/contacts/{contact_id}")
    assert get_response.status_code == 404

def test_create_contact_validation():
    """Test contact creation validation"""
    # Test missing required field
    contact_data = {"first_name": "John"}
    response = client.post("/api/contacts/", json=contact_data)
    assert response.status_code == 422
