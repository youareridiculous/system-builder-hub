"""
Tests for the dependency checking system
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from src.dependency_check import (
    collect_dependency_status, 
    _is_development_environment, 
    _is_sqlite_database,
    _check_module_availability
)

class TestDependencyCheck:
    
    def test_development_environment_detection(self):
        """Test development environment detection"""
        # Test with FLASK_ENV
        with patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            assert _is_development_environment() == True
        
        # Test with SBH_ENV
        with patch.dict(os.environ, {'SBH_ENV': 'dev'}):
            assert _is_development_environment() == True
        
        # Test with ENVIRONMENT
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            assert _is_development_environment() == True
        
        # Test production environment
        with patch.dict(os.environ, {'FLASK_ENV': 'production'}):
            assert _is_development_environment() == False
        
        # Test with no environment variables
        with patch.dict(os.environ, {}, clear=True):
            assert _is_development_environment() == False
    
    def test_sqlite_database_detection(self):
        """Test SQLite database detection"""
        # Test with sqlite URL
        with patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///test.db'}):
            assert _is_sqlite_database() == True
        
        # Test with PostgreSQL URL
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://user:pass@localhost/db'}):
            assert _is_sqlite_database() == False
        
        # Test with no DATABASE_URL
        with patch.dict(os.environ, {}, clear=True):
            assert _is_sqlite_database() == True
    
    @patch('src.dependency_check.importlib.import_module')
    def test_module_availability_check(self, mock_import):
        """Test module availability checking"""
        # Test successful import
        mock_import.return_value = MagicMock()
        assert _check_module_availability('flask') == True
        
        # Test failed import
        mock_import.side_effect = ImportError("No module named 'nonexistent'")
        assert _check_module_availability('nonexistent') == False
    
    @patch('src.dependency_check._is_development_environment')
    @patch('src.dependency_check._is_sqlite_database')
    @patch('src.dependency_check._check_module_availability')
    def test_collect_dependency_status_dev_sqlite(self, mock_check, mock_sqlite, mock_dev):
        """Test dependency status collection in development with SQLite"""
        mock_dev.return_value = True
        mock_sqlite.return_value = True
        
        # Mock all required deps as available
        def mock_check_impl(module):
            required = ["flask", "flask_cors", "sqlalchemy", "alembic", "cryptography",
                       "requests", "werkzeug", "jwt", "prometheus_client"]
            return module in required
        
        mock_check.side_effect = mock_check_impl
        
        status = collect_dependency_status()
        
        assert status["deps"] == True
        assert status["required_missing"] == []
        assert "psycopg2" in status["optional_missing"]  # Should be optional in dev/sqlite
        assert status["environment"]["is_development"] == True
        assert status["environment"]["is_sqlite"] == True
    
    @patch('src.dependency_check._is_development_environment')
    @patch('src.dependency_check._is_sqlite_database')
    @patch('src.dependency_check._check_module_availability')
    def test_collect_dependency_status_prod_postgres(self, mock_check, mock_sqlite, mock_dev):
        """Test dependency status collection in production with PostgreSQL"""
        mock_dev.return_value = False
        mock_sqlite.return_value = False
        
        # Mock all required deps as available (including psycopg2)
        def mock_check_impl(module):
            required = ["flask", "flask_cors", "sqlalchemy", "alembic", "cryptography",
                       "requests", "werkzeug", "jwt", "prometheus_client", "psycopg2"]
            return module in required
        
        mock_check.side_effect = mock_check_impl
        
        status = collect_dependency_status()
        
        assert status["deps"] == True
        assert status["required_missing"] == []
        assert "psycopg2" not in status["optional_missing"]  # Should be required in prod/postgres
        assert status["environment"]["is_development"] == False
        assert status["environment"]["is_sqlite"] == False
    
    @patch('src.dependency_check._is_development_environment')
    @patch('src.dependency_check._is_sqlite_database')
    @patch('src.dependency_check._check_module_availability')
    def test_missing_required_dependencies(self, mock_check, mock_sqlite, mock_dev):
        """Test handling of missing required dependencies"""
        mock_dev.return_value = True
        mock_sqlite.return_value = True
        
        # Mock some required deps as missing
        def mock_check_impl(module):
            available = ["flask", "flask_cors"]  # Only some available
            return module in available
        
        mock_check.side_effect = mock_check_impl
        
        status = collect_dependency_status()
        
        assert status["deps"] == False
        assert len(status["required_missing"]) > 0
        assert "sqlalchemy" in status["required_missing"]
        assert "alembic" in status["required_missing"]
    
    def test_clean_json_schema(self):
        """Test that the response has a clean JSON schema"""
        status = collect_dependency_status()
        
        # Verify required fields exist and have correct types
        assert "deps" in status
        assert isinstance(status["deps"], bool)
        
        assert "required_missing" in status
        assert isinstance(status["required_missing"], list)
        # All items should be strings
        for item in status["required_missing"]:
            assert isinstance(item, str)
        
        assert "optional_missing" in status
        assert isinstance(status["optional_missing"], list)
        # All items should be strings
        for item in status["optional_missing"]:
            assert isinstance(item, str)
        
        assert "summary" in status
        assert isinstance(status["summary"], dict)
        
        assert "environment" in status
        assert isinstance(status["environment"], dict)
