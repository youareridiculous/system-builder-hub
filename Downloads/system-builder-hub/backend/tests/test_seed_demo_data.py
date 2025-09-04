#!/usr/bin/env python3
"""
Test demo data seeding functionality
"""

import sys
import os
import subprocess
import sqlite3
import tempfile
import shutil
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def test_seed_demo_data():
    """Test that seed-db command creates demo data correctly"""
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        temp_backend = Path(temp_dir) / 'backend'
        temp_backend.mkdir()
        
        try:
            # Copy necessary files to temp directory
            backend_path = Path(__file__).parent.parent
            shutil.copytree(backend_path / 'src', temp_backend / 'src')
            shutil.copy(backend_path / 'alembic.ini', temp_backend / 'alembic.ini')
            shutil.copytree(backend_path / 'alembic', temp_backend / 'alembic')
            
            # Change to temp directory
            os.chdir(temp_backend)
            
            # Set environment variables
            os.environ['DATABASE_URL'] = 'sqlite:///./test_system_builder_hub.db'
            
            # Test 1: Run init-db
            print("🧪 Testing init-db command...")
            result = subprocess.run([
                sys.executable, '-m', 'src.cli', 'init-db'
            ], capture_output=True, text=True, cwd=temp_backend)
            
            if result.returncode != 0:
                print(f"❌ init-db failed: {result.stderr}")
                return False
            
            print("✅ init-db completed successfully")
            
            # Test 2: Run seed-db
            print("🧪 Testing seed-db command...")
            result = subprocess.run([
                sys.executable, '-m', 'src.cli', 'seed-db'
            ], capture_output=True, text=True, cwd=temp_backend)
            
            if result.returncode != 0:
                print(f"❌ seed-db failed: {result.stderr}")
                return False
            
            print("✅ seed-db completed successfully")
            
            # Test 3: Verify demo data was created
            print("🧪 Verifying demo data in database...")
            db_file = temp_backend / 'test_system_builder_hub.db'
            
            if not db_file.exists():
                print("❌ Database file not found")
                return False
            
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            # Check admin user exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE email = 'admin@demo.com'")
            user_count = cursor.fetchone()[0]
            if user_count == 0:
                print("❌ Admin user not found")
                return False
            print("✅ Admin user found")
            
            # Check demo project exists
            cursor.execute("SELECT COUNT(*) FROM projects WHERE name = 'Demo Project'")
            project_count = cursor.fetchone()[0]
            if project_count == 0:
                print("❌ Demo project not found")
                return False
            print("✅ Demo project found")
            
            # Check demo system exists
            cursor.execute("SELECT COUNT(*) FROM systems WHERE name = 'Demo System'")
            system_count = cursor.fetchone()[0]
            if system_count == 0:
                print("❌ Demo system not found")
                return False
            print("✅ Demo system found")
            
            # Get and display demo data details
            cursor.execute("SELECT id, email, role FROM users WHERE email = 'admin@demo.com'")
            user = cursor.fetchone()
            print(f"📋 Admin user: {user[1]} (role: {user[2]})")
            
            cursor.execute("SELECT id, name, tenant_id FROM projects WHERE name = 'Demo Project'")
            project = cursor.fetchone()
            print(f"📋 Demo project: {project[1]} (tenant: {project[2]})")
            
            cursor.execute("SELECT id, name, status FROM systems WHERE name = 'Demo System'")
            system = cursor.fetchone()
            print(f"📋 Demo system: {system[1]} (status: {system[2]})")
            
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            return False
        finally:
            os.chdir(original_cwd)

def test_seed_demo_data_idempotent():
    """Test that seed-db is idempotent (safe to run multiple times)"""
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        temp_backend = Path(temp_dir) / 'backend'
        temp_backend.mkdir()
        
        try:
            # Copy necessary files to temp directory
            backend_path = Path(__file__).parent.parent
            shutil.copytree(backend_path / 'src', temp_backend / 'src')
            shutil.copy(backend_path / 'alembic.ini', temp_backend / 'alembic.ini')
            shutil.copytree(backend_path / 'alembic', temp_backend / 'alembic')
            
            # Change to temp directory
            os.chdir(temp_backend)
            
            # Set environment variables
            os.environ['DATABASE_URL'] = 'sqlite:///./test_system_builder_hub.db'
            
            # Initialize database
            result = subprocess.run([
                sys.executable, '-m', 'src.cli', 'init-db'
            ], capture_output=True, text=True, cwd=temp_backend)
            
            if result.returncode != 0:
                print(f"❌ init-db failed: {result.stderr}")
                return False
            
            # Run seed-db first time
            result1 = subprocess.run([
                sys.executable, '-m', 'src.cli', 'seed-db'
            ], capture_output=True, text=True, cwd=temp_backend)
            
            if result1.returncode != 0:
                print(f"❌ First seed-db failed: {result1.stderr}")
                return False
            
            # Run seed-db second time (should be idempotent)
            result2 = subprocess.run([
                sys.executable, '-m', 'src.cli', 'seed-db'
            ], capture_output=True, text=True, cwd=temp_backend)
            
            if result2.returncode != 0:
                print(f"❌ Second seed-db failed: {result2.stderr}")
                return False
            
            # Verify data is still correct (no duplicates)
            db_file = temp_backend / 'test_system_builder_hub.db'
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            # Should still have exactly 1 admin user
            cursor.execute("SELECT COUNT(*) FROM users WHERE email = 'admin@demo.com'")
            user_count = cursor.fetchone()[0]
            if user_count != 1:
                print(f"❌ Expected 1 admin user, found {user_count}")
                return False
            
            # Should still have exactly 1 demo project
            cursor.execute("SELECT COUNT(*) FROM projects WHERE name = 'Demo Project'")
            project_count = cursor.fetchone()[0]
            if project_count != 1:
                print(f"❌ Expected 1 demo project, found {project_count}")
                return False
            
            conn.close()
            
            print("✅ seed-db is idempotent (safe to run multiple times)")
            return True
            
        except Exception as e:
            print(f"❌ Idempotency test failed with exception: {e}")
            return False
        finally:
            os.chdir(original_cwd)

if __name__ == '__main__':
    print("🧪 Testing demo data seeding...")
    
    try:
        # Test basic seeding
        if not test_seed_demo_data():
            print("\n❌ Basic seeding test failed")
            sys.exit(1)
        
        # Test idempotency
        if not test_seed_demo_data_idempotent():
            print("\n❌ Idempotency test failed")
            sys.exit(1)
        
        print("\n🎉 All demo data seeding tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)
