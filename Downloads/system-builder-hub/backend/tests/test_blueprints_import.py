"""
Test blueprint imports and registration
"""

import importlib
import pytest

def test_cobuilder_imports():
    """Test Co-Builder module imports"""
    importlib.import_module("src.cobuilder.router")
    m = importlib.import_module("src.cobuilder.api")
    assert hasattr(m, "cobuilder_bp")

def test_ops_imports():
    """Test Ops module imports"""
    m = importlib.import_module("src.ops.api")
    assert hasattr(m, "ops_bp")

def test_growth_imports():
    """Test Growth module imports"""
    m = importlib.import_module("src.growth.api")
    assert hasattr(m, "growth_bp")

def test_blueprints_registered():
    """Test that blueprints are registered in the app"""
    from src.app import create_app
    app = create_app()
    rules = {r.rule for r in app.url_map.iter_rules()}
    
    # Check that our API endpoints are registered
    assert any("/api/cobuilder" in r for r in rules), "Co-Builder routes not found"
    assert any("/api/ops" in r for r in rules), "Ops routes not found"
    assert any("/api/growth" in r for r in rules), "Growth routes not found"

if __name__ == "__main__":
    # Run tests
    test_cobuilder_imports()
    test_ops_imports()
    test_growth_imports()
    test_blueprints_registered()
    print("✅ All blueprint import tests passed!")
