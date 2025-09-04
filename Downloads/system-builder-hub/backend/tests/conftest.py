"""
Test configuration and fixtures for the builds API tests
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def mock_auth_decorators():
    """Mock authentication and tenancy decorators globally for all tests"""
    patches = []
    try:
        # Only patch if the module exists
        import src.builds_api
        patches.extend([
            patch("src.builds_api.require_auth", lambda f: f),
            patch("src.builds_api.require_tenant_dev", lambda f: f),
            patch("src.builds_api.require_tenant", lambda f: f)
        ])
    except ImportError:
        # Module doesn't exist, skip patching
        pass
    
    if patches:
        with patches[0], patches[1], patches[2]:
            yield
    else:
        yield


@pytest.fixture(autouse=True)
def mock_tenant_context():
    """Mock tenant context functions for tests"""
    patches = []
    try:
        # Only patch if the module exists
        import src.tenancy.context
        patches.extend([
            patch("src.tenancy.context.get_current_tenant_id", return_value="test-tenant"),
            patch("src.tenancy.context.get_current_tenant", return_value={"id": "test-tenant", "name": "Test Tenant"})
        ])
    except ImportError:
        # Module doesn't exist, skip patching
        pass
    
    if patches:
        with patches[0], patches[1]:
            yield
    else:
        yield


@pytest.fixture
def mock_db_connection():
    """Mock database connection for tests"""
    with patch("src.builds_api.get_db_connection") as mock_get_db:
        # Create a mock database connection
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_db.execute.return_value = mock_cursor
        mock_db.commit.return_value = None
        mock_get_db.return_value = mock_db
        yield mock_db, mock_cursor


@pytest.fixture
def mock_build_data():
    """Sample build data for tests"""
    return {
        'id': 'test-build-123',
        'name': 'Test Build',
        'description': 'Test Description',
        'template': 'test-template',
        'status': 'completed',
        'created_at': '2025-08-28 04:52:05.046183'
    }


@pytest.fixture
def mock_log_data():
    """Sample log data for tests"""
    return {
        'id': 'test-log-123',
        'build_id': 'test-build-123',
        'message': 'Test log message',
        'created_at': '2025-08-28 04:52:05.046183'
    }
