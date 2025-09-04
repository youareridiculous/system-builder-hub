import os
from typing import Optional

class Config:
    """Configuration for CRM Flagship application"""
    
    # Communication Provider Feature Flags
    COMM_PROVIDERS_EMAIL = os.getenv('COMM_PROVIDERS_EMAIL', 'mock')
    COMM_PROVIDERS_SMS = os.getenv('COMM_PROVIDERS_SMS', 'mock')
    COMM_PROVIDERS_VOICE = os.getenv('COMM_PROVIDERS_VOICE', 'mock')
    COMM_PROVIDERS_CALL_RECORD = os.getenv('COMM_PROVIDERS_CALL_RECORD', 'false').lower() == 'true'
    
    # SendGrid Configuration
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')
    SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@example.com')
    
    # Twilio Configuration
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER', '')
    
    # Webhook Configuration
    WEBHOOK_BASE_URL = os.getenv('WEBHOOK_BASE_URL', 'http://localhost:8000')
    
    @classmethod
    def is_provider_enabled(cls, provider_type: str) -> bool:
        """Check if a specific provider type is enabled"""
        if provider_type == 'email':
            return cls.COMM_PROVIDERS_EMAIL != 'mock'
        elif provider_type == 'sms':
            return cls.COMM_PROVIDERS_SMS != 'mock'
        elif provider_type == 'voice':
            return cls.COMM_PROVIDERS_VOICE != 'mock'
        return False
    
    @classmethod
    def get_provider_name(cls, provider_type: str) -> str:
        """Get the configured provider name for a type"""
        if provider_type == 'email':
            return cls.COMM_PROVIDERS_EMAIL
        elif provider_type == 'sms':
            return cls.COMM_PROVIDERS_SMS
        elif provider_type == 'voice':
            return cls.COMM_PROVIDERS_VOICE
        return 'mock'
    
    @classmethod
    def has_valid_credentials(cls, provider_type: str) -> bool:
        """Check if valid credentials are configured for a provider"""
        if provider_type == 'email' and cls.COMM_PROVIDERS_EMAIL == 'sendgrid':
            return bool(cls.SENDGRID_API_KEY and cls.SENDGRID_FROM_EMAIL)
        elif provider_type in ['sms', 'voice'] and cls.COMM_PROVIDERS_SMS == 'twilio':
            return bool(cls.TWILIO_ACCOUNT_SID and cls.TWILIO_AUTH_TOKEN and cls.TWILIO_FROM_NUMBER)
        return False
