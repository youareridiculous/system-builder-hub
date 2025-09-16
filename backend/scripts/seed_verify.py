#!/usr/bin/env python3
"""
Seed verification script for SBH CRM
Verifies that demo data seeding was successful by checking minimum entity counts.
"""

import sys
import os
import requests
import json
from typing import Dict, Any, Optional

def verify_seed_data(base_url: str, auth_token: str, tenant_id: str) -> bool:
    """
    Verify that demo seed data meets minimum requirements.
    
    Args:
        base_url: Base URL of the API
        auth_token: JWT authentication token
        tenant_id: Tenant ID to verify
        
    Returns:
        bool: True if all checks pass, False otherwise
    """
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "X-Tenant-ID": tenant_id,
        "Content-Type": "application/json"
    }
    
    print("🔍 Verifying demo seed data...")
    
    # Minimum required counts
    min_counts = {
        "contacts": 10,
        "deals": 5,
        "projects": 2,
        "tasks": 10,
        "messages": 3
    }
    
    all_passed = True
    
    # Check contacts count
    try:
        response = requests.get(f"{base_url}/api/contacts", headers=headers)
        if response.status_code == 200:
            contacts_data = response.json()
            contacts_count = len(contacts_data.get("data", []))
            print(f"  📇 Contacts: {contacts_count} (min: {min_counts['contacts']})")
            
            if contacts_count < min_counts["contacts"]:
                print(f"    ❌ FAILED: Expected at least {min_counts['contacts']} contacts")
                all_passed = False
            else:
                print(f"    ✅ PASSED")
        else:
            print(f"  📇 Contacts: ❌ FAILED to fetch (status: {response.status_code})")
            all_passed = False
    except Exception as e:
        print(f"  📇 Contacts: ❌ ERROR: {str(e)}")
        all_passed = False
    
    # Check deals count
    try:
        response = requests.get(f"{base_url}/api/deals", headers=headers)
        if response.status_code == 200:
            deals_data = response.json()
            deals_count = len(deals_data.get("data", []))
            print(f"  💼 Deals: {deals_count} (min: {min_counts['deals']})")
            
            if deals_count < min_counts["deals"]:
                print(f"    ❌ FAILED: Expected at least {min_counts['deals']} deals")
                all_passed = False
            else:
                print(f"    ✅ PASSED")
        else:
            print(f"  💼 Deals: ❌ FAILED to fetch (status: {response.status_code})")
            all_passed = False
    except Exception as e:
        print(f"  💼 Deals: ❌ ERROR: {str(e)}")
        all_passed = False
    
    # Check projects count
    try:
        response = requests.get(f"{base_url}/api/projects", headers=headers)
        if response.status_code == 200:
            projects_data = response.json()
            projects_count = len(projects_data.get("data", []))
            print(f"  📋 Projects: {projects_count} (min: {min_counts['projects']})")
            
            if projects_count < min_counts["projects"]:
                print(f"    ❌ FAILED: Expected at least {min_counts['projects']} projects")
                all_passed = False
            else:
                print(f"    ✅ PASSED")
        else:
            print(f"  📋 Projects: ❌ FAILED to fetch (status: {response.status_code})")
            all_passed = False
    except Exception as e:
        print(f"  📋 Projects: ❌ ERROR: {str(e)}")
        all_passed = False
    
    # Check tasks count
    try:
        response = requests.get(f"{base_url}/api/tasks", headers=headers)
        if response.status_code == 200:
            tasks_data = response.json()
            tasks_count = len(tasks_data.get("data", []))
            print(f"  ✅ Tasks: {tasks_count} (min: {min_counts['tasks']})")
            
            if tasks_count < min_counts["tasks"]:
                print(f"    ❌ FAILED: Expected at least {min_counts['tasks']} tasks")
                all_passed = False
            else:
                print(f"    ✅ PASSED")
        else:
            print(f"  ✅ Tasks: ❌ FAILED to fetch (status: {response.status_code})")
            all_passed = False
    except Exception as e:
        print(f"  ✅ Tasks: ❌ ERROR: {str(e)}")
        all_passed = False
    
    # Check messages count
    try:
        response = requests.get(f"{base_url}/api/messages/threads", headers=headers)
        if response.status_code == 200:
            threads_data = response.json()
            threads_count = len(threads_data.get("data", []))
            
            # Count total messages across all threads
            total_messages = 0
            for thread in threads_data.get("data", []):
                thread_id = thread["id"]
                messages_response = requests.get(f"{base_url}/api/messages/threads/{thread_id}/messages", headers=headers)
                if messages_response.status_code == 200:
                    messages_data = messages_response.json()
                    total_messages += len(messages_data.get("data", []))
            
            print(f"  💬 Messages: {total_messages} (min: {min_counts['messages']})")
            
            if total_messages < min_counts["messages"]:
                print(f"    ❌ FAILED: Expected at least {min_counts['messages']} messages")
                all_passed = False
            else:
                print(f"    ✅ PASSED")
        else:
            print(f"  💬 Messages: ❌ FAILED to fetch (status: {response.status_code})")
            all_passed = False
    except Exception as e:
        print(f"  💬 Messages: ❌ ERROR: {str(e)}")
        all_passed = False
    
    # Check data quality
    print("\n🔍 Checking data quality...")
    
    # Verify contacts have required fields
    try:
        response = requests.get(f"{base_url}/api/contacts", headers=headers)
        if response.status_code == 200:
            contacts_data = response.json()
            contacts = contacts_data.get("data", [])
            
            valid_contacts = 0
            for contact in contacts:
                attrs = contact.get("attributes", {})
                if attrs.get("first_name") and attrs.get("email"):
                    valid_contacts += 1
            
            print(f"  📇 Valid contacts: {valid_contacts}/{len(contacts)}")
            if valid_contacts < len(contacts) * 0.8:  # 80% should be valid
                print(f"    ⚠️  WARNING: Many contacts missing required fields")
        else:
            print(f"  📇 Data quality: ❌ FAILED to fetch contacts")
    except Exception as e:
        print(f"  📇 Data quality: ❌ ERROR: {str(e)}")
    
    # Verify deals have values
    try:
        response = requests.get(f"{base_url}/api/deals", headers=headers)
        if response.status_code == 200:
            deals_data = response.json()
            deals = deals_data.get("data", [])
            
            deals_with_values = 0
            total_value = 0
            for deal in deals:
                attrs = deal.get("attributes", {})
                if attrs.get("value", 0) > 0:
                    deals_with_values += 1
                    total_value += attrs.get("value", 0)
            
            print(f"  💼 Deals with values: {deals_with_values}/{len(deals)}")
            print(f"  💼 Total pipeline value: ${total_value:,}")
        else:
            print(f"  💼 Data quality: ❌ FAILED to fetch deals")
    except Exception as e:
        print(f"  💼 Data quality: ❌ ERROR: {str(e)}")
    
    return all_passed

def main():
    """Main function"""
    # Get configuration from environment or use defaults
    base_url = os.getenv("SBH_BASE_URL", "http://localhost:5000")
    auth_token = os.getenv("SBH_AUTH_TOKEN")
    tenant_id = os.getenv("SBH_TENANT_ID")
    
    if not auth_token:
        print("❌ Error: SBH_AUTH_TOKEN environment variable is required")
        print("   Set it to a valid JWT token for authentication")
        sys.exit(1)
    
    if not tenant_id:
        print("❌ Error: SBH_TENANT_ID environment variable is required")
        print("   Set it to the tenant ID to verify")
        sys.exit(1)
    
    print(f"🚀 SBH CRM Seed Verification")
    print(f"   Base URL: {base_url}")
    print(f"   Tenant ID: {tenant_id}")
    print()
    
    # Verify seed data
    success = verify_seed_data(base_url, auth_token, tenant_id)
    
    print()
    if success:
        print("✅ All seed verification checks PASSED!")
        print("   Demo data has been successfully seeded with minimum required entities.")
        sys.exit(0)
    else:
        print("❌ Some seed verification checks FAILED!")
        print("   Demo data may be incomplete or corrupted.")
        print("   Please re-run the demo seed process.")
        sys.exit(1)

if __name__ == "__main__":
    main()
