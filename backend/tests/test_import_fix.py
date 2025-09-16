#!/usr/bin/env python3
"""
Test to verify that src modules can be imported without manual path hacks
"""

def test_src_import():
    """Test that src modules can be imported"""
    import src
    assert src is not None

def test_src_app_import():
    """Test that src.app can be imported"""
    from src.app import create_app
    assert create_app is not None

def test_src_cli_import():
    """Test that src.cli can be imported"""
    import src.cli
    assert src.cli is not None

def test_src_builds_api_import():
    """Test that src.builds_api can be imported"""
    import src.builds_api
    assert src.builds_api is not None
