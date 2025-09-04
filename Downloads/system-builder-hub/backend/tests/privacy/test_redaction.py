"""
Tests for Data Redaction & Retention
"""

import pytest
from src.privacy.redaction import RedactionEngine, RetentionPolicy, redaction_engine, retention_policy


class TestRedactionEngine:
    """Test redaction engine functionality."""
    
    def test_email_redaction(self):
        """Test email address redaction."""
        text = "Contact us at john.doe@example.com or support@company.org"
        redacted, log = redaction_engine.redact_text(text)
        
        assert "[EMAIL_REDACTED]" in redacted
        assert "john.doe@example.com" not in redacted
        assert "support@company.org" not in redacted
        assert len(log) == 2
        assert log[0]["rule"] == "email"
        assert log[0]["severity"] == "high"
    
    def test_phone_redaction(self):
        """Test phone number redaction."""
        text = "Call us at (555) 123-4567 or +1-800-555-0123"
        redacted, log = redaction_engine.redact_text(text)
        
        assert "[PHONE_REDACTED]" in redacted
        assert "(555) 123-4567" not in redacted
        assert "+1-800-555-0123" not in redacted
        assert len(log) >= 1
        assert log[0]["rule"] == "phone"
    
    def test_credit_card_redaction(self):
        """Test credit card number redaction."""
        text = "Card number: 4111-1111-1111-1111"
        redacted, log = redaction_engine.redact_text(text)
        
        assert "[CC_REDACTED]" in redacted
        assert "4111-1111-1111-1111" not in redacted
        assert len(log) == 1
        assert log[0]["rule"] == "credit_card"
        assert log[0]["severity"] == "critical"
    
    def test_api_key_redaction(self):
        """Test API key redaction."""
        text = "API key: sk-1234567890abcdef1234567890abcdef1234567890"
        redacted, log = redaction_engine.redact_text(text)
        
        assert "[API_KEY_REDACTED]" in redacted
        assert "sk-1234567890abcdef1234567890abcdef1234567890" not in redacted
        assert len(log) == 1
        assert log[0]["rule"] == "api_key"
        assert log[0]["severity"] == "critical"
    
    def test_aws_key_redaction(self):
        """Test AWS key redaction."""
        text = "AWS Access Key: AKIA1234567890ABCDEF"
        redacted, log = redaction_engine.redact_text(text)
        
        assert "[AWS_KEY_REDACTED]" in redacted
        assert "AKIA1234567890ABCDEF" not in redacted
        assert len(log) == 1
        assert log[0]["rule"] == "aws_key"
    
    def test_jwt_token_redaction(self):
        """Test JWT token redaction."""
        text = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        redacted, log = redaction_engine.redact_text(text)
        
        assert "[JWT_REDACTED]" in redacted
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted
        assert len(log) == 1
        assert log[0]["rule"] == "jwt"
    
    def test_multiple_redactions(self):
        """Test multiple redactions in one text."""
        text = "Email: john@example.com, Phone: (555) 123-4567, API Key: sk-1234567890abcdef"
        redacted, log = redaction_engine.redact_text(text)
        
        assert "[EMAIL_REDACTED]" in redacted
        assert "[PHONE_REDACTED]" in redacted
        assert "[API_KEY_REDACTED]" in redacted
        assert len(log) == 3
    
    def test_no_sensitive_data(self):
        """Test text with no sensitive data."""
        text = "This is a normal message without any sensitive information."
        redacted, log = redaction_engine.redact_text(text)
        
        assert redacted == text
        assert len(log) == 0
    
    def test_empty_text(self):
        """Test empty text redaction."""
        text = ""
        redacted, log = redaction_engine.redact_text(text)
        
        assert redacted == text
        assert len(log) == 0
    
    def test_data_hash_generation(self):
        """Test data hash generation."""
        text = "Test data for hashing"
        hash1 = redaction_engine.get_redaction_hash(text)
        hash2 = redaction_engine.get_redaction_hash(text)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length
        assert hash1 != redaction_engine.get_redaction_hash("Different text")


class TestRetentionPolicy:
    """Test retention policy functionality."""
    
    def test_retention_policy_names(self):
        """Test retention policy names."""
        assert retention_policy.get_retention_seconds("none") == 0
        assert retention_policy.get_retention_seconds("1h") == 3600
        assert retention_policy.get_retention_seconds("24h") == 86400
        assert retention_policy.get_retention_seconds("7d") == 604800
        assert retention_policy.get_retention_seconds("30d") == 2592000
    
    def test_retention_should_retain(self):
        """Test retention should_retain logic."""
        assert retention_policy.should_retain("none") is False
        assert retention_policy.should_retain("1h") is True
        assert retention_policy.should_retain("24h") is True
        assert retention_policy.should_retain("invalid") is False
    
    def test_retention_expiry_time(self):
        """Test retention expiry time calculation."""
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        
        # No retention
        expiry = retention_policy.get_expiry_time("none", now)
        assert expiry is None
        
        # 1 hour retention
        expiry = retention_policy.get_expiry_time("1h", now)
        assert expiry == now + timedelta(seconds=3600)
        
        # 24 hour retention
        expiry = retention_policy.get_expiry_time("24h", now)
        assert expiry == now + timedelta(seconds=86400)
    
    def test_retention_is_expired(self):
        """Test retention expiry checking."""
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        
        # No retention (always expired)
        assert retention_policy.is_expired("none", now) is True
        
        # Future expiry (not expired)
        future_time = now + timedelta(hours=1)
        assert retention_policy.is_expired("24h", future_time) is False
        
        # Past expiry (expired)
        past_time = now - timedelta(hours=25)
        assert retention_policy.is_expired("24h", past_time) is True
