#!/usr/bin/env python3
"""
System Builder Hub CLI Entrypoint
"""
import os
import sys
import click
import subprocess
import sqlite3
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app import create_app
from llm_startup_validation import run_llm_startup_validation, get_llm_validation_summary
from llm_provider_service import llm_provider_service

# Import version
try:
    from version import APP_VERSION, VERSION_STRING, COMMIT_HASH, BRANCH
except ImportError:
    APP_VERSION = "0.1.0"
    VERSION_STRING = APP_VERSION
    COMMIT_HASH = None
    BRANCH = None

@click.group()
@click.version_option(version=APP_VERSION)
def cli():
    """System Builder Hub CLI"""
    pass

@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=5001, help='Port to bind to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--reload', is_flag=True, help='Enable auto-reload (dev only)')
def run(host: str, port: int, debug: bool, reload: bool):
    """Start the SBH web application"""
    try:
        app = create_app()
        
        # Set debug mode
        if debug or os.getenv('FLASK_ENV') == 'development':
            app.config['DEBUG'] = True
            reload = True
        
        click.echo(f"🚀 Starting SBH on {host}:{port}")
        click.echo(f"📊 Environment: {os.getenv('FLASK_ENV', 'production')}")
        click.echo(f"🔧 Debug: {app.config.get('DEBUG', False)}")
        click.echo(f"🔄 Auto-reload: {reload}")
        
        if reload and app.config.get('DEBUG'):
            # Use Flask development server with reload
            app.run(host=host, port=port, debug=True)
        else:
            # Use production server
            try:
                import gunicorn.app.base
                
                class StandaloneApplication(gunicorn.app.base.BaseApplication):
                    def __init__(self, app, options=None):
                        self.options = options or {}
                        self.application = app
                        super().__init__()
                    
                    def load_config(self):
                        for key, value in self.options.items():
                            self.cfg.set(key, value)
                    
                    def load(self):
                        return self.application
                
                options = {
                    'bind': f'{host}:{port}',
                    'workers': 2,
                    'threads': 2,
                    'timeout': 60,
                    'worker_class': 'sync'
                }
                
                StandaloneApplication(app, options).run()
                
            except ImportError:
                click.echo("⚠️ Gunicorn not available, using Flask development server")
                app.run(host=host, port=port, debug=False)
                
    except Exception as e:
        click.echo(f"❌ Failed to start application: {e}")
        sys.exit(1)

@cli.command()
@click.option('--force', is_flag=True, help='Force recreation of database')
def init_db(force: bool):
    """Initialize and migrate the database"""
    try:
        click.echo("🗄️ Initializing database...")
        
        # Get database path
        db_path = os.getenv('DATABASE_URL', 'sqlite:///./system_builder_hub.db')
        if db_path.startswith('sqlite:///'):
            db_file = db_path.replace('sqlite:///', '')
            db_dir = os.path.dirname(db_file)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                click.echo(f"📁 Created database directory: {db_dir}")
        
        # Check if Alembic is available
        try:
            import alembic
            click.echo("📦 Using Alembic for migrations...")
            
            # Run Alembic upgrade
            result = subprocess.run([
                sys.executable, '-m', 'alembic', 'upgrade', 'head'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                click.echo("✅ Database migrations completed successfully")
                click.echo(f"📊 Database path: {db_path}")
            else:
                click.echo(f"⚠️ Alembic migration failed: {result.stderr}")
                click.echo("🔄 Falling back to manual schema creation...")
                _create_schema_manually()
                
        except ImportError:
            click.echo("📦 Alembic not available, creating schema manually...")
            _create_schema_manually()
        
        click.echo("✅ Database initialization complete")
        
    except Exception as e:
        click.echo(f"❌ Database initialization failed: {e}")
        sys.exit(1)

def _create_schema_manually():
    """Create database schema manually if Alembic is not available"""
    db_path = os.getenv('DATABASE_URL', 'sqlite:///./system_builder_hub.db')
    if db_path.startswith('sqlite:///'):
        db_file = db_path.replace('sqlite:///', '')
        
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_provider_configs (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                api_key_encrypted TEXT NOT NULL,
                default_model TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                last_tested TIMESTAMP,
                test_latency_ms INTEGER,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_usage_logs (
                id TEXT PRIMARY KEY,
                provider_config_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                tokens_used INTEGER,
                latency_ms INTEGER,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                created_at TIMESTAMP NOT NULL,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                tenant_id TEXT NOT NULL,
                no_llm_mode BOOLEAN NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS systems (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                blueprint TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        """)
        
        conn.commit()
        conn.close()
        click.echo("✅ Manual schema creation completed")

@cli.command()
@click.option('--email', prompt='Admin email')
@click.option('--password', prompt='Admin password', hide_input=True, confirmation_prompt=True)
def create_admin(email: str, password: str):
    """Create an admin user"""
    try:
        click.echo("👤 Creating admin user...")
        
        # For now, we'll just create a simple admin record
        # In a real implementation, this would use proper user management
        db_path = os.getenv('DATABASE_URL', 'sqlite:///./system_builder_hub.db')
        if db_path.startswith('sqlite:///'):
            db_file = db_path.replace('sqlite:///', '')
            
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Create users table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """)
            
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                click.echo(f"⚠️ User {email} already exists")
                return
            
            # Create admin user (simplified - in production use proper hashing)
            import uuid
            from datetime import datetime
            
            user_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            
            cursor.execute("""
                INSERT INTO users (id, email, password_hash, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, email, f"hash_{password}", 'admin', now, now))
            
            conn.commit()
            conn.close()
            
            click.echo(f"✅ Admin user {email} created successfully")
            click.echo(f"🆔 User ID: {user_id}")
            
    except Exception as e:
        click.echo(f"❌ Failed to create admin user: {e}")
        sys.exit(1)

@cli.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def check(verbose: bool):
    """Run system health checks"""
    try:
        click.echo("🔍 Running system health checks...")
        
        checks = []
        
        # Check 1: Database connectivity
        try:
            db_path = os.getenv('DATABASE_URL', 'sqlite:///./system_builder_hub.db')
            if db_path.startswith('sqlite:///'):
                db_file = db_path.replace('sqlite:///', '')
                if os.path.exists(db_file):
                    conn = sqlite3.connect(db_file)
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    conn.close()
                    checks.append(("Database", "✅ Connected"))
                else:
                    checks.append(("Database", "❌ File not found"))
            else:
                checks.append(("Database", "⚠️ Non-SQLite database"))
        except Exception as e:
            checks.append(("Database", f"❌ Error: {e}"))
        
        # Check 2: LLM startup validation
        try:
            validation_result = run_llm_startup_validation()
            summary = get_llm_validation_summary()
            if summary['overall_status'] == 'healthy':
                checks.append(("LLM Validation", "✅ Healthy"))
            else:
                checks.append(("LLM Validation", f"⚠️ {summary['overall_status']}"))
        except Exception as e:
            checks.append(("LLM Validation", f"❌ Error: {e}"))
        
        # Check 3: Environment variables
        required_vars = ['LLM_SECRET_KEY']
        optional_vars = ['FLASK_ENV', 'DATABASE_URL', 'CORS_ORIGINS']
        
        env_checks = []
        for var in required_vars:
            if os.getenv(var):
                env_checks.append(f"✅ {var}")
            else:
                env_checks.append(f"❌ {var} (required)")
        
        for var in optional_vars:
            if os.getenv(var):
                env_checks.append(f"✅ {var}")
            else:
                env_checks.append(f"⚠️ {var} (optional)")
        
        checks.append(("Environment", "\n".join(env_checks)))
        
        # Check 4: App creation
        try:
            app = create_app()
            with app.test_client() as client:
                response = client.get('/healthz')
                if response.status_code == 200:
                    checks.append(("App Creation", "✅ Success"))
                else:
                    checks.append(("App Creation", f"⚠️ Health check failed: {response.status_code}"))
        except Exception as e:
            checks.append(("App Creation", f"❌ Error: {e}"))
        
        # Display version information
        click.echo(f"\n📋 Version Information:")
        click.echo(f"  Version: {APP_VERSION}")
        click.echo(f"  Version String: {VERSION_STRING}")
        if COMMIT_HASH:
            click.echo(f"  Commit: {COMMIT_HASH}")
        if BRANCH:
            click.echo(f"  Branch: {BRANCH}")
        
        # Display results
        click.echo("\n📊 Health Check Results:")
        click.echo("=" * 50)
        
        all_passed = True
        for check_name, result in checks:
            click.echo(f"{check_name}:")
            for line in result.split('\n'):
                click.echo(f"  {line}")
                if line.startswith('❌'):
                    all_passed = False
            click.echo()
        
        if all_passed:
            click.echo("🎉 All health checks passed!")
            return 0
        else:
            click.echo("⚠️ Some health checks failed")
            return 1
            
    except Exception as e:
        click.echo(f"❌ Health check failed: {e}")
        return 1

@cli.command()
@click.option('--name', default='Demo Project', help='Project name')
def demo(name: str):
    """Create a demo project for testing"""
    try:
        click.echo(f"🎭 Creating demo project: {name}")
        
        # Create app context
        app = create_app()
        with app.app_context():
            # Create demo project
            db_path = os.getenv('DATABASE_URL', 'sqlite:///./system_builder_hub.db')
            if db_path.startswith('sqlite:///'):
                db_file = db_path.replace('sqlite:///', '')
                
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                # Create demo project
                import uuid
                from datetime import datetime
                
                project_id = str(uuid.uuid4())
                system_id = str(uuid.uuid4())
                now = datetime.utcnow().isoformat()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO projects (id, name, description, tenant_id, no_llm_mode, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (project_id, name, 'Demo project for testing', 'demo_tenant', False, now, now))
                
                cursor.execute("""
                    INSERT OR REPLACE INTO systems (id, project_id, name, blueprint, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (system_id, project_id, f'{name} System', '{"demo": true}', 'draft', now, now))
                
                conn.commit()
                conn.close()
                
                click.echo(f"✅ Demo project created successfully")
                click.echo(f"🆔 Project ID: {project_id}")
                click.echo(f"🆔 System ID: {system_id}")
                click.echo(f"🌐 Access at: http://localhost:5001/ui/visual-builder?project={project_id}")
                
    except Exception as e:
        click.echo(f"❌ Failed to create demo project: {e}")
        sys.exit(1)

if __name__ == '__main__':
    cli()
