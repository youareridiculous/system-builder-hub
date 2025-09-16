#!/usr/bin/env python3
"""
Test database migration and configuration
"""
import os
import sys

def test_database_config():
    """Test database configuration"""
    print("🧪 Testing Database Configuration")
    
    # Test development environment
    os.environ['ENV'] = 'development'
    try:
        from src.db_core import get_database_url, get_database_info
        dev_url = get_database_url()
        dev_info = get_database_info()
        print(f"✅ Development: {dev_url} ({dev_info['type']})")
    except Exception as e:
        print(f"❌ Development config failed: {e}")
        return False
    
    # Test production environment
    os.environ['ENV'] = 'production'
    os.environ['DATABASE_URL_PROD'] = 'postgresql+psycopg2://test:test@localhost:5432/test'
    try:
        prod_url = get_database_url()
        prod_info = get_database_info()
        print(f"✅ Production: {prod_url} ({prod_info['type']})")
    except Exception as e:
        print(f"❌ Production config failed: {e}")
        return False
    
    return True

def test_health_check():
    """Test health check with new database layer"""
    print("\n🧪 Testing Health Check")
    
    try:
        from src.health import check_db
        db_ok, migrations_applied, details = check_db('./instance/app.db')
        print(f"✅ Health check: db_ok={db_ok}, migrations={migrations_applied}, details={details}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_makefile():
    """Test makefile commands"""
    print("\n🧪 Testing Makefile")
    
    import subprocess
    try:
        result = subprocess.run(['make', 'help'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Makefile help command works")
            return True
        else:
            print(f"❌ Makefile failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Makefile test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Database Migration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Database Configuration", test_database_config),
        ("Health Check", test_health_check),
        ("Makefile", test_makefile),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
