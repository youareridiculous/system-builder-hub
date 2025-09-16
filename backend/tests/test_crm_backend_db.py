"""
Tests for CRM backend database functionality
"""
import pytest
import json
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path

# Mock decorators before importing the module
with patch("src.auth_api.require_auth", lambda f: f), \
     patch("src.builds_api.require_tenant_dev", lambda f: f):
    
    # Now import the modules with mocked decorators
    import src.builds_api
    import src.scaffold


@pytest.fixture
def temp_generated_dir(tmp_path):
    """Create a temporary generated directory"""
    generated_dir = tmp_path / "generated"
    generated_dir.mkdir()
    
    with patch("src.scaffold.GENERATED_ROOT", str(generated_dir)):
        yield generated_dir


class TestCRMBackendDatabase:
    """Test cases for CRM backend database functionality"""

    def test_crm_backend_creates_data_directory(self, temp_generated_dir):
        """Test that CRM backend creates data directory automatically"""
        build_id = "test-crm-db-123"
        build_data = {
            'name': 'Test CRM',
            'description': 'Test CRM application',
            'template': 'crm_flagship'
        }
        
        # Run scaffold
        src.scaffold.scaffold_crm_flagship(build_id, build_data)
        
        # Check that data directory was created
        data_dir = temp_generated_dir / build_id / "backend" / "data"
        assert data_dir.exists()
        assert data_dir.is_dir()

    def test_crm_backend_db_file_auto_created(self, temp_generated_dir):
        """Test that database file is auto-created when needed"""
        build_id = "test-crm-db-456"
        build_data = {
            'name': 'Test CRM',
            'description': 'Test CRM application',
            'template': 'crm_flagship'
        }
        
        # Run scaffold
        src.scaffold.scaffold_crm_flagship(build_id, build_data)
        
        # Check that db.py was created with proper content
        db_py_path = temp_generated_dir / build_id / "backend" / "db.py"
        assert db_py_path.exists()
        
        # Read the db.py content
        with open(db_py_path, 'r') as f:
            db_content = f.read()
        
        # Check for key functions
        assert "ensure_db_directory()" in db_content
        assert "check_db_exists()" in db_content
        assert "DB_PATH" in db_content
        assert "data/app.db" in db_content

    def test_crm_backend_seed_integration(self, temp_generated_dir):
        """Test that seed.py integrates schema and data creation"""
        build_id = "test-crm-db-789"
        build_data = {
            'name': 'Test CRM',
            'description': 'Test CRM application',
            'template': 'crm_flagship'
        }
        
        # Run scaffold
        src.scaffold.scaffold_crm_flagship(build_id, build_data)
        
        # Check that seed.py was created with proper content
        seed_py_path = temp_generated_dir / build_id / "backend" / "seed.py"
        assert seed_py_path.exists()
        
        # Read the seed.py content
        with open(seed_py_path, 'r') as f:
            seed_content = f.read()
        
        # Check for key functions
        assert "create_schema()" in seed_content
        assert "initialize_database()" in seed_content
        assert "Database initialized with seed data" in seed_content

    def test_crm_backend_app_auto_initialization(self, temp_generated_dir):
        """Test that app.py automatically initializes database on startup"""
        build_id = "test-crm-db-101"
        build_data = {
            'name': 'Test CRM',
            'description': 'Test CRM application',
            'template': 'crm_flagship'
        }
        
        # Run scaffold
        src.scaffold.scaffold_crm_flagship(build_id, build_data)
        
        # Check that app.py was created with proper content
        app_py_path = temp_generated_dir / build_id / "backend" / "app.py"
        assert app_py_path.exists()
        
        # Read the app.py content
        with open(app_py_path, 'r') as f:
            app_content = f.read()
        
        # Check for startup event and database initialization
        assert "@app.on_event(\"startup\")" in app_content
        assert "startup_event()" in app_content
        assert "check_db_exists()" in app_content
        assert "initialize_database()" in app_content
        assert "Database not found, initializing with seed data" in app_content

    def test_crm_backend_router_uses_get_db(self, temp_generated_dir):
        """Test that routers use the get_db function"""
        build_id = "test-crm-db-202"
        build_data = {
            'name': 'Test CRM',
            'description': 'Test CRM application',
            'template': 'crm_flagship'
        }
        
        # Run scaffold
        src.scaffold.scaffold_crm_flagship(build_id, build_data)
        
        # Check accounts router
        accounts_router_path = temp_generated_dir / build_id / "backend" / "routers" / "accounts.py"
        assert accounts_router_path.exists()
        
        with open(accounts_router_path, 'r') as f:
            accounts_content = f.read()
        
        # Check that it uses get_db
        assert "from db import get_db" in accounts_content
        assert "get_db()" in accounts_content

    def test_crm_backend_database_path_correct(self, temp_generated_dir):
        """Test that database path points to correct location"""
        build_id = "test-crm-db-303"
        build_data = {
            'name': 'Test CRM',
            'description': 'Test CRM application',
            'template': 'crm_flagship'
        }
        
        # Run scaffold
        src.scaffold.scaffold_crm_flagship(build_id, build_data)
        
        # Check db.py content
        db_py_path = temp_generated_dir / build_id / "backend" / "db.py"
        with open(db_py_path, 'r') as f:
            db_content = f.read()
        
        # The DB_PATH should point to the data directory (relative path)
        assert "DB_PATH = \"data/app.db\"" in db_content

    def test_crm_backend_schema_creation(self, temp_generated_dir):
        """Test that schema creation includes all required tables"""
        build_id = "test-crm-db-404"
        build_data = {
            'name': 'Test CRM',
            'description': 'Test CRM application',
            'template': 'crm_flagship'
        }
        
        # Run scaffold
        src.scaffold.scaffold_crm_flagship(build_id, build_data)
        
        # Check db.py content for schema
        db_py_path = temp_generated_dir / build_id / "backend" / "db.py"
        with open(db_py_path, 'r') as f:
            db_content = f.read()
        
        # Check for all required tables
        assert "CREATE TABLE IF NOT EXISTS accounts" in db_content
        assert "CREATE TABLE IF NOT EXISTS contacts" in db_content
        assert "CREATE TABLE IF NOT EXISTS deals" in db_content
        assert "CREATE TABLE IF NOT EXISTS pipelines" in db_content
        assert "CREATE TABLE IF NOT EXISTS activities" in db_content

    def test_crm_backend_seed_data_includes_demo_records(self, temp_generated_dir):
        """Test that seed data includes demo records for all tables"""
        build_id = "test-crm-db-505"
        build_data = {
            'name': 'Test CRM',
            'description': 'Test CRM application',
            'template': 'crm_flagship'
        }
        
        # Run scaffold
        src.scaffold.scaffold_crm_flagship(build_id, build_data)
        
        # Check seed.py content for demo data
        seed_py_path = temp_generated_dir / build_id / "backend" / "seed.py"
        with open(seed_py_path, 'r') as f:
            seed_content = f.read()
        
        # Check for demo data inserts
        assert "Acme Corp" in seed_content
        assert "Global Industries" in seed_content
        assert "StartupXYZ" in seed_content
        assert "Enterprise Solutions" in seed_content
        assert "John" in seed_content
        assert "Smith" in seed_content
        assert "Jane" in seed_content
        assert "Doe" in seed_content
        assert "Enterprise License" in seed_content
        assert "Sales Pipeline" in seed_content
        assert "Follow-up Call" in seed_content

    def test_crm_backend_requirements_includes_sqlite3(self, temp_generated_dir):
        """Test that requirements.txt includes necessary dependencies"""
        build_id = "test-crm-db-606"
        build_data = {
            'name': 'Test CRM',
            'description': 'Test CRM application',
            'template': 'crm_flagship'
        }
        
        # Run scaffold
        src.scaffold.scaffold_crm_flagship(build_id, build_data)
        
        # Check requirements.txt
        requirements_path = temp_generated_dir / build_id / "backend" / "requirements.txt"
        assert requirements_path.exists()
        
        with open(requirements_path, 'r') as f:
            requirements_content = f.read()
        
        # Check for required dependencies
        assert "fastapi" in requirements_content
        assert "uvicorn" in requirements_content
        assert "sqlite3" in requirements_content

    def test_crm_backend_manifest_includes_database_info(self, temp_generated_dir):
        """Test that manifest includes database information"""
        build_id = "test-crm-db-707"
        build_data = {
            'name': 'Test CRM',
            'description': 'Test CRM application',
            'template': 'crm_flagship'
        }
        
        # Run scaffold
        src.scaffold.scaffold_crm_flagship(build_id, build_data)
        
        # Check manifest.json
        manifest_path = temp_generated_dir / build_id / "manifest.json"
        assert manifest_path.exists()
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Check manifest content
        assert manifest['name'] == 'Test CRM'
        assert manifest['template'] == 'crm_flagship'
        assert manifest['build_id'] == build_id
        assert 'created_at' in manifest
        assert 'ports' in manifest
