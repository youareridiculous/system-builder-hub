"""
Data Retention & Redaction Controls
Provides deterministic masking for PII/Secrets and retention policies.
"""

import re
import hashlib
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RedactionRule:
    """Redaction rule configuration."""
    name: str
    pattern: str
    replacement: str
    description: str
    severity: str  # low, medium, high, critical


class RedactionEngine:
    """Engine for redacting sensitive data."""
    
    def __init__(self):
        self.rules = self._initialize_rules()
    
    def _initialize_rules(self) -> List[RedactionRule]:
        """Initialize redaction rules."""
        return [
            # Email addresses
            RedactionRule(
                name="email",
                pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                replacement="[EMAIL_REDACTED]",
                description="Email address redaction",
                severity="high"
            ),
            # Phone numbers (US and international)
            RedactionRule(
                name="phone",
                pattern=r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
                replacement="[PHONE_REDACTED]",
                description="Phone number redaction",
                severity="high"
            ),
            # Credit card numbers
            RedactionRule(
                name="credit_card",
                pattern=r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
                replacement="[CC_REDACTED]",
                description="Credit card number redaction",
                severity="critical"
            ),
            # API keys (common patterns)
            RedactionRule(
                name="api_key",
                pattern=r'\b(sk-[a-zA-Z0-9]{20,}|pk_[a-zA-Z0-9]{20,}|[a-zA-Z0-9]{32,})\b',
                replacement="[API_KEY_REDACTED]",
                description="API key redaction",
                severity="critical"
            ),
            # Access tokens
            RedactionRule(
                name="access_token",
                pattern=r'\b(ya29\.[a-zA-Z0-9_-]+|ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|ghu_[a-zA-Z0-9]{36}|ghs_[a-zA-Z0-9]{36}|ghr_[a-zA-Z0-9]{36})\b',
                replacement="[TOKEN_REDACTED]",
                description="Access token redaction",
                severity="critical"
            ),
            # AWS access keys
            RedactionRule(
                name="aws_key",
                pattern=r'\b(AKIA[0-9A-Z]{16}|aws_access_key_id\s*[:=]\s*[A-Z0-9]{20})\b',
                replacement="[AWS_KEY_REDACTED]",
                description="AWS access key redaction",
                severity="critical"
            ),
            # AWS secret keys
            RedactionRule(
                name="aws_secret",
                pattern=r'\b(aws_secret_access_key\s*[:=]\s*[A-Za-z0-9/+=]{40})\b',
                replacement="[AWS_SECRET_REDACTED]",
                description="AWS secret key redaction",
                severity="critical"
            ),
            # Database connection strings
            RedactionRule(
                name="db_connection",
                pattern=r'(postgresql|mysql|mongodb)://[^:\s]+:[^@\s]+@[^/\s]+/[^\s]+',
                replacement="[DB_CONNECTION_REDACTED]",
                description="Database connection string redaction",
                severity="high"
            ),
            # SSH private keys
            RedactionRule(
                name="ssh_key",
                pattern=r'-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY-----',
                replacement="[SSH_KEY_REDACTED]",
                description="SSH private key redaction",
                severity="critical"
            ),
            # Social Security Numbers (US)
            RedactionRule(
                name="ssn",
                pattern=r'\b\d{3}-\d{2}-\d{4}\b',
                replacement="[SSN_REDACTED]",
                description="Social Security Number redaction",
                severity="critical"
            ),
            # IP addresses (optional, can be configured)
            RedactionRule(
                name="ip_address",
                pattern=r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
                replacement="[IP_REDACTED]",
                description="IP address redaction",
                severity="medium"
            ),
            # Passwords in config files
            RedactionRule(
                name="password",
                pattern=r'(password|passwd|pwd)\s*[:=]\s*[^\s\n]+',
                replacement="[PASSWORD_REDACTED]",
                description="Password redaction",
                severity="high"
            ),
            # JWT tokens
            RedactionRule(
                name="jwt",
                pattern=r'\b(eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*)\b',
                replacement="[JWT_REDACTED]",
                description="JWT token redaction",
                severity="high"
            ),
            # OAuth tokens
            RedactionRule(
                name="oauth_token",
                pattern=r'(access_token|refresh_token|token)\s*[:=]\s*[a-zA-Z0-9._-]+',
                replacement="[OAUTH_TOKEN_REDACTED]",
                description="OAuth token redaction",
                severity="high"
            ),
        ]
    
    def redact_text(self, text: str, enabled_rules: Optional[Set[str]] = None) -> Tuple[str, List[Dict]]:
        """
        Redact sensitive information from text.
        
        Args:
            text: Text to redact
            enabled_rules: Set of rule names to apply (None for all)
            
        Returns:
            Tuple of (redacted_text, redaction_log)
        """
        if not text:
            return text, []
        
        redacted_text = text
        redaction_log = []
        
        for rule in self.rules:
            if enabled_rules and rule.name not in enabled_rules:
                continue
            
            # Find all matches
            matches = list(re.finditer(rule.pattern, redacted_text, re.IGNORECASE))
            
            if matches:
                # Replace matches (in reverse order to maintain indices)
                for match in reversed(matches):
                    original = match.group(0)
                    redacted_text = (
                        redacted_text[:match.start()] + 
                        rule.replacement + 
                        redacted_text[match.end():]
                    )
                    
                    redaction_log.append({
                        "rule": rule.name,
                        "severity": rule.severity,
                        "description": rule.description,
                        "original_length": len(original),
                        "replacement": rule.replacement,
                        "position": match.start()
                    })
        
        return redacted_text, redaction_log
    
    def get_redaction_hash(self, text: str) -> str:
        """Generate a hash of text for retention tracking."""
        if not text:
            return ""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def should_retain_content(self, retention_seconds: int) -> bool:
        """Check if content should be retained based on retention policy."""
        return retention_seconds > 0


class RetentionPolicy:
    """Manages data retention policies."""
    
    def __init__(self):
        self.policies = {
            "none": 0,
            "1h": 3600,
            "24h": 86400,
            "7d": 604800,
            "30d": 2592000
        }
    
    def get_retention_seconds(self, policy_name: str) -> int:
        """Get retention seconds for a policy name."""
        return self.policies.get(policy_name, 0)
    
    def should_retain(self, policy_name: str) -> bool:
        """Check if data should be retained for a policy."""
        return self.get_retention_seconds(policy_name) > 0
    
    def get_expiry_time(self, policy_name: str, created_at: datetime) -> Optional[datetime]:
        """Get expiry time for data with a given policy."""
        retention_seconds = self.get_retention_seconds(policy_name)
        if retention_seconds == 0:
            return None
        return created_at + timedelta(seconds=retention_seconds)
    
    def is_expired(self, policy_name: str, created_at: datetime) -> bool:
        """Check if data is expired based on policy."""
        expiry_time = self.get_expiry_time(policy_name, created_at)
        if expiry_time is None:
            return True  # No retention means "expired"
        return datetime.utcnow() > expiry_time


# Global instances
redaction_engine = RedactionEngine()
retention_policy = RetentionPolicy()
