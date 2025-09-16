#!/usr/bin/env python3
"""
Test script to verify SQLAlchemy session management fixes
"""
import requests
import json
import time

BASE_URL = "https://sbh.umbervale.com"

def test_phase3_apis():
    """Test Phase-3 APIs with proper session management"""
    headers = {
        "Content-Type": "application/json",
        "X-User-Email": "test@example.com",
        "X-Tenant": "demo"
    }
    
    print("🧪 Testing Phase-3 APIs with session management fixes...")
    
    # Test 1: Create conversation
    print("\n1. Creating conversation...")
    conv_data = {"title": "Test Session Fix Conversation"}
    response = requests.post(f"{BASE_URL}/api/memory/conversations", 
                           headers=headers, json=conv_data)
    
    if response.status_code == 200:
        conv_result = response.json()
        if conv_result.get('ok'):
            conversation_id = conv_result['data']['id']
            print(f"✅ Created conversation: {conversation_id}")
        else:
            print(f"❌ Failed to create conversation: {conv_result}")
            return False
    else:
        print(f"❌ HTTP {response.status_code}: {response.text}")
        return False
    
    # Test 2: List conversations
    print("\n2. Listing conversations...")
    response = requests.get(f"{BASE_URL}/api/memory/conversations?tenant=demo", 
                          headers=headers)
    
    if response.status_code == 200:
        list_result = response.json()
        if list_result.get('ok'):
            conversations = list_result['data']['conversations']
            print(f"✅ Found {len(conversations)} conversations")
        else:
            print(f"❌ Failed to list conversations: {list_result}")
            return False
    else:
        print(f"❌ HTTP {response.status_code}: {response.text}")
        return False
    
    # Test 3: Add message
    print("\n3. Adding message...")
    msg_data = {
        "role": "user",
        "content": "This is a test message to verify session management"
    }
    response = requests.post(f"{BASE_URL}/api/memory/conversations/{conversation_id}/messages",
                           headers=headers, json=msg_data)
    
    if response.status_code == 200:
        msg_result = response.json()
        if msg_result.get('ok'):
            message_id = msg_result['data']['id']
            print(f"✅ Added message: {message_id}")
        else:
            print(f"❌ Failed to add message: {msg_result}")
            return False
    else:
        print(f"❌ HTTP {response.status_code}: {response.text}")
        return False
    
    # Test 4: List messages
    print("\n4. Listing messages...")
    response = requests.get(f"{BASE_URL}/api/memory/conversations/{conversation_id}/messages",
                          headers=headers)
    
    if response.status_code == 200:
        msgs_result = response.json()
        if msgs_result.get('ok'):
            messages = msgs_result['data']['messages']
            print(f"✅ Found {len(messages)} messages")
        else:
            print(f"❌ Failed to list messages: {msgs_result}")
            return False
    else:
        print(f"❌ HTTP {response.status_code}: {response.text}")
        return False
    
    # Test 5: Create build spec
    print("\n5. Creating build spec...")
    spec_data = {
        "title": "Test Build Spec",
        "plan_manifest": {"type": "web_app", "framework": "react"},
        "repo_skeleton": {"files": ["package.json", "src/App.js"]},
        "status": "draft"
    }
    response = requests.post(f"{BASE_URL}/api/specs", headers=headers, json=spec_data)
    
    if response.status_code == 200:
        spec_result = response.json()
        if spec_result.get('ok'):
            spec_id = spec_result['data']['id']
            print(f"✅ Created build spec: {spec_id}")
        else:
            print(f"❌ Failed to create build spec: {spec_result}")
            return False
    else:
        print(f"❌ HTTP {response.status_code}: {response.text}")
        return False
    
    # Test 6: Health check
    print("\n6. Checking health...")
    response = requests.get(f"{BASE_URL}/api/health")
    
    if response.status_code == 200:
        health = response.json()
        if health.get('ok') and health.get('persistent_memory', {}).get('status') == 'healthy':
            print("✅ Health check passed - persistent memory healthy")
        else:
            print(f"❌ Health check failed: {health}")
            return False
    else:
        print(f"❌ HTTP {response.status_code}: {response.text}")
        return False
    
    print("\n🎉 All Phase-3 API tests passed! Session management is working correctly.")
    return True

if __name__ == "__main__":
    success = test_phase3_apis()
    exit(0 if success else 1)
