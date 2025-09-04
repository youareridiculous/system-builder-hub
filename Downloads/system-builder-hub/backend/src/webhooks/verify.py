"""
Webhook signature verification
"""
import hmac
import hashlib
import time
from typing import Optional

def verify_signature(secret: str, timestamp: str, body: str, signature: str, tolerance_seconds: int = 300) -> bool:
    """
    Verify webhook signature
    
    Args:
        secret: Webhook secret
        timestamp: Request timestamp
        body: Request body
        signature: Expected signature
        tolerance_seconds: Time tolerance in seconds (default 5 minutes)
    
    Returns:
        True if signature is valid
    """
    try:
        # Check timestamp tolerance
        request_time = int(timestamp) / 1000  # Convert from milliseconds
        current_time = time.time()
        
        if abs(current_time - request_time) > tolerance_seconds:
            return False
        
        # Create expected signature
        message = f"{timestamp}.{body}"
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
        
    except (ValueError, TypeError):
        return False

def extract_signature_components(signature: str) -> Optional[str]:
    """Extract signature value from 'sha256=...' format"""
    if signature.startswith('sha256='):
        return signature[7:]  # Remove 'sha256=' prefix
    return None
