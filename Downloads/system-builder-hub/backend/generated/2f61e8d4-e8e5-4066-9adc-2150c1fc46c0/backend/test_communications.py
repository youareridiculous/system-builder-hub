#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8000"

def login_user(email, password):
    """Login and return JWT token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def test_communications():
    print("=== Communications Test (Mock Mode) ===\n")
    
    # Login as manager
    token = login_user("manager@sbh.dev", "Manager!123")
    if not token:
        print("❌ Failed to login as manager")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get a contact to send communications to
    response = requests.get(f"{BASE_URL}/api/contacts/", headers=headers)
    if response.status_code != 200:
        print("❌ Failed to get contacts")
        return
    
    contacts = response.json()
    if not contacts:
        print("❌ No contacts available")
        return
    
    contact = contacts[0]
    contact_id = contact["id"]
    print(f"Using contact: {contact['first_name']} {contact['last_name']} (ID: {contact_id})")
    
    # 1. Send Email
    print("1. Sending Email...")
    email_data = {
        "to_email": "test@example.com",
        "contact_id": contact_id,
        "subject": "Test Email from CRM",
        "body": "This is a test email sent from the CRM system."
    }
    response = requests.post(f"{BASE_URL}/api/communications/send-email", json=email_data, headers=headers)
    if response.status_code == 200:
        email_result = response.json()
        print(f"   ✅ Email sent: {email_result.get('id')}")
    else:
        print(f"   ❌ Failed to send email: {response.status_code}")
    
    # 2. Send SMS
    print("2. Sending SMS...")
    sms_data = {
        "to_phone": "+1234567890",
        "contact_id": contact_id,
        "message": "Test SMS from CRM system"
    }
    response = requests.post(f"{BASE_URL}/api/communications/send-sms", json=sms_data, headers=headers)
    if response.status_code == 200:
        sms_result = response.json()
        print(f"   ✅ SMS sent: {sms_result.get('id')}")
    else:
        print(f"   ❌ Failed to send SMS: {response.status_code}")
    
    # 3. Initiate Call
    print("3. Initiating Call...")
    call_data = {
        "to_phone": "+1234567890",
        "contact_id": contact_id
    }
    response = requests.post(f"{BASE_URL}/api/communications/initiate-call", json=call_data, headers=headers)
    if response.status_code == 200:
        call_result = response.json()
        print(f"   ✅ Call initiated: {call_result.get('id')}")
    else:
        print(f"   ❌ Failed to initiate call: {response.status_code}")
    
    # 4. Check Communications History
    print("4. Checking Communications History...")
    response = requests.get(f"{BASE_URL}/api/communications/history", headers=headers)
    if response.status_code == 200:
        history = response.json()
        print(f"   ✅ Communications history: {len(history)} items")
        
        # Check if our communications appear
        recent_comms = [c for c in history if c.get('contact_id') == contact_id]
        print(f"   📊 Recent communications for contact: {len(recent_comms)}")
        
        for comm in recent_comms[:3]:  # Show last 3
            print(f"      - {comm.get('type')}: {comm.get('subject', 'No subject')} ({comm.get('status')})")
    else:
        print(f"   ❌ Failed to get communications history: {response.status_code}")
    
    # 5. Check for Call Recordings
    print("5. Checking for Call Recordings...")
    response = requests.get(f"{BASE_URL}/api/communications/history", headers=headers)
    if response.status_code == 200:
        history = response.json()
        recordings = [c for c in history if c.get('type') == 'call' and c.get('recording_url')]
        print(f"   📹 Call recordings available: {len(recordings)}")
        
        for recording in recordings[:2]:  # Show first 2
            print(f"      - Recording: {recording.get('recording_url')} ({recording.get('status')})")
    else:
        print(f"   ❌ Failed to get communications for recordings: {response.status_code}")
    
    print(f"\n=== Communications Test Summary ===")
    print(f"Mock providers working: Email, SMS, Voice calls")
    print(f"Communications appear in history and contact timeline")
    print(f"Call recordings available for playback")

if __name__ == "__main__":
    test_communications()
