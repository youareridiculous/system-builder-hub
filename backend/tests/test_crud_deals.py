import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_create_deal():
    """Test creating a new deal"""
    deal_data = {
        "title": "Test Deal",
        "amount": 50000.0,
        "stage": "prospecting"
    }
    
    response = client.post("/api/deals/", json=deal_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == deal_data["title"]
    assert data["amount"] == deal_data["amount"]
    assert data["stage"] == deal_data["stage"]
    assert "id" in data

def test_get_deal():
    """Test getting a specific deal"""
    # First create a deal
    deal_data = {"title": "Test Deal", "amount": 10000.0}
    create_response = client.post("/api/deals/", json=deal_data)
    deal_id = create_response.json()["id"]
    
    # Then get it
    response = client.get(f"/api/deals/{deal_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == deal_data["title"]
    assert data["id"] == deal_id

def test_update_deal():
    """Test updating a deal"""
    # First create a deal
    deal_data = {"title": "Original Deal", "amount": 10000.0}
    create_response = client.post("/api/deals/", json=deal_data)
    deal_id = create_response.json()["id"]
    
    # Then update it
    update_data = {"title": "Updated Deal", "stage": "negotiation"}
    response = client.put(f"/api/deals/{deal_id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["stage"] == update_data["stage"]

def test_delete_deal():
    """Test deleting a deal"""
    # First create a deal
    deal_data = {"title": "To Delete", "amount": 5000.0}
    create_response = client.post("/api/deals/", json=deal_data)
    deal_id = create_response.json()["id"]
    
    # Then delete it
    response = client.delete(f"/api/deals/{deal_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Deal deleted successfully"
    
    # Verify it's gone
    get_response = client.get(f"/api/deals/{deal_id}")
    assert get_response.status_code == 404

def test_create_deal_validation():
    """Test deal creation validation"""
    # Test missing required field
    deal_data = {"amount": 10000.0}
    response = client.post("/api/deals/", json=deal_data)
    assert response.status_code == 422
