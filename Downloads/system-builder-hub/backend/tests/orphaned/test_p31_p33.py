#!/usr/bin/env python3
"""
Comprehensive Tests for P31-P33: Backup Framework, Billing, Ownership, and Access Hub
"""

import os
import json
import time
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import the modules to test
from backup_scheduler import backup_scheduler, BackupType, BackupTrigger
from snapshot_store import snapshot_store, StorageProvider
from backup_manifest import backup_manifest_manager, BackupStatus, BackupEventType
from backups import backup_framework
from billing import billing_manager, PlanType, SubscriptionStatus, InvoiceStatus
from ownership_registry import ownership_registry, BuyoutStatus, ExportStatus, LicenseType
from access_hub import access_hub, TileType, ActivityType

def test_endpoint(url, method='GET', data=None, headers=None):
    """Helper function to test endpoints"""
    import requests
    base_url = 'http://localhost:5000'
    
    try:
        if method == 'GET':
            response = requests.get(f"{base_url}{url}", headers=headers)
        elif method == 'POST':
            response = requests.post(f"{base_url}{url}", json=data, headers=headers)
        elif method == 'PUT':
            response = requests.put(f"{base_url}{url}", json=data, headers=headers)
        elif method == 'DELETE':
            response = requests.delete(f"{base_url}{url}", headers=headers)
        
        return {
            'status_code': response.status_code,
            'data': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            'headers': dict(response.headers)
        }
    except Exception as e:
        return {
            'status_code': 0,
            'data': str(e),
            'headers': {}
        }

def print_test_result(test_name, result, expected_status=200):
    """Helper function to print test results"""
    status = "✅ PASS" if result['status_code'] == expected_status else "❌ FAIL"
    print(f"{status} {test_name}")
    if result['status_code'] != expected_status:
        print(f"   Expected: {expected_status}, Got: {result['status_code']}")
        print(f"   Response: {result['data']}")

def test_p31_backup_framework():
    """Test P31: Auto-Backups & File Recovery Framework"""
    print("\n🧪 Testing P31: Auto-Backups & File Recovery Framework")
    
    # Test backup trigger
    result = test_endpoint('/api/backup/trigger', method='POST', data={
        'backup_type': 'full',
        'name': 'Test Backup',
        'description': 'Test backup for P31'
    })
    print_test_result("Backup Trigger", result, 201)
    
    if result['status_code'] == 201:
        backup_id = result['data'].get('id')
        
        # Test backup list
        result = test_endpoint('/api/backup/list')
        print_test_result("Backup List", result)
        
        # Test backup manifest
        result = test_endpoint(f'/api/backup/manifest/{backup_id}')
        print_test_result("Backup Manifest", result)
        
        # Test backup verify
        result = test_endpoint(f'/api/backup/verify/{backup_id}', method='POST')
        print_test_result("Backup Verify", result)
        
        # Test backup restore
        result = test_endpoint('/api/backup/restore', method='POST', data={
            'backup_id': backup_id,
            'restore_type': 'full'
        })
        print_test_result("Backup Restore", result, 202)
        
        # Test retention policy
        result = test_endpoint('/api/backup/retention/set', method='POST', data={
            'name': 'Test Policy',
            'retention_days': 30,
            'max_backups': 10
        })
        print_test_result("Retention Policy", result, 201)
        
        # Test backup purge
        result = test_endpoint(f'/api/backup/purge/{backup_id}', method='DELETE')
        print_test_result("Backup Purge", result)

def test_p32_billing_ownership():
    """Test P32: Ownership, Subscription & Buyout Model"""
    print("\n🧪 Testing P32: Ownership, Subscription & Buyout Model")
    
    # Test billing usage
    result = test_endpoint('/api/billing/usage')
    print_test_result("Billing Usage", result)
    
    # Test billing quote
    result = test_endpoint('/api/billing/quote', method='POST', data={
        'plan_type': 'pro',
        'billing_cycle': 'monthly'
    })
    print_test_result("Billing Quote", result, 200)
    
    # Test billing checkout
    result = test_endpoint('/api/billing/checkout', method='POST', data={
        'plan_id': 'test_plan',
        'payment_method': 'card'
    })
    print_test_result("Billing Checkout", result, 201)
    
    # Test billing webhook
    result = test_endpoint('/api/billing/webhook', method='POST', data={
        'type': 'invoice.payment_succeeded',
        'data': {'object': {'id': 'test_invoice'}}
    })
    print_test_result("Billing Webhook", result, 200)
    
    # Test invoices
    result = test_endpoint('/api/billing/invoices')
    print_test_result("Billing Invoices", result)
    
    # Test license status
    result = test_endpoint('/api/license/status')
    print_test_result("License Status", result)
    
    # Test license rotate
    result = test_endpoint('/api/license/rotate', method='POST')
    print_test_result("License Rotate", result, 201)
    
    # Test ownership buyout quote
    result = test_endpoint('/api/ownership/buyout/quote', method='POST', data={
        'system_id': 'test_system',
        'buyout_type': 'full'
    })
    print_test_result("Buyout Quote", result, 200)
    
    # Test ownership buyout execute
    result = test_endpoint('/api/ownership/buyout/execute', method='POST', data={
        'buyout_id': 'test_buyout',
        'payment_method': 'card'
    })
    print_test_result("Buyout Execute", result, 201)
    
    # Test export create
    result = test_endpoint('/api/export/create', method='POST', data={
        'system_id': 'test_system',
        'export_type': 'full'
    })
    print_test_result("Export Create", result, 201)
    
    if result['status_code'] == 201:
        export_id = result['data'].get('id')
        
        # Test export status
        result = test_endpoint(f'/api/export/status/{export_id}')
        print_test_result("Export Status", result)
        
        # Test export download
        result = test_endpoint(f'/api/export/download/{export_id}')
        print_test_result("Export Download", result)
    
    # Test entitlements
    result = test_endpoint('/api/entitlements')
    print_test_result("Entitlements", result)

def test_p33_access_hub():
    """Test P33: System Access Hub"""
    print("\n🧪 Testing P33: System Access Hub")
    
    # Test hub tiles
    result = test_endpoint('/api/hub/tiles')
    print_test_result("Hub Tiles", result)
    
    # Test create tile
    result = test_endpoint('/api/hub/tile', method='POST', data={
        'name': 'Test Tile',
        'description': 'Test tile for P33',
        'tile_type': 'system',
        'url': '/test',
        'icon': 'test-icon',
        'color': '#007bff'
    })
    print_test_result("Create Tile", result, 201)
    
    if result['status_code'] == 201:
        tile_id = result['data'].get('id')
        
        # Test share tile
        result = test_endpoint(f'/api/hub/tile/{tile_id}/share', method='POST', data={
            'expires_hours': 72,
            'max_uses': 10
        })
        print_test_result("Share Tile", result, 201)
        
        # Test favorite tile
        result = test_endpoint(f'/api/hub/tile/{tile_id}/favorite', method='POST')
        print_test_result("Favorite Tile", result, 201)
        
        # Test unfavorite tile
        result = test_endpoint(f'/api/hub/tile/{tile_id}/favorite', method='DELETE')
        print_test_result("Unfavorite Tile", result)
    
    # Test hub activity
    result = test_endpoint('/api/hub/activity')
    print_test_result("Hub Activity", result)
    
    # Test branding settings
    result = test_endpoint('/api/branding/settings')
    print_test_result("Branding Settings", result)
    
    # Test branding theme
    result = test_endpoint('/api/branding/theme', method='POST', data={
        'theme': 'dark',
        'primary_color': '#007bff',
        'secondary_color': '#6c757d'
    })
    print_test_result("Branding Theme", result, 201)
    
    # Test branding domain verify
    result = test_endpoint('/api/branding/domain/verify', method='POST', data={
        'domain': 'test.example.com'
    })
    print_test_result("Branding Domain Verify", result, 200)
    
    # Test create API token
    result = test_endpoint('/api/tokens/create', method='POST', data={
        'name': 'Test Token',
        'permissions': ['read', 'write'],
        'expires_days': 365
    })
    print_test_result("Create API Token", result, 201)
    
    # Test list API tokens
    result = test_endpoint('/api/tokens/list')
    print_test_result("List API Tokens", result)
    
    # Test revoke API token
    if result['status_code'] == 200 and result['data']:
        token_id = result['data'][0].get('id')
        result = test_endpoint(f'/api/tokens/revoke/{token_id}', method='POST')
        print_test_result("Revoke API Token", result)

def test_cross_cutting_features():
    """Test cross-cutting features"""
    print("\n🧪 Testing Cross-Cutting Features")
    
    # Test feature flags
    result = test_endpoint('/api/feature-flags')
    print_test_result("Feature Flags", result)
    
    # Test feature flag audit
    result = test_endpoint('/api/feature-flags/audit')
    print_test_result("Feature Flag Audit", result)
    
    # Test idempotency status
    result = test_endpoint('/api/idempotency/status')
    print_test_result("Idempotency Status", result)
    
    # Test streaming status
    result = test_endpoint('/api/streaming/status')
    print_test_result("Streaming Status", result)
    
    # Test streaming cleanup
    result = test_endpoint('/api/streaming/cleanup', method='POST')
    print_test_result("Streaming Cleanup", result)
    
    # Test OpenAPI documentation
    result = test_endpoint('/openapi.json')
    print_test_result("OpenAPI JSON", result)
    
    # Test Swagger UI
    result = test_endpoint('/docs')
    print_test_result("Swagger UI", result)
    
    # Test metrics
    result = test_endpoint('/metrics')
    print_test_result("Prometheus Metrics", result)

def test_unit_backup_framework():
    """Unit tests for backup framework"""
    print("\n🧪 Unit Testing Backup Framework")
    
    # Test backup scheduler
    try:
        # Create a test schedule
        schedule = backup_scheduler.create_schedule(
            name="Test Schedule",
            backup_type=BackupType.FULL,
            frequency_hours=24,
            retention_days=7
        )
        print("✅ Backup Schedule Creation")
        
        # Test manual trigger
        trigger = backup_scheduler.trigger_manual_backup(
            backup_type=BackupType.FULL,
            metadata={'test': True}
        )
        print("✅ Manual Backup Trigger")
        
        # Test system event trigger
        trigger = backup_scheduler.trigger_system_event_backup(
            event_type="test_event",
            backup_type=BackupType.INCREMENTAL,
            metadata={'event': 'test'}
        )
        print("✅ System Event Backup Trigger")
        
    except Exception as e:
        print(f"❌ Backup Scheduler Test Failed: {e}")

def test_unit_snapshot_store():
    """Unit tests for snapshot store"""
    print("\n🧪 Unit Testing Snapshot Store")
    
    try:
        # Test snapshot creation
        test_data = b"Test backup data"
        metadata = snapshot_store.create_snapshot(
            name="Test Snapshot",
            data=test_data,
            tags={'test': 'true'}
        )
        print("✅ Snapshot Creation")
        
        if metadata:
            # Test snapshot retrieval
            retrieved_data = snapshot_store.retrieve_snapshot(metadata.id)
            if retrieved_data == test_data:
                print("✅ Snapshot Retrieval")
            else:
                print("❌ Snapshot Retrieval Failed")
            
            # Test snapshot verification
            if snapshot_store.verify_snapshot(metadata.id):
                print("✅ Snapshot Verification")
            else:
                print("❌ Snapshot Verification Failed")
            
            # Test snapshot deletion
            if snapshot_store.delete_snapshot(metadata.id):
                print("✅ Snapshot Deletion")
            else:
                print("❌ Snapshot Deletion Failed")
        
    except Exception as e:
        print(f"❌ Snapshot Store Test Failed: {e}")

def test_unit_billing():
    """Unit tests for billing system"""
    print("\n🧪 Unit Testing Billing System")
    
    try:
        # Test plan creation
        plan = billing_manager.create_plan(
            name="Test Plan",
            type=PlanType.BASIC,
            price_monthly=29.0,
            price_yearly=290.0,
            currency="USD",
            features={'test': True},
            limits={'exports_per_month': 50}
        )
        print("✅ Plan Creation")
        
        # Test subscription creation
        subscription = billing_manager.create_subscription(
            user_id="test_user",
            tenant_id="test_tenant",
            plan_id=plan.id,
            trial_days=7
        )
        print("✅ Subscription Creation")
        
        # Test usage increment
        if billing_manager.increment_usage("test_user", "test_tenant", "exports_per_month", 1):
            print("✅ Usage Increment")
        else:
            print("❌ Usage Increment Failed")
        
        # Test usage retrieval
        usage = billing_manager.get_usage("test_user", "test_tenant")
        if usage:
            print("✅ Usage Retrieval")
        else:
            print("❌ Usage Retrieval Failed")
        
    except Exception as e:
        print(f"❌ Billing System Test Failed: {e}")

def test_unit_ownership():
    """Unit tests for ownership registry"""
    print("\n🧪 Unit Testing Ownership Registry")
    
    try:
        # Test buyout request creation
        buyout = ownership_registry.create_buyout_request(
            user_id="test_user",
            tenant_id="test_tenant",
            system_id="test_system",
            buyout_type="full",
            amount=999.99,
            currency="USD",
            description="Test buyout"
        )
        print("✅ Buyout Request Creation")
        
        # Test license creation
        license_obj = ownership_registry.create_license(
            user_id="test_user",
            tenant_id="test_tenant",
            license_type=LicenseType.STANDARD,
            features={'test': True},
            valid_days=365,
            max_users=5
        )
        print("✅ License Creation")
        
        # Test license validation
        if ownership_registry.validate_license(license_obj.license_key):
            print("✅ License Validation")
        else:
            print("❌ License Validation Failed")
        
        # Test export creation
        export = ownership_registry.create_export(
            user_id="test_user",
            tenant_id="test_tenant",
            system_id="test_system",
            export_type="full",
            metadata={'test': True}
        )
        print("✅ Export Creation")
        
        # Test entitlement creation
        entitlement = ownership_registry.create_entitlement(
            user_id="test_user",
            tenant_id="test_tenant",
            feature="test_feature",
            limits={'max_uses': 100},
            valid_days=365
        )
        print("✅ Entitlement Creation")
        
    except Exception as e:
        print(f"❌ Ownership Registry Test Failed: {e}")

def test_unit_access_hub():
    """Unit tests for access hub"""
    print("\n🧪 Unit Testing Access Hub")
    
    try:
        # Test tile creation
        tile = access_hub.create_tile(
            name="Test Tile",
            description="Test tile for unit testing",
            tile_type=TileType.SYSTEM,
            url="/test",
            icon="test-icon",
            color="#007bff"
        )
        print("✅ Tile Creation")
        
        # Test tile retrieval
        retrieved_tile = access_hub.get_tile(tile.id)
        if retrieved_tile and retrieved_tile.id == tile.id:
            print("✅ Tile Retrieval")
        else:
            print("❌ Tile Retrieval Failed")
        
        # Test favorite addition
        if access_hub.add_favorite(tile.id):
            print("✅ Favorite Addition")
        else:
            print("❌ Favorite Addition Failed")
        
        # Test API token creation
        token_data = access_hub.create_api_token(
            name="Test Token",
            permissions=['read', 'write'],
            expires_days=365
        )
        if token_data:
            print("✅ API Token Creation")
            
            # Test API token validation
            token_obj = access_hub.validate_api_token(token_data['token'])
            if token_obj:
                print("✅ API Token Validation")
            else:
                print("❌ API Token Validation Failed")
        else:
            print("❌ API Token Creation Failed")
        
        # Test share link creation
        share_data = access_hub.create_share_link(
            tile_id=tile.id,
            expires_hours=72,
            max_uses=10
        )
        if share_data:
            print("✅ Share Link Creation")
            
            # Test share link validation
            share_info = access_hub.validate_share_link(share_data['share_token'])
            if share_info:
                print("✅ Share Link Validation")
            else:
                print("❌ Share Link Validation Failed")
        else:
            print("❌ Share Link Creation Failed")
        
        # Test activity event creation
        event = access_hub.create_activity_event(
            user_id="test_user",
            tenant_id="test_tenant",
            activity_type=ActivityType.TILE_CREATED,
            target_id=tile.id,
            target_type="tile",
            description="Test activity event"
        )
        print("✅ Activity Event Creation")
        
        # Test branding settings update
        if access_hub.update_branding_settings(
            tenant_id="test_tenant",
            theme="dark",
            primary_color="#007bff",
            secondary_color="#6c757d"
        ):
            print("✅ Branding Settings Update")
        else:
            print("❌ Branding Settings Update Failed")
        
    except Exception as e:
        print(f"❌ Access Hub Test Failed: {e}")

def main():
    """Main test runner"""
    print("🚀 Starting P31-P33 Comprehensive Tests")
    print("=" * 50)
    
    # Run unit tests first
    test_unit_backup_framework()
    test_unit_snapshot_store()
    test_unit_billing()
    test_unit_ownership()
    test_unit_access_hub()
    
    # Run integration tests
    test_p31_backup_framework()
    test_p32_billing_ownership()
    test_p33_access_hub()
    test_cross_cutting_features()
    
    print("\n" + "=" * 50)
    print("🎉 P31-P33 Tests Completed!")

if __name__ == "__main__":
    main()
