"""
Test the centralized events logger
"""

import pytest
from src.events import log_event, get_recent_events, clear_schema_cache

def test_log_event_basic():
    """Test basic event logging"""
    # Clear cache to ensure fresh schema detection
    clear_schema_cache()
    
    # Test logging a simple event
    result = log_event("test_event", tenant_id="demo", module="test", payload={"test": True})
    
    # Should return True on success
    assert result is True

def test_log_event_without_app_context():
    """Test logging without Flask app context (should fail gracefully)"""
    # Clear cache
    clear_schema_cache()
    
    # This should fail gracefully without app context
    result = log_event("test_event", tenant_id="demo")
    
    # Should return False when no app context
    assert result is False

def test_get_recent_events():
    """Test retrieving recent events"""
    # This will only work with app context
    events = get_recent_events(tenant_id="demo", limit=5)
    
    # Should return a list (empty if no events)
    assert isinstance(events, list)
