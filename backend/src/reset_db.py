#!/usr/bin/env python3
"""
System Builder Hub Database Reset Tool
"""

import os
import sys
import subprocess
import sqlite3
import uuid
import time
from datetime import datetime
import click

def stop_running_services():
    """Stop running Flask and worker processes gracefully"""
    try:
        import psutil
        import signal
        
        stopped_count = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'python' in cmdline and ('src/cli.py run' in cmdline or 'src/cli.py worker' in cmdline):
                    click.echo(f"   Stopping process {proc.info['pid']}: {cmdline}")
                    proc.send_signal(signal.SIGTERM)
                    try:
                        proc.wait(timeout=5)
                        stopped_count += 1
                    except psutil.TimeoutExpired:
                        proc.kill()
                        stopped_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return stopped_count
    except ImportError:
        click.echo("   psutil not available, skipping process management")
        return 0

def reset_redis():
    """Reset Redis using FLUSHALL"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=2)
        r.ping()
        r.flushall()
        return True
    except Exception as e:
        click.echo(f"   Redis not available: {e}")
        return False

def remove_database_file():
    """Remove the database file if it exists"""
    db_file = 'system_builder_hub.db'
    if os.path.exists(db_file):
        os.remove(db_file)
        return True
    return False

def run_migrations():
    """Run Alembic migrations"""
    try:
        # Run migrations
        result = subprocess.run(['alembic', 'upgrade', 'head'], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            click.echo(f"   Migration error: {result.stderr}")
            return False
        
        # Get current migration
        current_result = subprocess.run(['alembic', 'current'], 
                                      capture_output=True, text=True, timeout=10)
        
        if current_result.returncode == 0:
            click.echo(f"   Current migration: {current_result.stdout.strip()}")
        
        return True
        
    except subprocess.TimeoutExpired:
        click.echo("   Migration timed out")
        return False
    except Exception as e:
        click.echo(f"   Migration error: {e}")
        return False

def seed_demo_data():
    """Seed demo data - creates demo tenant, admin user, and sample project"""
    try:
        # Get database path
        db_path = os.getenv('DATABASE_URL', 'sqlite:///./system_builder_hub.db')
        if db_path.startswith('sqlite:///'):
            db_file = db_path.replace('sqlite:///', '')
        else:
            click.echo("   ❌ Only SQLite database seeding is supported")
            return False
        
        # Check if database file exists
        if not os.path.exists(db_file):
            click.echo("   ❌ Database file not found. Run init-db first.")
            return False
        
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Generate IDs and timestamps
        demo_tenant_id = 'demo-tenant-001'
        admin_user_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        system_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        # Hash password for admin user (simple hash for demo purposes)
        import hashlib
        admin_password = 'admin123'
        password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
        
        # Create demo tenant (if tenants table exists, otherwise use string ID)
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO tenants (id, slug, name, plan, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (demo_tenant_id, 'demo', 'Demo Tenant', 'free', 'active', now, now))
            click.echo("   ✅ Demo tenant created")
        except sqlite3.OperationalError:
            # Tenants table doesn't exist, that's okay - we'll use string ID
            click.echo("   ℹ️  Tenants table not found, using string tenant ID")
        
        # Create admin user (check if exists first)
        cursor.execute("SELECT id FROM users WHERE email = 'admin@demo.com'")
        existing_user = cursor.fetchone()
        if existing_user:
            admin_user_id = existing_user[0]
            click.echo("   ℹ️  Admin user already exists")
        else:
            cursor.execute("""
                INSERT INTO users (id, email, password_hash, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (admin_user_id, 'admin@demo.com', password_hash, 'admin', now, now))
            click.echo("   ✅ Admin user created (admin@demo.com / admin123)")
        
        # Create demo project (check if exists first)
        cursor.execute("SELECT id FROM projects WHERE name = 'Demo Project'")
        existing_project = cursor.fetchone()
        if existing_project:
            project_id = existing_project[0]
            click.echo("   ℹ️  Demo project already exists")
        else:
            cursor.execute("""
                INSERT INTO projects (id, name, description, tenant_id, no_llm_mode, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (project_id, 'Demo Project', 'Demo project for testing SBH capabilities', demo_tenant_id, False, now, now))
            click.echo("   ✅ Demo project created")
        
        # Create demo system (check if exists first)
        cursor.execute("SELECT id FROM systems WHERE name = 'Demo System'")
        existing_system = cursor.fetchone()
        if existing_system:
            system_id = existing_system[0]
            click.echo("   ℹ️  Demo system already exists")
        else:
            cursor.execute("""
                INSERT INTO systems (id, project_id, name, blueprint, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (system_id, project_id, 'Demo System', '{"demo": true, "description": "A sample system for testing"}', 'draft', now, now))
            click.echo("   ✅ Demo system created")
        
        # Create tenant-user relationship if tenants table exists
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO tenant_users (id, tenant_id, user_id, role, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (str(uuid.uuid4()), demo_tenant_id, admin_user_id, 'owner', now))
            click.echo("   ✅ Tenant-user relationship created")
        except sqlite3.OperationalError:
            # Tenant users table doesn't exist, that's okay
            click.echo("   ℹ️  Tenant-users table not found, skipping relationship")
        
        conn.commit()
        conn.close()
        
        click.echo("   📋 Demo data summary:")
        click.echo(f"      - Tenant ID: {demo_tenant_id}")
        click.echo(f"      - Admin User: admin@demo.com")
        click.echo(f"      - Project ID: {project_id}")
        click.echo(f"      - System ID: {system_id}")
        
        return True
        
    except Exception as e:
        click.echo(f"   ❌ Demo data seeding error: {e}")
        return False

def run_verification_checks():
    """Run smoke verification checks"""
    try:
        # Check database file exists
        if not os.path.exists('system_builder_hub.db'):
            click.echo("   ❌ Database file not found")
            return False
        
        # Check project count
        conn = sqlite3.connect('system_builder_hub.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM projects")
        project_count = cursor.fetchone()[0]
        click.echo(f"   📊 Projects: {project_count}")
        
        cursor.execute("SELECT COUNT(*) FROM systems")
        system_count = cursor.fetchone()[0]
        click.echo(f"   📊 Systems: {system_count}")
        
        conn.close()
        
        # Check if server responds (if it's running)
        try:
            import requests
            response = requests.get('http://localhost:5001/healthz', timeout=5)
            if response.status_code == 200:
                click.echo("   ✅ Health check endpoint responding")
            else:
                click.echo(f"   ⚠️  Health check returned {response.status_code}")
        except ImportError:
            click.echo("   ℹ️  requests not available, skipping health check")
        except Exception:
            click.echo("   ℹ️  Server not running (expected if --with-server not used)")
        
        return True
        
    except Exception as e:
        click.echo(f"   Verification error: {e}")
        return False

def start_services():
    """Start Flask server"""
    try:
        # Start Flask server
        server_process = subprocess.Popen(
            ['python', 'src/cli.py', 'run', '--port', '5001', '--debug'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        time.sleep(3)
        
        # Check if server process is still running
        if server_process.poll() is None:
            click.echo("   ✅ Flask server started successfully")
            return True
        else:
            click.echo("   ❌ Flask server failed to start")
            return False
            
    except Exception as e:
        click.echo(f"   Service start error: {e}")
        return False

@click.command()
@click.option('--with-server', is_flag=True, help='Start server and workers after reset')
def reset_db(with_server):
    """Reset database and environment for local development"""
    try:
        click.echo("🔄 Starting System Builder Hub database reset...")
        
        # Step 1: Stop services gracefully
        click.echo("⏹️  Stopping running services...")
        stopped_processes = stop_running_services()
        if stopped_processes:
            click.echo(f"✅ Stopped {stopped_processes} running processes")
        else:
            click.echo("ℹ️  No running processes to stop")
        
        # Step 2: Reset Redis
        click.echo("🗑️  Resetting Redis...")
        redis_reset_result = reset_redis()
        if redis_reset_result:
            click.echo("✅ Redis flushed successfully")
        else:
            click.echo("⚠️  Redis not available (continuing without Redis reset)")
        
        # Step 3: Delete database file
        click.echo("🗑️  Removing existing database...")
        db_removed = remove_database_file()
        if db_removed:
            click.echo("✅ Database file removed")
        else:
            click.echo("ℹ️  No database file to remove")
        
        # Step 4: Reset Alembic migration state
        click.echo("📦 Running database migrations...")
        migration_result = run_migrations()
        if migration_result:
            click.echo(f"✅ Migrations completed successfully")
        else:
            click.echo("❌ Migration failed")
            return 1
        
        # Step 5: Seed demo/staging data
        click.echo("🌱 Seeding demo data...")
        seed_result = seed_demo_data()
        if seed_result:
            click.echo("✅ Demo tenant + projects seeded")
        else:
            click.echo("❌ Demo data seeding failed")
            return 1
        
        # Step 6: Run smoke verification checks
        click.echo("🔍 Running verification checks...")
        verification_result = run_verification_checks()
        if verification_result:
            click.echo("✅ Environment healthy")
        else:
            click.echo("❌ Verification checks failed")
            return 1
        
        # Step 7: Optional auto-restart
        if with_server:
            click.echo("🚀 Starting services...")
            start_result = start_services()
            if start_result:
                click.echo("✅ Services started successfully")
                click.echo("\n🌐 Access URLs:")
                click.echo("   Dashboard: http://localhost:5001/")
                click.echo("   Builder: http://localhost:5001/builder")
                click.echo("   Marketplace: http://localhost:5001/marketplace")
                click.echo("   Settings: http://localhost:5001/settings")
                click.echo("   Eval Lab: http://localhost:5001/eval-lab")
                click.echo("   API Docs: http://localhost:5001/openapi.json")
            else:
                click.echo("❌ Failed to start services")
                return 1
        
        click.echo("\n🎉 Database reset completed successfully!")
        return 0
        
    except Exception as e:
        click.echo(f"❌ Reset failed: {e}")
        return 1

if __name__ == '__main__':
    reset_db()
