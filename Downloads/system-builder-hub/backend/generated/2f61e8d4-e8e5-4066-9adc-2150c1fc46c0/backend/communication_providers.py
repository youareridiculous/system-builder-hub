from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import json
import requests
from datetime import datetime

class CommunicationProvider(ABC):
    """Abstract base class for communication providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider_name = self.__class__.__name__.replace('Provider', '').lower()
    
    @abstractmethod
    async def send_email(self, to: str, subject: str, body: str, contact_id: int) -> Dict[str, Any]:
        """Send an email"""
        pass
    
    @abstractmethod
    async def initiate_call(self, phone_number: str, contact_id: int) -> Dict[str, Any]:
        """Initiate a phone call"""
        pass
    
    @abstractmethod
    async def send_sms(self, phone_number: str, message: str, contact_id: int) -> Dict[str, Any]:
        """Send an SMS"""
        pass
    
    @abstractmethod
    async def get_status(self, message_id: str) -> Dict[str, Any]:
        """Get status of a message/call"""
        pass

class TwilioProvider(CommunicationProvider):
    """Twilio implementation for phone/SMS"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.account_sid = config.get('account_sid')
        self.auth_token = config.get('auth_token')
        self.phone_number = config.get('phone_number')
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"
    
    async def send_email(self, to: str, subject: str, body: str, contact_id: int) -> Dict[str, Any]:
        # Twilio doesn't handle email, would need SendGrid integration
        raise NotImplementedError("Twilio doesn't support email directly")
    
    async def initiate_call(self, phone_number: str, contact_id: int) -> Dict[str, Any]:
        """Initiate a Twilio call"""
        url = f"{self.base_url}/Calls.json"
        data = {
            'To': phone_number,
            'From': self.phone_number,
            'Url': f"{self.config.get('webhook_url', '')}/twilio/voice",
            'StatusCallback': f"{self.config.get('webhook_url', '')}/twilio/status",
            'StatusCallbackEvent': ['initiated', 'ringing', 'answered', 'completed'],
            'StatusCallbackMethod': 'POST'
        }
        
        response = requests.post(url, data=data, auth=(self.account_sid, self.auth_token))
        result = response.json()
        
        return {
            'provider_message_id': result.get('sid'),
            'status': result.get('status'),
            'provider': 'twilio',
            'type': 'call'
        }
    
    async def send_sms(self, phone_number: str, message: str, contact_id: int) -> Dict[str, Any]:
        """Send SMS via Twilio"""
        url = f"{self.base_url}/Messages.json"
        data = {
            'To': phone_number,
            'From': self.phone_number,
            'Body': message,
            'StatusCallback': f"{self.config.get('webhook_url', '')}/twilio/sms-status"
        }
        
        response = requests.post(url, data=data, auth=(self.account_sid, self.auth_token))
        result = response.json()
        
        return {
            'provider_message_id': result.get('sid'),
            'status': result.get('status'),
            'provider': 'twilio',
            'type': 'sms'
        }
    
    async def get_status(self, message_id: str) -> Dict[str, Any]:
        """Get status of a Twilio message/call"""
        url = f"{self.base_url}/Messages/{message_id}.json"
        response = requests.get(url, auth=(self.account_sid, self.auth_token))
        result = response.json()
        
        return {
            'status': result.get('status'),
            'provider': 'twilio'
        }

class SendGridProvider(CommunicationProvider):
    """SendGrid implementation for email"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.from_email = config.get('from_email')
        self.base_url = "https://api.sendgrid.com/v3"
    
    async def send_email(self, to: str, subject: str, body: str, contact_id: int) -> Dict[str, Any]:
        """Send email via SendGrid"""
        url = f"{self.base_url}/mail/send"
        data = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": self.from_email},
            "subject": subject,
            "content": [{"type": "text/html", "value": body}]
        }
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, json=data, headers=headers)
        result = response.json()
        
        return {
            'provider_message_id': result.get('id'),
            'status': 'sent' if response.status_code == 202 else 'failed',
            'provider': 'sendgrid',
            'type': 'email'
        }
    
    async def initiate_call(self, phone_number: str, contact_id: int) -> Dict[str, Any]:
        # SendGrid doesn't handle phone calls
        raise NotImplementedError("SendGrid doesn't support phone calls")
    
    async def send_sms(self, phone_number: str, message: str, contact_id: int) -> Dict[str, Any]:
        # SendGrid doesn't handle SMS
        raise NotImplementedError("SendGrid doesn't support SMS")
    
    async def get_status(self, message_id: str) -> Dict[str, Any]:
        """Get status of a SendGrid email"""
        # SendGrid doesn't provide real-time status via API
        return {
            'status': 'sent',
            'provider': 'sendgrid'
        }

class ProviderFactory:
    """Factory for creating communication providers"""
    
    _providers = {
        'twilio': TwilioProvider,
        'sendgrid': SendGridProvider
    }
    
    @classmethod
    def create_provider(cls, provider_name: str, config: Dict[str, Any]) -> CommunicationProvider:
        """Create a provider instance"""
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        provider_class = cls._providers[provider_name]
        return provider_class(config)
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """Register a new provider"""
        cls._providers[name] = provider_class
