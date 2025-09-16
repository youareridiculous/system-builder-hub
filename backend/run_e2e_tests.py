#!/usr/bin/env python3
"""
Simple E2E Test Runner
"""
import os
import sys
import subprocess
import time

def setup_environment():
    """Set up test environment"""
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['LLM_SECRET_KEY'] = 'dGVzdC1rZXktZm9yLXRlc3Rpbmctc2VjcmV0cy0xMjM='
    os.environ['PYTHONPATH'] = '.'

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import pytest
        print("✅ pytest is available")
    except ImportError:
        print("❌ pytest not found. Install with: pip install pytest pytest-cov")
        return False
    
    try:
        import requests
        print("✅ requests is available")
    except ImportError:
        print("❌ requests not found. Install with: pip install requests")
        return False
    
    return True

def run_tests():
    """Run E2E tests"""
    print("🚀 Running E2E Core Build Loop Tests...")
    
    # Run pytest with E2E tests
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/e2e/',
        '-v',
        '--tb=short',
        '--timeout=300'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ All E2E tests passed!")
            return True
        else:
            print(f"❌ E2E tests failed with return code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality without pytest"""
    print("🧪 Testing basic functionality...")
    
    try:
        # Test imports
        sys.path.insert(0, 'src')
        from llm_core import LLMService
        print("✅ LLM core imports successfully")
        
        # Test secrets
        from secrets import encrypt_secret, decrypt_secret
        test_secret = "test-secret"
        encrypted = encrypt_secret(test_secret)
        decrypted = decrypt_secret(encrypted)
        assert decrypted == test_secret
        print("✅ Secrets encryption/decryption works")
        
        # Test LLM service
        service = LLMService('test_tenant')
        print("✅ LLM service created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def main():
    """Main test runner"""
    print("🔧 Setting up environment...")
    setup_environment()
    
    print("📋 Checking dependencies...")
    if not check_dependencies():
        print("⚠️ Running basic functionality test only...")
        return test_basic_functionality()
    
    print("🧪 Running comprehensive E2E tests...")
    return run_tests()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
