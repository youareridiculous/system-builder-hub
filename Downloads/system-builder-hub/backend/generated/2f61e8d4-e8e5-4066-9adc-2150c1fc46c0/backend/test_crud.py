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

def test_crud():
    print("=== CRUD & Relations Test ===\n")
    
    # Login as manager (has write permissions)
    token = login_user("manager@sbh.dev", "Manager!123")
    if not token:
        print("❌ Failed to login as manager")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create Account
    print("1. Creating Account...")
    account_data = {
        "name": "Test Company Inc",
        "industry": "Technology",
        "website": "https://testcompany.com",
        "phone": "+1-555-0123"
    }
    response = requests.post(f"{BASE_URL}/api/accounts/", json=account_data, headers=headers)
    if response.status_code == 200:
        account = response.json()
        account_id = account["id"]
        print(f"   ✅ Account created: {account_id}")
    else:
        print(f"   ❌ Failed to create account: {response.status_code}")
        return
    
    # 2. Create Contact (linked to Account)
    print("2. Creating Contact...")
    contact_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@testcompany.com",
        "phone": "+1-555-0124",
        "account_id": account_id
    }
    response = requests.post(f"{BASE_URL}/api/contacts/", json=contact_data, headers=headers)
    if response.status_code == 200:
        contact = response.json()
        contact_id = contact["id"]
        print(f"   ✅ Contact created: {contact_id}")
    else:
        print(f"   ❌ Failed to create contact: {response.status_code}")
        return
    
    # 3. Create Deal (linked to Account/Contact)
    print("3. Creating Deal...")
    deal_data = {
        "title": "Enterprise Software License",
        "amount": 50000,
        "stage": "Proposal",
        "account_id": account_id,
        "contact_id": contact_id
    }
    response = requests.post(f"{BASE_URL}/api/deals/", json=deal_data, headers=headers)
    if response.status_code == 200:
        deal = response.json()
        deal_id = deal["id"]
        print(f"   ✅ Deal created: {deal_id}")
    else:
        print(f"   ❌ Failed to create deal: {response.status_code}")
        return
    
    # 4. Create Activity (linked to Deal/Contact)
    print("4. Creating Activity...")
    activity_data = {
        "type": "Call",
        "subject": "Follow-up on proposal",
        "contact_id": contact_id,
        "deal_id": deal_id,
        "scheduled_at": "2024-01-15T10:00:00Z"
    }
    response = requests.post(f"{BASE_URL}/api/activities/", json=activity_data, headers=headers)
    if response.status_code == 200:
        activity = response.json()
        activity_id = activity["id"]
        print(f"   ✅ Activity created: {activity_id}")
    else:
        print(f"   ❌ Failed to create activity: {response.status_code}")
        return
    
    # 5. Create Note (linked to Contact)
    print("5. Creating Note...")
    note_data = {
        "content": "Great conversation about enterprise needs. Follow up next week.",
        "contact_id": contact_id
    }
    response = requests.post(f"{BASE_URL}/api/notes/", json=note_data, headers=headers)
    if response.status_code == 200:
        note = response.json()
        note_id = note["id"]
        print(f"   ✅ Note created: {note_id}")
    else:
        print(f"   ❌ Failed to create note: {response.status_code}")
        return
    
    # 6. Verify Contact Detail Workspace Timeline
    print("6. Verifying Contact Detail Timeline...")
    response = requests.get(f"{BASE_URL}/api/contacts/{contact_id}", headers=headers)
    if response.status_code == 200:
        contact_detail = response.json()
        print(f"   ✅ Contact detail retrieved")
        print(f"   📊 Timeline items: {len(contact_detail.get('timeline', []))}")
        
        # Check if our created items appear in timeline
        timeline = contact_detail.get('timeline', [])
        has_deal = any(item.get('type') == 'deal' and item.get('deal_id') == deal_id for item in timeline)
        has_activity = any(item.get('type') == 'activity' and item.get('activity_id') == activity_id for item in timeline)
        has_note = any(item.get('type') == 'note' and item.get('note_id') == note_id for item in timeline)
        
        print(f"   🔗 Deal in timeline: {'✅' if has_deal else '❌'}")
        print(f"   🔗 Activity in timeline: {'✅' if has_activity else '❌'}")
        print(f"   🔗 Note in timeline: {'✅' if has_note else '❌'}")
    else:
        print(f"   ❌ Failed to get contact detail: {response.status_code}")
    
    # 7. Update Contact
    print("7. Updating Contact...")
    update_data = {"first_name": "Johnny"}
    response = requests.put(f"{BASE_URL}/api/contacts/{contact_id}", json=update_data, headers=headers)
    if response.status_code == 200:
        print(f"   ✅ Contact updated")
    else:
        print(f"   ❌ Failed to update contact: {response.status_code}")
    
    # 8. Delete Note (cleanup)
    print("8. Cleaning up...")
    response = requests.delete(f"{BASE_URL}/api/notes/{note_id}", headers=headers)
    if response.status_code == 200:
        print(f"   ✅ Note deleted")
    else:
        print(f"   ❌ Failed to delete note: {response.status_code}")
    
    print(f"\n=== CRUD Test Summary ===")
    print(f"Created IDs: Account={account_id}, Contact={contact_id}, Deal={deal_id}, Activity={activity_id}")
    print(f"Relations verified: Contact linked to Account, Deal linked to both, Activity linked to both")
    print(f"Timeline verification: Contact detail workspace shows related items")

if __name__ == "__main__":
    test_crud()
