import requests
import json
from typing import Dict, Any, Optional
from config import Config

class SendGridProvider:
    """SendGrid email provider implementation"""
    
    def __init__(self):
        self.api_key = Config.SENDGRID_API_KEY
        self.from_email = Config.SENDGRID_FROM_EMAIL
        self.base_url = "https://api.sendgrid.com/v3"
        
    def send_email(self, to_email: str, subject: str, body: str, **kwargs) -> Dict[str, Any]:
        """Send email via SendGrid"""
        if not self.api_key:
            raise ValueError("SendGrid API key not configured")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "personalizations": [
                {
                    "to": [{"email": to_email}],
                    "subject": subject
                }
            ],
            "from": {"email": self.from_email},
            "content": [
                {
                    "type": "text/plain",
                    "value": body
                }
            ]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/mail/send",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 202:
                # SendGrid returns 202 for successful sends
                return {
                    "success": True,
                    "provider_message_id": response.headers.get("X-Message-Id"),
                    "status": "sent",
                    "provider_response": "Email queued for delivery"
                }
            else:
                return {
                    "success": False,
                    "status": "failed",
                    "provider_response": f"SendGrid error: {response.status_code} - {response.text}"
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "status": "failed",
                "provider_response": f"Network error: {str(e)}"
            }
    
    def get_status(self, message_id: str) -> Dict[str, Any]:
        """Get email delivery status (SendGrid doesn't provide real-time status via API)"""
        return {
            "status": "sent",  # Assume sent if we got a 202 response
            "provider_message_id": message_id
        }
