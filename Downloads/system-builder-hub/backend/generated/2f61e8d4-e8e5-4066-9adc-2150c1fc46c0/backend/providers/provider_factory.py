from typing import Dict, Any, Optional
from config import Config

class MockProvider:
    """Mock provider for testing and development"""
    
    def send_email(self, to_email: str, subject: str, body: str, **kwargs) -> Dict[str, Any]:
        """Mock email sending"""
        return {
            "success": True,
            "provider_message_id": f"mock_email_{hash(to_email + subject)}",
            "status": "sent",
            "provider_response": "Email sent (simulated)"
        }
    
    def send_sms(self, to_number: str, message: str, **kwargs) -> Dict[str, Any]:
        """Mock SMS sending"""
        return {
            "success": True,
            "provider_message_id": f"mock_sms_{hash(to_number + message)}",
            "status": "sent",
            "provider_response": "SMS sent (simulated)"
        }
    
    def initiate_call(self, to_number: str, **kwargs) -> Dict[str, Any]:
        """Mock call initiation"""
        return {
            "success": True,
            "provider_message_id": f"mock_call_{hash(to_number)}",
            "status": "initiated",
            "provider_response": "Call initiated (simulated)"
        }
    
    def get_status(self, message_id: str) -> Dict[str, Any]:
        """Mock status check"""
        return {
            "status": "delivered",
            "provider_message_id": message_id
        }

class ProviderFactory:
    """Factory for creating communication providers"""
    
    _mock_provider = MockProvider()
    _sendgrid_provider = None
    _twilio_provider = None
    
    @classmethod
    def get_email_provider(cls):
        """Get email provider based on configuration"""
        if Config.is_provider_enabled('email') and Config.has_valid_credentials('email'):
            if Config.COMM_PROVIDERS_EMAIL == 'sendgrid':
                if cls._sendgrid_provider is None:
                    from .sendgrid_provider import SendGridProvider
                    cls._sendgrid_provider = SendGridProvider()
                return cls._sendgrid_provider
        return cls._mock_provider
    
    @classmethod
    def get_sms_provider(cls):
        """Get SMS provider based on configuration"""
        if Config.is_provider_enabled('sms') and Config.has_valid_credentials('sms'):
            if Config.COMM_PROVIDERS_SMS == 'twilio':
                if cls._twilio_provider is None:
                    from .twilio_provider import TwilioProvider
                    cls._twilio_provider = TwilioProvider()
                return cls._twilio_provider
        return cls._mock_provider
    
    @classmethod
    def get_voice_provider(cls):
        """Get voice provider based on configuration"""
        if Config.is_provider_enabled('voice') and Config.has_valid_credentials('voice'):
            if Config.COMM_PROVIDERS_VOICE == 'twilio':
                if cls._twilio_provider is None:
                    from .twilio_provider import TwilioProvider
                    cls._twilio_provider = TwilioProvider()
                return cls._twilio_provider
        return cls._mock_provider
    
    @classmethod
    def get_provider_status(cls) -> Dict[str, str]:
        """Get status of all providers"""
        return {
            "email": Config.get_provider_name('email'),
            "sms": Config.get_provider_name('sms'),
            "voice": Config.get_provider_name('voice'),
            "call_recording": "enabled" if Config.COMM_PROVIDERS_CALL_RECORD else "disabled"
        }
