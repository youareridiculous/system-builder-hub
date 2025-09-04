"""
Integration tests for readiness endpoint
"""
import pytest
from src.app import create_app

@pytest.fixture
def app():
    """Create test app"""
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

def test_readiness_endpoint_includes_deps(client):
    """Test that /readiness endpoint includes dependency status"""
    response = client.get('/readiness')
    
    assert response.status_code == 200
    data = response.get_json()
    
    # Check that deps field is present
    assert 'deps' in data
    assert isinstance(data['deps'], bool)
    
    # Check other required fields
    assert 'status' in data
    assert 'version' in data
    assert 'total_deps' in data
    assert 'available_deps' in data
    
    # If deps is True, there should be no missing deps
    if data['deps']:
        assert data['missing_deps'] == []
    else:
        assert 'missing_deps' in data
        assert isinstance(data['missing_deps'], list)

def test_readiness_endpoint_structure(client):
    """Test readiness endpoint response structure"""
    response = client.get('/readiness')
    
    assert response.status_code == 200
    data = response.get_json()
    
    # Verify all expected fields
    expected_fields = ['status', 'version', 'deps', 'total_deps', 'available_deps']
    for field in expected_fields:
        assert field in data, f"Missing field: {field}"
    
    # Verify field types
    assert isinstance(data['status'], str)
    assert isinstance(data['version'], str)
    assert isinstance(data['deps'], bool)
    assert isinstance(data['total_deps'], int)
    assert isinstance(data['available_deps'], int)
    
    # Verify logical constraints
    assert data['available_deps'] <= data['total_deps']
    assert data['status'] in ['ready', 'not_ready', 'error']
