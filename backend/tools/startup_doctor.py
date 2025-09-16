#!/usr/bin/env python3
"""
Startup Doctor - Diagnostic tool for SBH startup issues
"""
import sys
import os
import importlib
import requests
import json
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def check_imports() -> Dict[str, Any]:
    """Check if core modules can be imported"""
    results = {}
    
    core_modules = [
        'config',
        'app',
        'ui_build',
        'ui_project_loader', 
        'ui_visual_builder',
        'ui_guided',
        'templates_catalog',
        'features_catalog'
    ]
    
    for module in core_modules:
        try:
            importlib.import_module(module)
            results[module] = {'status': 'OK', 'error': None}
        except Exception as e:
            results[module] = {'status': 'FAILED', 'error': str(e)}
    
    return results

def check_app_creation() -> Dict[str, Any]:
    """Check if Flask app can be created"""
    try:
        from app import create_app
        app = create_app()
        return {
            'status': 'OK',
            'error': None,
            'routes_count': len(list(app.url_map.iter_rules()))
        }
    except Exception as e:
        return {
            'status': 'FAILED',
            'error': str(e),
            'routes_count': 0
        }

def check_endpoints(base_url: str = 'http://localhost:5001') -> Dict[str, Any]:
    """Check if core endpoints respond"""
    results = {}
    
    core_endpoints = [
        '/healthz',
        '/dashboard',
        '/ui/build',
        '/ui/project-loader',
        '/ui/visual-builder',
        '/ui/preview'
    ]
    
    for endpoint in core_endpoints:
        try:
            response = requests.get(f'{base_url}{endpoint}', timeout=5)
            results[endpoint] = {
                'status': response.status_code,
                'error': None
            }
        except Exception as e:
            results[endpoint] = {
                'status': 'ERROR',
                'error': str(e)
            }
    
    return results

def print_summary_table(imports: Dict[str, Any], app_creation: Dict[str, Any], endpoints: Dict[str, Any]):
    """Print a formatted summary table"""
    print("=" * 80)
    print("SBH STARTUP DIAGNOSTICS")
    print("=" * 80)
    
    # Imports section
    print("\n📦 IMPORTS:")
    print("-" * 40)
    for module, result in imports.items():
        status_icon = "✅" if result['status'] == 'OK' else "❌"
        print(f"{status_icon} {module:<20} {result['status']}")
        if result['error']:
            print(f"    Error: {result['error']}")
    
    # App creation section
    print(f"\n🚀 APP CREATION:")
    print("-" * 40)
    status_icon = "✅" if app_creation['status'] == 'OK' else "❌"
    print(f"{status_icon} Flask App: {app_creation['status']}")
    if app_creation['error']:
        print(f"    Error: {app_creation['error']}")
    else:
        print(f"    Routes: {app_creation['routes_count']}")
    
    # Endpoints section
    print(f"\n🌐 ENDPOINTS:")
    print("-" * 40)
    for endpoint, result in endpoints.items():
        if result['status'] == 200:
            status_icon = "✅"
        elif result['status'] == 'ERROR':
            status_icon = "❌"
        else:
            status_icon = "⚠️"
        print(f"{status_icon} {endpoint:<25} {result['status']}")
        if result['error']:
            print(f"    Error: {result['error']}")
    
    # Overall status
    print(f"\n📊 OVERALL STATUS:")
    print("-" * 40)
    
    import_failures = sum(1 for r in imports.values() if r['status'] != 'OK')
    endpoint_failures = sum(1 for r in endpoints.values() if r['status'] != 200)
    
    if import_failures == 0 and app_creation['status'] == 'OK' and endpoint_failures == 0:
        print("✅ ALL SYSTEMS OPERATIONAL")
        return True
    else:
        print(f"❌ ISSUES DETECTED:")
        if import_failures > 0:
            print(f"   - {import_failures} import failures")
        if app_creation['status'] != 'OK':
            print(f"   - App creation failed")
        if endpoint_failures > 0:
            print(f"   - {endpoint_failures} endpoint failures")
        return False

def main():
    """Main diagnostic function"""
    print("🔍 Running SBH Startup Diagnostics...")
    
    # Check imports
    imports = check_imports()
    
    # Check app creation
    app_creation = check_app_creation()
    
    # Check endpoints (only if app creation succeeded)
    endpoints = {}
    if app_creation['status'] == 'OK':
        endpoints = check_endpoints()
    
    # Print summary
    success = print_summary_table(imports, app_creation, endpoints)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
