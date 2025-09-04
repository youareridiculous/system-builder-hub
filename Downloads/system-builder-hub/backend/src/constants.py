"""
System Builder Hub constants

Centralized constants for the application, including tenant management
and logging utilities.
"""

import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Tenant constants
SYSTEM_TENANT_KEY = "system"
SYSTEM_TENANT_ID = "00000000000000000000000000000000"  # 32 hex
DEMO_TENANT_KEY = "demo"
DEMO_TENANT_ID = "demo"  # Keep as plain "demo" for DB compatibility

# Throttled warning system
_WARNING_THROTTLE: Dict[str, float] = {}
WARNING_THROTTLE_SECONDS = 60

def throttled_warning(message: str, key: str = None) -> None:
    """
    Log a warning message, but throttle repeated identical messages.
    
    Args:
        message: The warning message to log
        key: Optional key for throttling (defaults to message content)
    """
    if key is None:
        key = message
    
    now = time.time()
    last_warned = _WARNING_THROTTLE.get(key, 0)
    
    if now - last_warned >= WARNING_THROTTLE_SECONDS:
        logger.warning(message)
        _WARNING_THROTTLE[key] = now

def normalize_tenant_id(raw: Optional[str]) -> str:
    """
    Normalize tenant ID to canonical form.
    
    Args:
        raw: Raw tenant ID from header, body, or query param
        
    Returns:
        Normalized tenant ID string
    """
    if not raw:
        return DEMO_TENANT_ID
    
    raw_str = str(raw).strip()
    
    # Handle system tenant
    if raw_str.lower() == SYSTEM_TENANT_KEY or raw_str == SYSTEM_TENANT_ID:
        return SYSTEM_TENANT_ID
    
    # Handle demo tenant
    if raw_str.lower() == DEMO_TENANT_KEY or raw_str == DEMO_TENANT_ID:
        return DEMO_TENANT_ID
    
    # Check if it's a 32-character hex string (valid tenant ID)
    if len(raw_str) == 32 and all(c in '0123456789abcdefABCDEF' for c in raw_str):
        return raw_str.lower()
    
    # Log throttled warning for malformed values
    throttled_warning(
        f"Malformed tenant ID: '{raw_str}', falling back to demo",
        f"malformed_tenant_{raw_str}"
    )
    
    return DEMO_TENANT_ID

def get_friendly_tenant_key(normalized_id: str) -> str:
    """
    Convert normalized tenant ID back to human-readable key for API responses.
    
    Args:
        normalized_id: Normalized tenant ID (e.g., "00000000000000000000000000000000")
        
    Returns:
        Human-readable tenant key (e.g., "system", "demo")
    """
    if normalized_id == SYSTEM_TENANT_ID:
        return SYSTEM_TENANT_KEY
    elif normalized_id == DEMO_TENANT_ID:
        return DEMO_TENANT_KEY
    else:
        # For custom tenant IDs, return as-is (they're already human-readable)
        return normalized_id
