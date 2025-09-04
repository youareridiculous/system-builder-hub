"""
Tests for builds UI routes
"""
import pytest
from unittest.mock import patch
from flask import Flask

# Mock decorators before importing the module
with patch("src.preview_ui.require_auth", lambda f: f):
    import src.preview_ui


@pytest.fixture
def app():
    """Create a test Flask app with the preview UI blueprint"""
    import os
    app = Flask(__name__, template_folder=os.path.join(os.getcwd(), 'templates'))
    app.config['TESTING'] = True
    app.register_blueprint(src.preview_ui.bp)
    return app


@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()


class TestBuildsUIRoutes:
    """Test cases for builds UI routes"""

    def test_ui_builds_route_returns_200(self, client):
        """Test that /ui/builds returns 200 and includes table container"""
        response = client.get('/ui/builds')
        
        assert response.status_code == 200
        assert b'builds-content' in response.data  # Table container marker
        assert b'Builds Dashboard' in response.data  # Page title

    def test_ui_builds_route_includes_table_structure(self, client):
        """Test that the builds page includes the expected table structure"""
        response = client.get('/ui/builds')
        
        assert response.status_code == 200
        # Check for table structure
        assert b'<table' in response.data
        assert b'builds-table' in response.data
        # Check for table headers
        assert b'<th>ID</th>' in response.data
        assert b'<th>Name</th>' in response.data
        assert b'<th>Template</th>' in response.data
        assert b'<th>Status</th>' in response.data
        assert b'<th>Created</th>' in response.data

    def test_ui_builds_route_includes_detail_drawer(self, client):
        """Test that the builds page includes the detail drawer structure"""
        response = client.get('/ui/builds')
        
        assert response.status_code == 200
        # Check for detail drawer
        assert b'detail-drawer' in response.data
        assert b'drawer-content' in response.data
        # Check for drawer header
        assert b'Build Details' in response.data

    def test_ui_builds_route_includes_refresh_button(self, client):
        """Test that the builds page includes the refresh button"""
        response = client.get('/ui/builds')
        
        assert response.status_code == 200
        # Check for refresh button
        assert b'refresh-btn' in response.data
        assert b'Refresh' in response.data
