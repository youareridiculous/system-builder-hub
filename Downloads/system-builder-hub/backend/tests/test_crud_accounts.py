import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_create_account():
    """Test creating a new account"""
    account_data = {
        "name": "Test Company",
        "industry": "Technology",
        "website": "https://testcompany.com"
    }
    
    response = client.post("/api/accounts/", json=account_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == account_data["name"]
    assert data["industry"] == account_data["industry"]
    assert data["website"] == account_data["website"]
    assert "id" in data

def test_get_account():
    """Test getting a specific account"""
    # First create an account
    account_data = {"name": "Test Account", "industry": "Test"}
    create_response = client.post("/api/accounts/", json=account_data)
    account_id = create_response.json()["id"]
    
    # Then get it
    response = client.get(f"/api/accounts/{account_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == account_data["name"]
    assert data["id"] == account_id

def test_update_account():
    """Test updating an account"""
    # First create an account
    account_data = {"name": "Original Name", "industry": "Original"}
    create_response = client.post("/api/accounts/", json=account_data)
    account_id = create_response.json()["id"]
    
    # Then update it
    update_data = {"name": "Updated Name", "industry": "Updated"}
    response = client.put(f"/api/accounts/{account_id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["industry"] == update_data["industry"]

def test_delete_account():
    """Test deleting an account"""
    # First create an account
    account_data = {"name": "To Delete", "industry": "Test"}
    create_response = client.post("/api/accounts/", json=account_data)
    account_id = create_response.json()["id"]
    
    # Then delete it
    response = client.delete(f"/api/accounts/{account_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Account deleted successfully"
    
    # Verify it's gone
    get_response = client.get(f"/api/accounts/{account_id}")
    assert get_response.status_code == 404

def test_get_nonexistent_account():
    """Test getting a non-existent account"""
    response = client.get("/api/accounts/99999")
    assert response.status_code == 404

def test_update_nonexistent_account():
    """Test updating a non-existent account"""
    update_data = {"name": "Updated Name"}
    response = client.put("/api/accounts/99999", json=update_data)
    assert response.status_code == 404

def test_delete_nonexistent_account():
    """Test deleting a non-existent account"""
    response = client.delete("/api/accounts/99999")
    assert response.status_code == 404

def test_create_account_validation():
    """Test account creation validation"""
    # Test missing required field
    account_data = {"industry": "Technology"}
    response = client.post("/api/accounts/", json=account_data)
    assert response.status_code == 422
