import requests
import json
from typing import Dict, Any, Optional
from config import Config

class TwilioProvider:
    """Twilio SMS and Voice provider implementation"""
    
    def __init__(self):
        self.account_sid = Config.TWILIO_ACCOUNT_SID
        self.auth_token = Config.TWILIO_AUTH_TOKEN
        self.from_number = Config.TWILIO_FROM_NUMBER
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"
        
    def send_sms(self, to_number: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send SMS via Twilio"""
        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise ValueError("Twilio credentials not configured")
            
        url = f"{self.base_url}/Messages.json"
        
        data = {
            "To": to_number,
            "From": self.from_number,
            "Body": message
        }
        
        try:
            response = requests.post(
                url,
                auth=(self.account_sid, self.auth_token),
                data=data,
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                return {
                    "success": True,
                    "provider_message_id": result.get("sid"),
                    "status": "sent",
                    "provider_response": "SMS sent successfully"
                }
            else:
                return {
                    "success": False,
                    "status": "failed",
                    "provider_response": f"Twilio error: {response.status_code} - {response.text}"
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "status": "failed",
                "provider_response": f"Network error: {str(e)}"
            }
    
    def initiate_call(self, to_number: str, **kwargs) -> Dict[str, Any]:
        """Initiate voice call via Twilio"""
        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise ValueError("Twilio credentials not configured")
            
        url = f"{self.base_url}/Calls.json"
        
        # Create TwiML for the call
        twiml = f"""
        <Response>
            <Say>Hello! This is a test call from your CRM system.</Say>
            <Pause length="2"/>
            <Say>Thank you for your time. Goodbye!</Say>
        </Response>
        """
        
        data = {
            "To": to_number,
            "From": self.from_number,
            "Twiml": twiml,
            "Record": "true" if Config.COMM_PROVIDERS_CALL_RECORD else "false"
        }
        
        try:
            response = requests.post(
                url,
                auth=(self.account_sid, self.auth_token),
                data=data,
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                return {
                    "success": True,
                    "provider_message_id": result.get("sid"),
                    "status": "initiated",
                    "provider_response": "Call initiated successfully"
                }
            else:
                return {
                    "success": False,
                    "status": "failed",
                    "provider_response": f"Twilio error: {response.status_code} - {response.text}"
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "status": "failed",
                "provider_response": f"Network error: {str(e)}"
            }
    
    def get_status(self, message_id: str) -> Dict[str, Any]:
        """Get SMS or call status"""
        if not all([self.account_sid, self.auth_token]):
            return {"status": "unknown", "provider_message_id": message_id}
            
        # Try to get SMS status first
        url = f"{self.base_url}/Messages/{message_id}.json"
        
        try:
            response = requests.get(
                url,
                auth=(self.account_sid, self.auth_token),
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "status": result.get("status", "unknown"),
                    "provider_message_id": message_id
                }
        except:
            pass
            
        # Try to get call status
        url = f"{self.base_url}/Calls/{message_id}.json"
        
        try:
            response = requests.get(
                url,
                auth=(self.account_sid, self.auth_token),
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "status": result.get("status", "unknown"),
                    "provider_message_id": message_id,
                    "duration": result.get("duration"),
                    "recording_url": result.get("recording_url")
                }
        except:
            pass
            
        return {"status": "unknown", "provider_message_id": message_id}
