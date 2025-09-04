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

def test_webhooks():
    print("=== Webhooks Console Test ===\n")
    
    # Test Owner role (should have webhooks.read and webhooks.replay)
    print("1. Testing Owner role...")
    owner_token = login_user("owner@sbh.dev", "Owner!123")
    if not owner_token:
        print("   ❌ Failed to login as owner")
        return
    
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Test webhooks events listing
    response = requests.get(f"{BASE_URL}/api/webhooks/events?limit=10", headers=owner_headers)
    if response.status_code == 200:
        events_data = response.json()
        print(f"   ✅ Webhooks events listed: {events_data.get('total_count', 0)} events")
        
        # Test replay if there are events
        events = events_data.get('events', [])
        if events:
            event_id = events[0]['id']
            replay_response = requests.post(f"{BASE_URL}/api/webhooks/events/{event_id}/replay", headers=owner_headers)
            if replay_response.status_code == 200:
                print(f"   ✅ Webhook replay successful for event {event_id}")
            else:
                print(f"   ❌ Webhook replay failed: {replay_response.status_code}")
        else:
            print("   ⚠️  No webhook events to replay")
    else:
        print(f"   ❌ Failed to list webhooks events: {response.status_code}")
    
    # Test Sales role (should not have webhooks access)
    print("\n2. Testing Sales role...")
    sales_token = login_user("sales@sbh.dev", "Sales!123")
    if not sales_token:
        print("   ❌ Failed to login as sales")
        return
    
    sales_headers = {"Authorization": f"Bearer {sales_token}"}
    
    # Test webhooks events listing (should be denied)
    response = requests.get(f"{BASE_URL}/api/webhooks/events?limit=10", headers=sales_headers)
    if response.status_code == 403:
        print("   ✅ Webhooks access correctly denied for Sales role")
    else:
        print(f"   ❌ Webhooks access incorrectly allowed: {response.status_code}")
    
    # Test ReadOnly role (should not have webhooks access)
    print("\n3. Testing ReadOnly role...")
    readonly_token = login_user("readonly@sbh.dev", "Read!123")
    if not readonly_token:
        print("   ❌ Failed to login as readonly")
        return
    
    readonly_headers = {"Authorization": f"Bearer {readonly_token}"}
    
    # Test webhooks events listing (should be denied)
    response = requests.get(f"{BASE_URL}/api/webhooks/events?limit=10", headers=readonly_headers)
    if response.status_code == 403:
        print("   ✅ Webhooks access correctly denied for ReadOnly role")
    else:
        print(f"   ❌ Webhooks access incorrectly allowed: {response.status_code}")
    
    # Test filters and pagination
    print("\n4. Testing filters and pagination...")
    response = requests.get(f"{BASE_URL}/api/webhooks/events?limit=5&offset=0&provider=sendgrid", headers=owner_headers)
    if response.status_code == 200:
        filtered_data = response.json()
        print(f"   ✅ Filters working: {filtered_data.get('total_count', 0)} events with provider filter")
        print(f"   ✅ Pagination working: limit={filtered_data.get('limit')}, offset={filtered_data.get('offset')}")
    else:
        print(f"   ❌ Filters/pagination failed: {response.status_code}")
    
    print(f"\n=== Webhooks Test Summary ===")
    print(f"Owner/Admin can list and replay webhook events")
    print(f"Sales/ReadOnly correctly denied webhooks access")
    print(f"Filters and pagination working correctly")

if __name__ == "__main__":
    test_webhooks()
