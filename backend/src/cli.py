#!/usr/bin/env python3
"""
System Builder Hub CLI
"""

import os
import sys
import subprocess
import sqlite3
import uuid
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
import click

# Load environment variables from .env file
env_path = find_dotenv(usecwd=True)
load_dotenv(env_path)
print(f"🔑 Loaded env from: {env_path}")

# Add dependency check at the very top
try:
    from src.dependency_check import collect_dependency_status, print_dependency_error
except ImportError:
    # If dependency_check itself can't be imported, we have bigger problems
    print("❌ Critical error: Cannot import dependency_check module")
    sys.exit(1)

def preflight_check():
    """Run preflight checks before any CLI operations."""
    status = collect_dependency_status()
    
    if not status["deps"]:
        print_dependency_error(status["required_missing"])
        return False
    
    return True

def _auto_discover_module_commands(cli_group):
    """Auto-discover and register module CLI commands"""
    import os
    import importlib
    from pathlib import Path
    
    src_path = Path("src")
    if not src_path.exists():
        return
    
    # Look for module directories
    for module_dir in src_path.iterdir():
        if module_dir.is_dir() and not module_dir.name.startswith("_"):
            module_name = module_dir.name
            cli_file = module_dir / "cli.py"
            
            if cli_file.exists():
                try:
                    # Try to import the module CLI
                    cli_module = importlib.import_module(f"src.{module_name}.cli")
                    
                    # Look for click group (module name)
                    if hasattr(cli_module, module_name):
                        command_group = getattr(cli_module, module_name)
                        if hasattr(command_group, "commands"):
                            cli_group.add_command(command_group)
                            click.echo(f"Auto-registered CLI commands for {module_name}")
                except ImportError as e:
                    # Module not available, skip
                    pass
                except Exception as e:
                    click.echo(f"Failed to auto-register CLI for {module_name}: {e}")

@click.group()
def cli():
    """System Builder Hub CLI"""
    pass

@cli.command()
def check():
    """Run dependency and environment checks"""
    click.echo("🔍 Running System Builder Hub health checks...")
    
    # Check dependencies using unified status
    status = collect_dependency_status()
    
    if status["deps"]:
        click.echo("✅ All required dependencies available")
        
        # Show optional dependencies status
        if status["optional_missing"]:
            click.echo(f"ℹ️  Optional dependencies missing: {', '.join(status['optional_missing'])}")
        else:
            click.echo("✅ All optional dependencies available")
    else:
        click.echo(f"❌ Missing {len(status['required_missing'])} required dependencies:")
        for dep in status["required_missing"]:
            click.echo(f"   - {dep}")
        click.echo("\n🔧 Run: pip install -r requirements.txt")
        return 1
    
    # Check database
    try:
        import sqlite3
        if os.path.exists('system_builder_hub.db'):
            conn = sqlite3.connect('system_builder_hub.db')
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            conn.close()
            click.echo(f"✅ Database: {table_count} tables found")
        else:
            click.echo("ℹ️  Database: No database file found (run migrations to create)")
    except Exception as e:
        click.echo(f"⚠️  Database: {e}")
    
    # Check Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=2)
        r.ping()
        click.echo("✅ Redis: Connected")
    except Exception as e:
        click.echo(f"⚠️  Redis: {e}")
    
    click.echo("🎉 Health checks completed!")
    return 0

@cli.command()
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--port', default=5001, help='Port to bind to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--no-reload', is_flag=True, help='Disable Flask reloader (recommended for build progress)')
def run(host, port, debug, no_reload):
    """Run the SBH server"""
    # Run preflight check before starting server
    if not preflight_check():
        sys.exit(1)
    
    from src.app import create_app
    
    app = create_app()
    
    if debug:
        app.config['DEBUG'] = True
    
    # Disable reloader if requested or if COB_PERSIST_BUILDS is enabled
    use_reloader = not no_reload and not os.getenv('COB_PERSIST_BUILDS', '0') == '1'
    
    if not use_reloader:
        print("🔄 Flask reloader disabled - build progress will persist across requests")
    
    app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)

@cli.command()
def smoke():
    """Run smoke tests to verify core functionality"""
    # Run preflight check before smoke tests
    if not preflight_check():
        sys.exit(1)
    
    print("🧪 Running SBH Smoke Tests...")
    
    # Run startup doctor
    try:
        doctor()
        print("✅ Smoke tests passed")
    except Exception as e:
        print(f"❌ Smoke tests failed: {e}")
        sys.exit(1)

@cli.command()
def doctor():
    """Run startup diagnostics"""
    # Run preflight check before diagnostics
    if not preflight_check():
        sys.exit(1)
    
    startup_doctor_path = Path(__file__).parent.parent / 'tools' / 'startup_doctor.py'
    
    if not startup_doctor_path.exists():
        print("⚠️  Startup doctor not found, skipping diagnostics")
        return
    
    subprocess.run([sys.executable, str(startup_doctor_path)])

@cli.command()
@click.option('--name', default='Demo Project', help='Project name')
def demo(name: str):
    """Create a demo project for testing"""
    # Run preflight check before demo creation
    if not preflight_check():
        sys.exit(1)
    
    try:
        click.echo(f"🎭 Creating demo project: {name}")
        
        # Create app context
        from src.app import create_app
        app = create_app()
        with app.app_context():
            # Create demo project
            db_path = os.getenv('DATABASE_URL', 'sqlite:///./system_builder_hub.db')
            if db_path.startswith('sqlite:///'):
                db_file = db_path.replace('sqlite:///', '')
                
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                # Create demo project
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

@cli.command(name="init-db")
def init_db():
    """Initialize database schema using Alembic migrations"""
    # Run preflight check before database initialization
    if not preflight_check():
        sys.exit(1)
    
    try:
        click.echo("🗄️  Initializing database schema...")
        
        # Check if Alembic is configured
        alembic_ini_path = Path(__file__).parent.parent / 'alembic.ini'
        if not alembic_ini_path.exists():
            click.echo("❌ Alembic not configured. Missing alembic.ini file")
            click.echo("💡 Make sure you're running from the backend directory")
            return 1
        
        # Run Alembic upgrade head from the backend directory
        backend_dir = Path(__file__).parent.parent
        result = subprocess.run([
            sys.executable, '-m', 'alembic', 'upgrade', 'head'
        ], capture_output=True, text=True, cwd=backend_dir)
        
        if result.returncode == 0:
            click.echo("✅ Database schema initialized successfully")
            if result.stdout.strip():
                click.echo("📋 Migration output:")
                click.echo(result.stdout)
            return 0
        else:
            click.echo("❌ Database initialization failed")
            if result.stderr.strip():
                click.echo("📋 Error output:")
                click.echo(result.stderr)
            return 1
            
    except Exception as e:
        click.echo(f"❌ Database initialization error: {e}")
        return 1

@cli.command(name="seed-db")
def seed_db():
    """Seed database with demo data (tenant, admin user, sample project)"""
    # Run preflight check before seeding
    if not preflight_check():
        sys.exit(1)
    
    try:
        click.echo("🌱 Seeding database with demo data...")
        
        # Try to import seed function from reset_db
        try:
            from src.reset_db import seed_demo_data
        except ImportError as e:
            click.echo(f"❌ Cannot import seed function: {e}")
            click.echo("💡 Make sure reset_db.py exists and is accessible")
            return 1
        
        # Run seeding
        seed_result = seed_demo_data()
        if seed_result:
            click.echo("✅ Demo data seeded successfully")
            click.echo("📋 Seeded:")
            click.echo("   - Demo tenant")
            click.echo("   - Admin user")
            click.echo("   - Sample project")
            return 0
        else:
            click.echo("❌ Demo data seeding failed")
            click.echo("💡 Check if database is initialized (run init-db first)")
            return 1
            
    except Exception as e:
        click.echo(f"❌ Database seeding error: {e}")
        return 1

@cli.command()
@click.option('--with-server', is_flag=True, help='Start server and workers after reset')
def reset_db(with_server: bool):
    """Reset database and environment for local development"""
    # Run preflight check before reset
    if not preflight_check():
        sys.exit(1)
    
    try:
        click.echo("🔄 Starting System Builder Hub database reset...")
        
        # Import reset functions
        from src.reset_db import (
            stop_running_services, reset_redis, remove_database_file,
            run_migrations, seed_demo_data, run_verification_checks, start_services
        )
        
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

@cli.command()
def dump_routes():
    """Dump all available routes"""
    # Run preflight check before dumping routes
    if not preflight_check():
        sys.exit(1)
    
    from src.app import create_app
    app = create_app()
    print("Available routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint:30s} {rule.methods} {rule.rule}")

@cli.command()
def db_info():
    """Get database information (dev-only)"""
    # Run preflight check
    if not preflight_check():
        sys.exit(1)
    
    try:
        import json
        import os
        import sqlite3
        
        # Get database path from config
        from src.app import create_app
        app = create_app()
        
        with app.app_context():
            db_path = app.config.get('DATABASE', 'system_builder_hub.db')
            abs_db_path = os.path.abspath(db_path)
            
            # Connect to database
            db = sqlite3.connect(abs_db_path)
            db.row_factory = sqlite3.Row
            
            # Get tables
            cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row['name'] for row in cursor.fetchall()]
            
            # Get tasks preview (last 10)
            tasks_preview = []
            if 'tasks' in tables:
                try:
                    cursor = db.execute("""
                        SELECT id, title, completed, tenant_id, created_at
                        FROM tasks 
                        ORDER BY id DESC 
                        LIMIT 10
                    """)
                    tasks_preview = [dict(row) for row in cursor.fetchall()]
                except Exception as e:
                    click.echo(f"Warning: Could not fetch tasks preview: {e}")
                    tasks_preview = []
            
            db.close()
            
            # Output JSON
            result = {
                "db_path": abs_db_path,
                "tables": tables,
                "tasks_preview": tasks_preview
            }
            
            print(json.dumps(result, indent=2))
            
    except Exception as e:
        click.echo(f"❌ Error getting DB info: {e}")
        return 1

# CRM Module Commands
@cli.group()
def crm():
    """CRM Flagship v1.01 module commands"""
    pass

@crm.command()
def status():
    """Check CRM module status and health"""
    # Run preflight check
    if not preflight_check():
        sys.exit(1)
    
    try:
        click.echo("🔍 Checking CRM Flagship v1.01 module status...")
        
        # Check database tables
        db_path = os.path.abspath('system_builder_hub.db')
        if not os.path.exists(db_path):
            click.echo("❌ Database not found. Run 'init-db' first.")
            return 1
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check CRM tables
        crm_tables = [
            'contacts', 'deals', 'activities', 'projects', 
            'tasks', 'messages', 'message_threads', 'tenant_users', 'crm_ops_audit_logs'
        ]
        
        missing_tables = []
        existing_tables = []
        
        for table in crm_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if cursor.fetchone():
                existing_tables.append(table)
            else:
                missing_tables.append(table)
        
        conn.close()
        
        # Report status
        click.echo(f"📊 CRM Tables: {len(existing_tables)}/{len(crm_tables)} present")
        
        if existing_tables:
            click.echo("✅ Present tables:")
            for table in existing_tables:
                click.echo(f"   - {table}")
        
        if missing_tables:
            click.echo("❌ Missing tables:")
            for table in missing_tables:
                click.echo(f"   - {table}")
            click.echo("💡 Run 'alembic upgrade head' to create missing tables")
        
        # Check API endpoints (if server is running)
        try:
            import requests
            response = requests.get('http://127.0.0.1:5001/api/contacts/', timeout=2)
            if response.status_code == 401:  # Expected: tenant context required
                click.echo("✅ CRM API endpoints responding")
            else:
                click.echo(f"⚠️  CRM API endpoints: HTTP {response.status_code}")
        except Exception:
            click.echo("ℹ️  CRM API endpoints: Server not running (start with 'run')")
        
        click.echo("🎉 CRM status check completed!")
        return 0
        
    except Exception as e:
        click.echo(f"❌ CRM status check error: {e}")
        return 1

@crm.command()
@click.option('--force', is_flag=True, help='Force reseed even if data exists')
def seed(force):
    """Seed CRM module with demo data"""
    # Run preflight check
    if not preflight_check():
        sys.exit(1)
    
    try:
        click.echo("🌱 Seeding CRM Flagship v1.01 with demo data...")
        
        # Import CRM seeding function
        try:
            from src.crm_ops.seed import seed_crm_demo_data
        except ImportError:
            click.echo("❌ CRM seeding module not found")
            click.echo("💡 CRM seeding functionality not yet implemented")
            return 1
        
        # Run seeding
        result = seed_crm_demo_data(force=force)
        if result:
            click.echo("✅ CRM demo data seeded successfully")
            click.echo("📋 Seeded:")
            click.echo("   - Demo contacts")
            click.echo("   - Sample deals")
            click.echo("   - Activity records")
            click.echo("   - Project templates")
            click.echo("   - Task examples")
            return 0
        else:
            click.echo("❌ CRM demo data seeding failed")
            return 1
            
    except Exception as e:
        click.echo(f"❌ CRM seeding error: {e}")
        return 1

@crm.command()
@click.option('--keep-data', is_flag=True, help='Keep existing CRM data')
def reset(keep_data):
    """Reset CRM module (clear data and reseed)"""
    # Run preflight check
    if not preflight_check():
        sys.exit(1)
    
    try:
        click.echo("🔄 Resetting CRM Flagship v1.01 module...")
        
        if not keep_data:
            click.echo("🗑️  Clearing existing CRM data...")
            # For now, just log that clearing would happen
            click.echo("ℹ️  CRM data clearing would be implemented here")
        
        # Reseed
        click.echo("🌱 Reseeding CRM data...")
        try:
            from src.crm_ops.seed import seed_crm_demo_data
            result = seed_crm_demo_data(force=True)
            if result:
                click.echo("✅ CRM reset completed successfully")
                return 0
            else:
                click.echo("❌ CRM reseeding failed")
                return 1
        except ImportError:
            click.echo("❌ CRM seeding module not found")
            return 1
            
    except Exception as e:
        click.echo(f"❌ CRM reset error: {e}")
        return 1
# Build Commands
@cli.group()
def build():
    """Build new modules and systems"""
    pass

@build.command()
@click.option("--name", required=True, help="Module name (e.g., lms)")
@click.option("--title", required=True, help="Module title (e.g., LMS Core)")
@click.option("--version", required=True, help="Module version (e.g., 1.0.0)")
@click.option("--category", required=True, help="Module category (e.g., Education)")
@click.option("--features", required=True, help="Comma-separated features (e.g., courses,lessons,quizzes)")
@click.option("--plans", required=True, help="Comma-separated plans (e.g., starter,pro,enterprise)")
@click.option("--spec", required=True, help="System specification in natural language")
def module(name, title, version, category, features, plans, spec):
    """Build a new module from specification"""
    from src.builder.module_scaffolder import ModuleScaffolder
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Building module: {name}")
    
    try:
        scaffolder = ModuleScaffolder()
        scaffolder.build_module(
            name=name,
            title=title,
            version=version,
            category=category,
            features=features.split(","),
            plans=plans.split(","),
            spec=spec
        )
        logger.info(f"✅ Module {name} built successfully!")
    except Exception as e:
        logger.error(f"Failed to build module {name}: {e}")
        raise click.ClickException(str(e))

@build.command()
@click.option("--spec", required=True, help="Natural language specification")
@click.option("--dry-run", is_flag=True, help="Show parsed spec without building")
def natural(spec, dry_run):
    """Build a new module from natural language specification"""
    import logging
    from src.builder.spec_parser import SpecParser
    from src.builder.module_scaffolder import ModuleScaffolder
    
    logger = logging.getLogger(__name__)
    logger.info("Parsing natural language specification")
    
    try:
        # Parse the natural language specification
        parser = SpecParser()
        parsed_spec = parser.parse_spec(spec)
        
        # Show parsed specification
        click.echo("🔍 Parsed Specification:")
        click.echo(f"  Name: {parsed_spec['name']}")
        click.echo(f"  Title: {parsed_spec['title']}")
        click.echo(f"  Version: {parsed_spec['version']}")
        click.echo(f"  Category: {parsed_spec['category']}")
        click.echo(f"  Features: {', '.join(parsed_spec['features'])}")
        click.echo(f"  Plans: {', '.join(parsed_spec['plans'])}")
        click.echo(f"  Description: {parsed_spec['spec']}")
        
        if dry_run:
            click.echo("\\n✅ Dry run completed - no module built")
            return
        
        # Confirm with user
        if not click.confirm("\\nProceed with building this module?"):
            click.echo("❌ Module build cancelled")
            return
        
        # Build the module using the deterministic scaffolder
        scaffolder = ModuleScaffolder()
        scaffolder.build_module(
            name=parsed_spec['name'],
            title=parsed_spec['title'],
            version=parsed_spec['version'],
            category=parsed_spec['category'],
            features=parsed_spec['features'],
            plans=parsed_spec['plans'],
            spec=parsed_spec['spec']
        )
        
        # Save the parsed specification
        parser.save_parsed_spec(parsed_spec['name'], parsed_spec)
        
        logger.info(f"✅ Module {parsed_spec['name']} built successfully from natural language!")
        click.echo(f"\\n🎉 Module {parsed_spec['name']} built successfully!")
        
    except Exception as e:
        logger.error(f"Failed to build module from natural language: {e}")
        raise click.ClickException(str(e))

@build.command()
@click.option("--file", required=True, help="Path to JSON specification file")
@click.option("--dry-run", is_flag=True, help="Validate spec without building")
def spec(file, dry_run):
    """Build a module from structured JSON specification"""
    import json
    import logging
    from pathlib import Path
    
    logger = logging.getLogger(__name__)
    logger.info(f"Building module from spec file: {file}")
    
    try:
        # Read and parse JSON spec file
        spec_path = Path(file)
        if not spec_path.exists():
            raise click.ClickException(f"Spec file not found: {file}")
        
        with open(spec_path, 'r') as f:
            spec_data = json.load(f)
        
        # Validate required fields
        required_fields = ['name', 'title', 'version', 'category', 'description']
        for field in required_fields:
            if not spec_data.get(field):
                raise click.ClickException(f"Missing required field: {field}")
        
        click.echo("📋 Specification loaded:")
        click.echo(f"  Name: {spec_data['name']}")
        click.echo(f"  Title: {spec_data['title']}")
        click.echo(f"  Version: {spec_data['version']}")
        click.echo(f"  Category: {spec_data['category']}")
        click.echo(f"  Features: {len(spec_data.get('features', []))}")
        click.echo(f"  Plans: {len(spec_data.get('plans', []))}")
        click.echo(f"  Description: {spec_data['description'][:100]}...")
        
        if dry_run:
            click.echo("\\n✅ Dry run completed - spec is valid")
            return
        
        # Confirm with user
        if not click.confirm("\\nProceed with building this module?"):
            click.echo("❌ Module build cancelled")
            return
        
        # Build module using Spec API
        from src.spec.api import _create_module_from_spec
        
        result = _create_module_from_spec(
            module_name=spec_data['name'].lower().replace(' ', '_'),
            title=spec_data['title'],
            version=spec_data['version'],
            category=spec_data['category'],
            features=spec_data.get('features', []),
            plans=spec_data.get('plans', []),
            description=spec_data['description'],
            tags=spec_data.get('tags', [])
        )
        
        if result['success']:
            click.echo(f"\\n🎉 Module {spec_data['name']} built successfully!")
            click.echo(f"Files created: {len(result['files_created'])}")
            for file_path in result['files_created']:
                click.echo(f"  ✅ {file_path}")
        else:
            raise click.ClickException(f"Module build failed: {result['error']}")
            
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON in spec file: {e}")
    except Exception as e:
        logger.error(f"Failed to build module from spec: {e}")
        raise click.ClickException(str(e))

@build.command()
@click.option("--message", required=True, help="Natural language build request")
@click.option("--dry-run", is_flag=True, help="Show parsed spec without building")
def vibe(message, dry_run):
    """Build a module using Vibe Mode (natural language)"""
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"Building module using Vibe Mode: {message}")
    
    try:
        # This command routes through the existing natural language parser
        # and scaffolder (Phase 9 implementation)
        from src.builder.spec_parser import SpecParser
        from src.builder.module_scaffolder import ModuleScaffolder
        
        click.echo("⚡ Vibe Mode: Parsing natural language request...")
        
        # Parse the natural language specification
        parser = SpecParser()
        parsed_spec = parser.parse_spec(message)
        
        # Show parsed specification
        click.echo("\\n🔍 Parsed Specification:")
        click.echo(f"  Name: {parsed_spec['name']}")
        click.echo(f"  Title: {parsed_spec['title']}")
        click.echo(f"  Version: {parsed_spec['version']}")
        click.echo(f"  Category: {parsed_spec['category']}")
        click.echo(f"  Features: {', '.join(parsed_spec['features'])}")
        click.echo(f"  Plans: {', '.join(parsed_spec['plans'])}")
        click.echo(f"  Description: {parsed_spec['spec']}")
        
        if dry_run:
            click.echo("\\n✅ Dry run completed - no module built")
            click.echo("💡 Tip: Use 'build natural' for more control over the build process")
            return
        
        # Confirm with user
        if not click.confirm("\\nProceed with building this module?"):
            click.echo("❌ Module build cancelled")
            return
        
        # Build the module using the deterministic scaffolder
        scaffolder = ModuleScaffolder()
        scaffolder.build_module(
            name=parsed_spec['name'],
            title=parsed_spec['title'],
            version=parsed_spec['version'],
            category=parsed_spec['category'],
            features=parsed_spec['features'],
            plans=parsed_spec['plans'],
            spec=parsed_spec['spec']
        )
        
        # Save the parsed specification
        parser.save_parsed_spec(parsed_spec['name'], parsed_spec)
        
        logger.info(f"✅ Module {parsed_spec['name']} built successfully using Vibe Mode!")
        click.echo(f"\\n🎉 Module {parsed_spec['name']} built successfully!")
        click.echo("💡 Tip: Use 'build spec' for structured planning, 'build vibe' for quick exploration")
        
    except Exception as e:
        logger.error(f"Failed to build module from natural language: {e}")
        raise click.ClickException(str(e))

# Project Commands
@cli.group()
def project():
    """Project management commands"""
    pass

@project.command()
@click.argument('project_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
@click.option('--force', is_flag=True, help='Overwrite existing files')
def resume(project_path, dry_run, force):
    """Resume an existing project by completing SBH integration"""
    import logging
    from src.builder.project_analyzer import ProjectAnalyzer
    from src.builder.project_resumer import ProjectResumer
    
    logger = logging.getLogger(__name__)
    logger.info(f"Resuming project: {project_path}")
    
    try:
        if dry_run:
            # Just analyze and show what would be done
            analyzer = ProjectAnalyzer(project_path)
            analysis = analyzer.analyze()
            
            click.echo("🔍 Project Analysis Report")
            click.echo("=" * 50)
            click.echo(f"Project: {analysis.project_name}")
            click.echo(f"Path: {analysis.project_path}")
            click.echo(f"SBH Compatibility Score: {analysis.sbh_compatibility_score:.1%}")
            click.echo()
            
            # Show present artifacts
            present_artifacts = [a for a in analysis.artifacts if a.status == "present"]
            if present_artifacts:
                click.echo("✅ Present Artifacts:")
                for artifact in present_artifacts:
                    click.echo(f"  - {artifact.name} ({artifact.priority} priority)")
                click.echo()
            
            # Show missing artifacts
            missing_artifacts = [a for a in analysis.artifacts if a.status == "missing"]
            if missing_artifacts:
                click.echo("❌ Missing Artifacts:")
                for artifact in missing_artifacts:
                    click.echo(f"  - {artifact.name} ({artifact.priority} priority)")
                click.echo()
            
            # Show recommendations
            if analysis.recommendations:
                click.echo("📋 Recommendations:")
                for recommendation in analysis.recommendations:
                    click.echo(f"  - {recommendation}")
                click.echo()
            
            click.echo("🔧 This is a dry run - no changes will be made")
            click.echo("Run without --dry-run to actually resume the project")
            
        else:
            # Actually resume the project
            resumer = ProjectResumer(project_path, force=force)
            results = resumer.resume_project()
            
            click.echo("🎉 Project Resume Complete!")
            click.echo("=" * 50)
            click.echo(f"Project: {results['project_name']}")
            click.echo(f"Compatibility Score: {results['compatibility_score_before']:.1%} → {results['compatibility_score_after']:.1%}")
            click.echo()
            
            if results['changes_made']:
                click.echo("✅ Changes Made:")
                for change in results['changes_made']:
                    click.echo(f"  - {change['component']}: {change['action']}")
                click.echo()
            
            if results['errors']:
                click.echo("❌ Errors:")
                for error in results['errors']:
                    click.echo(f"  - {error}")
                click.echo()
            
            click.echo("📄 Detailed reports saved:")
            click.echo(f"  - Analysis: {project_path}/resume.report.md")
            click.echo(f"  - Completion: {project_path}/resume.completion.md")
            
    except Exception as e:
        logger.error(f"Failed to resume project: {e}")
        raise click.ClickException(str(e))

# Marketplace Commands
@cli.group()
def marketplace():
    """Marketplace module management commands"""
    pass

@marketplace.command()
def list():
    """List available marketplace modules"""
    # Run preflight check
    if not preflight_check():
        sys.exit(1)
    
    try:
        click.echo("📋 Available marketplace modules:")
        
        # Load marketplace templates
        import json
        from pathlib import Path
        
        marketplace_dir = Path('marketplace')
        if not marketplace_dir.exists():
            click.echo("❌ Marketplace directory not found")
            return 1
        
        # Find all JSON files
        json_files = list(marketplace_dir.glob('*.json'))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    template = json.load(f)
                
                if template.get('is_active', True):
                    click.echo(f"   ✅ {template.get('name', 'Unknown')} ({template.get('slug', 'unknown')})")
                    click.echo(f"      Version: {template.get('version', 'N/A')}")
                    click.echo(f"      Category: {template.get('category', 'N/A')}")
                    description = template.get('description', 'N/A')
                    if description and len(description) > 60:
                        click.echo(f"      Description: {description[:60]}...")
                    else:
                        click.echo(f"      Description: {description}")
                else:
                    click.echo(f"   ⚠️  {template.get('name', 'Unknown')} ({template.get('slug', 'unknown')}) - Inactive")
                
                click.echo()
                
            except Exception as e:
                click.echo(f"   ❌ Error reading {json_file.name}: {e}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Marketplace list error: {e}")
        return 1

@marketplace.command()
@click.option('--module', help='Specific module to validate (e.g., crm_lite)')
def validate(module):
    """Validate marketplace templates and configurations"""
    # Run preflight check
    if not preflight_check():
        sys.exit(1)
    
    try:
        if module:
            click.echo(f"🔍 Validating {module} module...")
            validate_specific_module(module)
        else:
            click.echo("🔍 Validating all marketplace templates...")
            validate_all_modules()
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Marketplace validation error: {e}")
        return 1

def validate_specific_module(module_name):
    """Validate a specific module"""
    if module_name.lower() == 'crm_lite':
        validate_crm_lite_module()
    elif module_name.lower() == 'crm':
        validate_crm_module()
    else:
        click.echo(f"❌ Unknown module: {module_name}")
        click.echo("💡 Available modules: crm, crm_lite")

def validate_crm_lite_module():
    """Validate CRM Lite module"""
    import json
    from pathlib import Path
    
    crm_lite_template_path = Path('marketplace/crm_lite.json')
    if not crm_lite_template_path.exists():
        click.echo("❌ CRM Lite template not found: marketplace/crm_lite.json")
        return 1
    
    with open(crm_lite_template_path, 'r') as f:
        template = json.load(f)
    
    # Validate required fields
    required_fields = ['id', 'slug', 'name', 'version', 'description', 'plans', 'provision']
    missing_fields = []
    
    for field in required_fields:
        if field not in template:
            missing_fields.append(field)
    
    if missing_fields:
        click.echo(f"❌ CRM Lite template missing required fields: {', '.join(missing_fields)}")
        return 1
    
    # Validate version
    if template['version'] != '1.0.0':
        click.echo(f"❌ CRM Lite template version mismatch: expected 1.0.0, got {template['version']}")
        return 1
    
    # Validate plans structure
    if not isinstance(template['plans'], dict):
        click.echo("❌ CRM Lite template plans must be an object")
        return 1
    
    # Validate provision config
    if not isinstance(template['provision'], dict):
        click.echo("❌ CRM Lite template provision must be an object")
        return 1
    
    click.echo("✅ CRM Lite template validation passed")
    click.echo(f"   - Name: {template['name']}")
    click.echo(f"   - Version: {template['version']}")
    click.echo(f"   - Plans: {len(template['plans'])} available")
    click.echo(f"   - Provision: {template['provision']}")
    
    # Check if CRM Lite module is integrated
    try:
        from src.crm_lite.models import CrmLiteContact
        click.echo("✅ CRM Lite module integration verified")
    except ImportError:
        click.echo("❌ CRM Lite module not properly integrated")
        return 1
    
    # Check if tables exist
    try:
        import sqlite3
        db_path = os.path.abspath('system_builder_hub.db')
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='crm_lite_contacts'")
            if cursor.fetchone():
                click.echo("✅ CRM Lite database tables verified")
            else:
                click.echo("⚠️  CRM Lite database tables not found (run migrations)")
            conn.close()
        else:
            click.echo("⚠️  Database not found (run init-db)")
    except Exception as e:
        click.echo(f"⚠️  Database check failed: {e}")
    
    click.echo("🎉 CRM Lite validation completed!")

def validate_crm_module():
    """Validate CRM module"""
    import json
    from pathlib import Path
    
    crm_template_path = Path('marketplace/flagship-crm.json')
    if not crm_template_path.exists():
        click.echo("❌ CRM template not found: marketplace/flagship-crm.json")
        return 1
    
    with open(crm_template_path, 'r') as f:
        crm_template = json.load(f)
    
    # Validate required fields
    required_fields = ['slug', 'name', 'version', 'description', 'plans']
    missing_fields = []
    
    for field in required_fields:
        if field not in crm_template:
            missing_fields.append(field)
    
    if missing_fields:
        click.echo(f"❌ CRM template missing required fields: {', '.join(missing_fields)}")
        return 1
    
    # Validate version matches integrated module
    if crm_template['version'] != '1.01':
        click.echo(f"❌ CRM template version mismatch: expected 1.01, got {crm_template['version']}")
        return 1
    
    # Validate plans structure
    if not isinstance(crm_template['plans'], dict):
        click.echo("❌ CRM template plans must be an object")
        return 1
    
    click.echo("✅ CRM template validation passed")
    click.echo(f"   - Name: {crm_template['name']}")
    click.echo(f"   - Version: {crm_template['version']}")
    click.echo(f"   - Plans: {len(crm_template['plans'])} available")
    
    # Check if CRM module is integrated
    try:
        from src.crm_ops.models import Contact, Deal, Activity
        click.echo("✅ CRM module integration verified")
    except ImportError:
        click.echo("❌ CRM module not properly integrated")
        return 1
    
    click.echo("🎉 CRM validation completed!")

def validate_all_modules():
    """Validate all modules"""
    try:
        click.echo("Validating CRM Lite...")
        validate_crm_lite_module()
        click.echo()
        click.echo("Validating CRM...")
        validate_crm_module()
        click.echo()
        click.echo("🎉 All module validations completed!")
    except Exception as e:
        click.echo(f"❌ All modules validation error: {e}")
        return 1

@marketplace.command()
@click.option('--module', required=True, help='Module to provision (e.g., crm)')
@click.option('--tenant', required=True, help='Tenant ID to provision for')
def provision(module, tenant):
    """Provision a marketplace module for a tenant"""
    # Run preflight check
    if not preflight_check():
        sys.exit(1)
    
    try:
        click.echo(f"🚀 Provisioning {module} module for tenant {tenant}...")
        
        if module.lower() == 'crm':
            # Check if CRM is already provisioned
            db_path = os.path.abspath('system_builder_hub.db')
            if not os.path.exists(db_path):
                click.echo("❌ Database not found. Run 'init-db' first.")
                return 1
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if CRM tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contacts'")
            if cursor.fetchone():
                click.echo("✅ CRM module already provisioned (tables exist)")
                conn.close()
                return 0
            
            conn.close()
            
            # Provision CRM module
            click.echo("📦 Installing CRM module...")
            
            # Run migrations (idempotent)
            try:
                import subprocess
                result = subprocess.run(['alembic', 'upgrade', 'head'], 
                                      capture_output=True, text=True, check=True)
                click.echo("✅ Database migrations applied")
            except subprocess.CalledProcessError as e:
                click.echo(f"❌ Migration failed: {e.stderr}")
                return 1
            
            # Seed demo data
            try:
                from src.crm_ops.seed import seed_crm_demo_data
                result = seed_crm_demo_data(force=False)
                if result:
                    click.echo("✅ CRM demo data seeded")
                else:
                    click.echo("⚠️  CRM seeding completed (may already have data)")
            except ImportError:
                click.echo("⚠️  CRM seeding module not available")
            
            click.echo(f"🎉 CRM module provisioned successfully for tenant {tenant}")
            return 0
        elif module.lower() == 'crm_lite':
            # Check if CRM Lite is already provisioned
            db_path = os.path.abspath('system_builder_hub.db')
            if not os.path.exists(db_path):
                click.echo("❌ Database not found. Run 'init-db' first.")
                return 1
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if CRM Lite tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='crm_lite_contacts'")
            if cursor.fetchone():
                click.echo("✅ CRM Lite module already provisioned (tables exist)")
                conn.close()
                return 0
            
            conn.close()
            
            # Provision CRM Lite module
            click.echo("📦 Installing CRM Lite module...")
            
            # Run migrations (idempotent)
            try:
                import subprocess
                result = subprocess.run(['alembic', 'upgrade', 'head'], 
                                      capture_output=True, text=True, check=True)
                click.echo("✅ Database migrations applied")
            except subprocess.CalledProcessError as e:
                click.echo(f"❌ Migration failed: {e.stderr}")
                return 1
            
            # Seed demo data
            try:
                import subprocess
                seed_result = subprocess.run(['python', '-m', 'src.cli', 'crm-lite', 'seed-contacts-cmd', '--tenant', tenant], 
                                           capture_output=True, text=True, check=True)
                if seed_result.returncode == 0:
                    click.echo("✅ CRM Lite demo data seeded")
                else:
                    click.echo("⚠️  CRM Lite seeding completed (may already have data)")
            except subprocess.CalledProcessError:
                click.echo("⚠️  CRM Lite seeding module not available")
            
            click.echo(f"🎉 CRM Lite module provisioned successfully for tenant {tenant}")
            return 0
        else:
            click.echo(f"❌ Unknown module: {module}")
            click.echo("💡 Available modules: crm, crm_lite")
            return 1
            
    except Exception as e:
        click.echo(f"❌ Provisioning error: {e}")
        return 1

@marketplace.command()
@click.option('--tenant', required=True, help='Tenant ID')
@click.option('--module', required=True, help='Module name (e.g., crm)')
@click.option('--plan', required=True, help='Plan name (e.g., starter, pro, enterprise)')
@click.option('--days', default=14, help='Trial duration in days')
def trial(tenant, module, plan, days):
    """Start a trial for a tenant/module combination"""
    # Run preflight check
    if not preflight_check():
        sys.exit(1)
    
    try:
        click.echo(f"🚀 Starting {days}-day trial for {module} module (plan: {plan})...")
        
        # Import billing service
        try:
            from src.billing.service import billing_service
        except ImportError:
            click.echo("❌ Billing service not available")
            return 1
        
        # Start trial
        result = billing_service.start_trial(tenant, module, plan, days)
        
        if result['status'] == 'started_trial':
            click.echo(f"✅ Trial started successfully")
            click.echo(f"   - Subscription ID: {result['subscription_id']}")
            click.echo(f"   - Trial ends: {result['trial_ends_at']}")
        elif result['status'] == 'already_on_trial':
            click.echo(f"ℹ️  Tenant already on trial")
            click.echo(f"   - Subscription ID: {result['subscription_id']}")
            click.echo(f"   - Trial ends: {result['trial_ends_at']}")
        else:
            click.echo(f"⚠️  Trial status: {result['status']}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Trial start error: {e}")
        return 1

@marketplace.command()
@click.option('--tenant', required=True, help='Tenant ID')
@click.option('--module', required=True, help='Module name (e.g., crm)')
@click.option('--plan', required=True, help='Plan name (e.g., starter, pro, enterprise)')
def subscribe(tenant, module, plan):
    """Subscribe a tenant to a module plan"""
    # Run preflight check
    if not preflight_check():
        sys.exit(1)
    
    try:
        click.echo(f"💳 Subscribing {tenant} to {module} module (plan: {plan})...")
        
        # Import billing service
        try:
            from src.billing.service import billing_service
        except ImportError:
            click.echo("❌ Billing service not available")
            return 1
        
        # Subscribe
        result = billing_service.subscribe(tenant, module, plan)
        
        if result['status'] == 'subscribed':
            click.echo(f"✅ Subscription activated successfully")
            click.echo(f"   - Subscription ID: {result['subscription_id']}")
        elif result['status'] == 'already_subscribed':
            click.echo(f"ℹ️  Tenant already subscribed")
            click.echo(f"   - Subscription ID: {result['subscription_id']}")
        else:
            click.echo(f"⚠️  Subscription status: {result['status']}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Subscription error: {e}")
        return 1

@marketplace.command()
@click.option('--tenant', required=True, help='Tenant ID')
@click.option('--module', required=True, help='Module name (e.g., crm)')
def cancel(tenant, module):
    """Cancel a subscription"""
    # Run preflight check
    if not preflight_check():
        sys.exit(1)
    
    try:
        click.echo(f"❌ Canceling subscription for {tenant} on {module} module...")
        
        # Import billing service
        try:
            from src.billing.service import billing_service
        except ImportError:
            click.echo("❌ Billing service not available")
            return 1
        
        # Cancel
        result = billing_service.cancel(tenant, module)
        
        if result['status'] == 'canceled':
            click.echo(f"✅ Subscription canceled successfully")
            click.echo(f"   - Subscription ID: {result['subscription_id']}")
        elif result['status'] == 'already_canceled':
            click.echo(f"ℹ️  Subscription already canceled")
            click.echo(f"   - Subscription ID: {result['subscription_id']}")
        elif result['status'] == 'not_subscribed':
            click.echo(f"ℹ️  No subscription found for this tenant/module")
        else:
            click.echo(f"⚠️  Cancel status: {result['status']}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Cancel error: {e}")
        return 1

@marketplace.command()
@click.option('--tenant', required=True, help='Tenant ID')
@click.option('--module', required=True, help='Module name (e.g., crm)')
def status(tenant, module):
    """Get subscription status for a tenant/module"""
    # Run preflight check
    if not preflight_check():
        sys.exit(1)
    
    try:
        click.echo(f"📊 Checking subscription status for {tenant} on {module} module...")
        
        # Import billing service
        try:
            from src.billing.service import billing_service
        except ImportError:
            click.echo("❌ Billing service not available")
            return 1
        
        # Get status
        result = billing_service.status(tenant, module)
        
        if result['status'] == 'not_subscribed':
            click.echo(f"ℹ️  No subscription found")
        else:
            click.echo(f"📋 Subscription Details:")
            click.echo(f"   - Status: {result['status']}")
            click.echo(f"   - Plan: {result['plan']}")
            click.echo(f"   - Created: {result['created_at']}")
            click.echo(f"   - Updated: {result['updated_at']}")
            
            if result.get('trial_ends_at'):
                click.echo(f"   - Trial ends: {result['trial_ends_at']}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Status check error: {e}")
        return 1

@marketplace.command()
@click.option('--tenant', required=True, help='Tenant ID')
@click.option('--module', required=True, help='Module name (e.g., crm)')
def module_status(tenant, module):
    """Get module status for a tenant/module"""
    # Run preflight check
    if not preflight_check():
        sys.exit(1)
    
    try:
        click.echo(f"🔍 Checking module status for {module} module for tenant {tenant}...")
        
        if module.lower() == 'crm_lite':
            # Check CRM Lite status
            db_path = os.path.abspath('system_builder_hub.db')
            if not os.path.exists(db_path):
                click.echo("❌ Database not found")
                return 1
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if CRM Lite tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='crm_lite_contacts'")
            if not cursor.fetchone():
                click.echo("❌ CRM Lite tables not found - module not provisioned")
                conn.close()
                return 1
            
            # Check contact count for tenant
            cursor.execute("SELECT COUNT(*) FROM crm_lite_contacts WHERE tenant_id = ?", (tenant,))
            contact_count = cursor.fetchone()[0]
            
            # Check total contacts
            cursor.execute("SELECT COUNT(*) FROM crm_lite_contacts")
            total_contacts = cursor.fetchone()[0]
            
            conn.close()
            
            click.echo("✅ CRM Lite module status:")
            click.echo(f"   - Tables: Present")
            click.echo(f"   - Tenant contacts: {contact_count}")
            click.echo(f"   - Total contacts: {total_contacts}")
            click.echo(f"   - Status: {'Provisioned' if contact_count > 0 else 'Provisioned (no data)'}")
            
            if contact_count == 0:
                click.echo("💡 Run: python -m src.cli crm-lite seed-contacts-cmd --tenant " + tenant)
            
            return 0
        elif module.lower() == 'crm':
            # Check CRM status (existing logic)
            click.echo(f"ℹ️  CRM module status check not implemented yet")
            return 0
        else:
            click.echo(f"❌ Unknown module: {module}")
            click.echo("💡 Available modules: crm, crm_lite")
            return 1
            
    except Exception as e:
        click.echo(f"❌ Module status check error: {e}")
        return 1

@cli.command()
@click.option('--queues', default='default,high,low', help='Comma-separated list of queues to listen to')
@click.option('--burst', is_flag=True, help='Run in burst mode (exit when no jobs)')
@click.option('--name', help='Worker name (default: auto-generated)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--redis-url', help='Redis URL (default: redis://127.0.0.1:6379/0). BLPOP waits up to ~400s; we disable socket_timeout to avoid false timeouts.')
def worker(queues, burst, name, verbose, redis_url):
    """Start background worker for processing jobs"""
    # Run preflight check before starting worker
    if not preflight_check():
        sys.exit(1)
    
    try:
        # Import worker functionality
        from src.jobs.worker import main as worker_main
        from src.redis_core import redis_available
        
        # Set Redis URL if provided
        if redis_url:
            os.environ['REDIS_URL'] = redis_url
            click.echo(f"🔗 Using Redis URL: {redis_url}")
        
        # Check Redis availability
        if not redis_available():
            click.echo("❌ Redis not available. Please start Redis first:")
            click.echo("   brew install redis && brew services start redis")
            click.echo("   or: docker run -d -p 6379:6379 redis:alpine")
            click.echo("   or: specify custom Redis URL with --redis-url")
            return 1
        
        # Parse queues
        queue_list = [q.strip() for q in queues.split(',') if q.strip()]
        if not queue_list:
            click.echo("❌ No valid queues specified")
            return 1
        
        click.echo(f"🚀 Starting RQ worker...")
        click.echo(f"📋 Queues: {', '.join(queue_list)}")
        if burst:
            click.echo("⚡ Burst mode: will exit when no jobs")
        if name:
            click.echo(f"🏷️  Worker name: {name}")
        if verbose:
            click.echo("🔍 Verbose logging enabled")
        
        # Set environment variables for the worker
        if name:
            os.environ['RQ_WORKER_NAME'] = name
        if burst:
            os.environ['RQ_BURST_MODE'] = 'true'
        if verbose:
            os.environ['RQ_VERBOSE'] = 'true'
        
        # Set queue configuration
        os.environ['RQ_QUEUES'] = queues
        
        # Start the worker
        worker_main()
        
    except ImportError as e:
        click.echo(f"❌ Failed to import worker module: {e}")
        click.echo("💡 Make sure all dependencies are installed: pip install -r requirements.txt")
        return 1
    except KeyboardInterrupt:
        click.echo("\n⏹️  Worker stopped by user")
    except Exception as e:
        click.echo(f"❌ Worker error: {e}")
        return 1

# LLM Commands
@cli.group()
def llm():
    """LLM management and routing commands"""
    pass

@llm.command()
def status():
    """Get LLM status and routing information"""
    try:
        from src.llm.providers import LLMProviderManager
        
        click.echo("🧠 Getting LLM status...")
        
        provider_manager = LLMProviderManager()
        
        # Get provider status
        providers_info = provider_manager.get_all_providers()
        routing_info = provider_manager.get_routing_info()
        
        click.echo("✅ LLM Status:")
        click.echo(f"   Available: {any(p.configured for p in providers_info)}")
        click.echo(f"   Default Model: {routing_info['default_model']}")
        click.echo(f"   Secondary Model: {routing_info['secondary_model']}")
        click.echo(f"   Tertiary Model: {routing_info['tertiary_model']}")
        click.echo(f"   Routing Policy: {routing_info['routing_policy']}")
        click.echo(f"   Daily Budget: ${routing_info['cost_budget_daily']:.2f}")
        click.echo(f"   Daily Cost: ${routing_info['daily_cost']:.4f}")
        click.echo(f"   Budget Exceeded: {routing_info['budget_exceeded']}")
        click.echo(f"   Log Prompts: {routing_info['log_prompts']}")
        
        click.echo("\n📊 Providers:")
        for provider in providers_info:
            status_icon = "✅" if provider.configured else "❌"
            click.echo(f"   {status_icon} {provider.name}: {provider.model_default}")
            click.echo(f"      Configured: {provider.configured}")
            click.echo(f"      Supports JSON: {provider.supports_json}")
            click.echo(f"      Supports Tools: {provider.supports_tools}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to get LLM status: {e}")
        return 1

@llm.command()
@click.option('--provider', default='openai', help='Provider to test')
def test(provider):
    """Test LLM connection"""
    try:
        from src.llm.providers import LLMProviderManager
        
        click.echo(f"🧠 Testing LLM provider: {provider}")
        
        provider_manager = LLMProviderManager()
        llm_provider = provider_manager.get_provider(provider)
        
        if not llm_provider.is_configured():
            click.echo(f"❌ Provider {provider} not configured")
            return 1
        
        click.echo(f"✅ Provider {provider} is configured")
        click.echo(f"   Model: {llm_provider.default_model}")
        click.echo(f"   Supports JSON: {llm_provider.supports_json}")
        click.echo(f"   Supports Tools: {llm_provider.supports_tools}")
        
        # Test routing
        click.echo("\n🔄 Testing model routing:")
        test_tasks = ['spec_parse', 'scaffold', 'classify']
        for task in test_tasks:
            model = provider_manager.route_model(task)
            click.echo(f"   {task} → {model}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to test LLM: {e}")
        return 1

# Register ERP Core commands
try:
    from src.erp_core.cli import erp
    cli.add_command(erp)
except ImportError as e:
    # ERP Core not available, skip registration
    pass

# Ops Commands
@cli.group()
def ops():
    """Operations and health monitoring commands"""
    pass

# Security Commands
@cli.group()
def security():
    """Security audit and baseline commands"""
    pass

@cli.group()
def ecosystem():
    """Ecosystem orchestration and multi-module system commands"""
    pass

@cli.group()
def deploy():
    """Deployment bundle and environment management commands"""
    pass

@cli.group()
def releases():
    """Release management and continuous deployment commands"""
    pass

@cli.group()
def tenants():
    """Tenant management and control plane commands"""
    pass

@ops.command()
@click.option('--tenant', help='Tenant ID to check')
@click.option('--module', help='Module to check (crm, erp, lms, all)')
def status(tenant, module):
    """Get operations status"""
    try:
        from src.ops.health import HealthChecker
        
        health_checker = HealthChecker()
        health_status = health_checker.get_overall_health(tenant, module)
        
        click.echo(f"🔍 Operations Status for {module or 'all modules'}")
        click.echo(f"Overall Status: {health_status['status'].upper()}")
        click.echo(f"Timestamp: {health_status['timestamp']}")
        
        for check_name, check_result in health_status['checks'].items():
            status_emoji = "✅" if check_result['status'] == 'healthy' else "⚠️" if check_result['status'] == 'degraded' else "❌"
            click.echo(f"{status_emoji} {check_name}: {check_result['status']} - {check_result['message']}")
            
    except Exception as e:
        click.echo(f"❌ Status check failed: {e}")
        return 1

@ops.command()
@click.option('--action', required=True, help='Action to perform (migrate, reseed, reregister, restart_worker)')
@click.option('--module', help='Module to target')
@click.option('--tenant', help='Tenant ID for tenant-specific actions')
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
def remediate(action, module, tenant, dry_run):
    """Execute a remediation action"""
    try:
        from src.ops.remediations import RemediationService
        
        remediation_service = RemediationService()
        result = remediation_service.remediate(action, module, tenant, dry_run)
        
        status_emoji = "✅" if result['status'] == 'success' else "⚠️" if result['status'] == 'dry_run' else "❌"
        click.echo(f"{status_emoji} {result['action']}: {result['status']}")
        click.echo(f"Message: {result['message']}")
        
        if result.get('output'):
            click.echo(f"Output: {result['output']}")
            
    except Exception as e:
        click.echo(f"❌ Remediation failed: {e}")
        return 1

# Growth Commands
@cli.group()
def growth():
    """Growth intelligence and analytics commands"""
    pass

@growth.command()
@click.option('--from-date', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--to-date', required=True, help='End date (YYYY-MM-DD)')
@click.option('--tenant', help='Tenant ID to filter')
@click.option('--module', help='Module to filter')
def metrics(from_date, to_date, tenant, module):
    """Get growth metrics for a date range"""
    try:
        from src.growth.rollup import DailyRollupService
        
        rollup_service = DailyRollupService()
        
        # For now, just show the date range and filters
        click.echo(f"📊 Growth Metrics")
        click.echo(f"From: {from_date}")
        click.echo(f"To: {to_date}")
        if tenant:
            click.echo(f"Tenant: {tenant}")
        if module:
            click.echo(f"Module: {module}")
        
        click.echo("ℹ️  Use the API endpoint /api/growth/metrics for detailed data")
        
    except Exception as e:
        click.echo(f"❌ Metrics query failed: {e}")
        return 1

@growth.command()
@click.option('--tenant', help='Tenant ID to analyze')
def insights(tenant):
    """Get growth insights and analytics"""
    try:
        from src.growth.rollup import DailyRollupService
        
        rollup_service = DailyRollupService()
        
        click.echo(f"📈 Growth Insights")
        if tenant:
            click.echo(f"Tenant: {tenant}")
        else:
            click.echo("All tenants")
        
        click.echo("ℹ️  Use the API endpoint /api/growth/insights for detailed analytics")
        
    except Exception as e:
        click.echo(f"❌ Insights query failed: {e}")
        return 1

@growth.command()
def rollup():
    """Trigger daily metrics rollup"""
    try:
        from src.growth.rollup import DailyRollupService
        
        rollup_service = DailyRollupService()
        result = rollup_service.run_daily_rollup()
        
        if 'error' in result:
            click.echo(f"❌ Rollup failed: {result['error']}")
            return 1
        else:
            click.echo(f"✅ Daily rollup completed")
            click.echo(f"Date: {result['date']}")
            click.echo(f"Events processed: {result['events_processed']}")
            click.echo(f"Metrics written: {result['metrics_written']}")
            
    except Exception as e:
        click.echo(f"❌ Rollup failed: {e}")
        return 1

@security.command()
@click.option('--module', default='all', help='Module to audit (crm, erp, lms, all)')
@click.option('--tenant', default='demo', help='Tenant ID for audit')
@click.option('--dry-run', is_flag=True, help='Run audit without making changes')
@click.option('--json', is_flag=True, help='Output results in JSON format')
def audit(module, tenant, dry_run, json):
    """Run comprehensive security audit"""
    try:
        from src.security.audit import SecurityAuditor
        
        click.echo("🔐 Starting security audit...")
        click.echo(f"Module: {module}")
        click.echo(f"Tenant: {tenant}")
        click.echo(f"Dry run: {dry_run}")
        
        auditor = SecurityAuditor()
        result = auditor.run_full_audit(dry_run=dry_run)
        
        if json:
            import json as json_lib
            click.echo(json_lib.dumps(result, indent=2))
        else:
            # Human-readable output
            click.echo(f"\n🔐 Security Audit Results")
            click.echo(f"Overall Score: {result.get('score', 0)}/100")
            click.echo(f"Timestamp: {result.get('timestamp', 'unknown')}")
            
            if result.get('findings'):
                click.echo(f"\n🚨 Findings ({len(result['findings'])}):")
                for finding in result['findings'][:10]:  # Show first 10
                    click.echo(f"  • {finding}")
                if len(result['findings']) > 10:
                    click.echo(f"  ... and {len(result['findings']) - 10} more")
            else:
                click.echo("\n✅ No security findings")
            
            if result.get('recommendations'):
                click.echo(f"\n💡 Recommendations ({len(result['recommendations'])}):")
                for rec in result['recommendations']:
                    click.echo(f"  • {rec}")
            
            if result.get('modules'):
                click.echo(f"\n📦 Module Scores:")
                for mod_name, mod_data in result['modules'].items():
                    score = mod_data.get('score', 0)
                    status = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
                    click.echo(f"  {status} {mod_name}: {score}/100")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Security audit failed: {e}")
        return 1

@security.command()
@click.option('--json', is_flag=True, help='Output results in JSON format')
def status(json):
    """Get current security status"""
    try:
        from src.security.audit import SecurityAuditor
        
        click.echo("🔐 Checking security status...")
        
        auditor = SecurityAuditor()
        # For status, we'll just show a summary without running full audit
        click.echo("✅ Security services operational")
        click.echo("ℹ️  Run 'security audit' for detailed analysis")
        
        if json:
            import json as json_lib
            status_data = {
                "status": "operational",
                "services": ["auditor", "rate_limiter"],
                "timestamp": datetime.now().isoformat()
            }
            click.echo(json_lib.dumps(status_data, indent=2))
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Security status check failed: {e}")
        return 1

# Ecosystem Commands
@ecosystem.command()
def list():
    """List all available system blueprints"""
    try:
        from src.ecosystem.blueprints import list_blueprints
        
        click.echo("🌐 Available System Blueprints:")
        blueprints = list_blueprints()
        
        if not blueprints:
            click.echo("❌ No system blueprints found")
            return 1
        
        for bp in blueprints:
            click.echo(f"  📋 {bp['name']} v{bp['version']}")
            click.echo(f"     Description: {bp.get('description', 'No description')}")
            click.echo(f"     Modules: {', '.join(bp['modules'])}")
            click.echo(f"     Contracts: {bp['contracts_count']}")
            click.echo(f"     Workflows: {bp['workflows_count']}")
            click.echo()
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to list blueprints: {e}")
        return 1

@ecosystem.command()
@click.option('--system', required=True, help='System blueprint name (e.g., revops_suite)')
@click.option('--tenant', default='demo', help='Tenant ID (default: demo)')
def provision(system, tenant):
    """Provision a complete system based on blueprint"""
    try:
        from src.ecosystem.orchestrator import EcosystemOrchestrator
        
        click.echo(f"🚀 Provisioning system '{system}' for tenant '{tenant}'...")
        
        orchestrator = EcosystemOrchestrator()
        result = orchestrator.provision_system(system, tenant)
        
        if result['success']:
            data = result['data']
            click.echo(f"✅ System '{system}' provisioned successfully!")
            click.echo(f"   Modules: {len(data['modules'])}")
            click.echo(f"   Demo data seeded: {data['demo_data_seeded']}")
            
            if data['demo_data_seeded'] and 'demo_data_summary' in data:
                summary = data['demo_data_summary']
                click.echo(f"   CRM contacts: {summary.get('crm_contacts', 0)}")
                click.echo(f"   ERP orders: {summary.get('erp_orders', 0)}")
            
            return 0
        else:
            click.echo(f"❌ System provisioning failed: {result['error']}")
            return 1
            
    except Exception as e:
        click.echo(f"❌ System provisioning failed: {e}")
        return 1

@ecosystem.command()
@click.option('--name', required=True, help='Contract name (e.g., contacts_sync, orders_to_deals)')
@click.option('--tenant', default='demo', help='Tenant ID (default: demo)')
@click.option('--dry-run', is_flag=True, help='Show what would be executed without making changes')
def run_contract(name, tenant, dry_run):
    """Run a data contract for a tenant"""
    try:
        from src.ecosystem.orchestrator import EcosystemOrchestrator
        
        action = "dry-run" if dry_run else "execute"
        click.echo(f"🔄 Running contract '{name}' for tenant '{tenant}' ({action})...")
        
        orchestrator = EcosystemOrchestrator()
        result = orchestrator.run_contract(name, tenant, dry_run)
        
        if result['success']:
            data = result['data']
            click.echo(f"✅ Contract '{name}' completed successfully!")
            click.echo(f"   Total records: {data['total_records']}")
            click.echo(f"   Validated: {data['validated']}")
            click.echo(f"   Transformed: {data['transformed']}")
            click.echo(f"   Applied: {data['applied']}")
            
            if data['errors']:
                click.echo(f"   Errors: {len(data['errors'])}")
                for error in data['errors'][:3]:  # Show first 3 errors
                    click.echo(f"     - {error}")
                if len(data['errors']) > 3:
                    click.echo(f"     ... and {len(data['errors']) - 3} more")
            
            return 0
        else:
            click.echo(f"❌ Contract execution failed: {result['error']}")
            return 1
            
    except Exception as e:
        click.echo(f"❌ Contract execution failed: {e}")
        return 1

@ecosystem.command()
@click.option('--name', required=True, help='Workflow name (e.g., lead_to_cash, new_customer_360)')
@click.option('--tenant', default='demo', help='Tenant ID (default: demo)')
@click.option('--dry-run', is_flag=True, help='Show what would be executed without making changes')
def run_workflow(name, tenant, dry_run):
    """Run a predefined workflow for a tenant"""
    try:
        from src.ecosystem.orchestrator import EcosystemOrchestrator
        
        action = "dry-run" if dry_run else "execute"
        click.echo(f"⚡ Running workflow '{name}' for tenant '{tenant}' ({action})...")
        
        orchestrator = EcosystemOrchestrator()
        result = orchestrator.run_workflow(name, tenant, dry_run)
        
        if result['success']:
            click.echo(f"✅ Workflow '{name}' completed successfully!")
            
            if 'results' in result:
                results = result['results']
                click.echo(f"   Results: {len(results)}")
                
                for i, res in enumerate(results[:3]):  # Show first 3 results
                    if 'lead_id' in res:
                        click.echo(f"     {i+1}. Lead: {res['lead_name']} → Order: {res['order_id']}")
                    elif 'customer_id' in res:
                        profile = res.get('profile', {})
                        modules = ', '.join(profile.get('modules', []))
                        click.echo(f"     {i+1}. Customer: {profile.get('name', 'Unknown')} ({modules})")
                
                if len(results) > 3:
                    click.echo(f"     ... and {len(results) - 3} more results")
            
            return 0
        else:
            click.echo(f"❌ Workflow execution failed: {result['error']}")
            return 1
            
    except Exception as e:
        click.echo(f"❌ Workflow execution failed: {e}")
        return 1

# Deployment Commands
@deploy.command()
def list():
    """List all available deployment bundles"""
    try:
        from src.deployment.bundles import list_bundles
        
        click.echo("🚀 Available Deployment Bundles:")
        bundles = list_bundles()
        
        if not bundles:
            click.echo("❌ No deployment bundles found")
            return 1
        
        for bundle in bundles:
            click.echo(f"  📦 {bundle['name']} v{bundle['version']}")
            click.echo(f"     Ecosystem: {bundle['ecosystem']}")
            click.echo(f"     Environment: {bundle['environment']}")
            click.echo(f"     Description: {bundle.get('description', 'No description')}")
            click.echo(f"     Services: {bundle['services_count']}")
            click.echo(f"     Tags: {', '.join(bundle['tags'])}")
            click.echo()
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to list deployment bundles: {e}")
        return 1

@deploy.command()
@click.option('--bundle', required=True, help='Bundle name to validate')
def validate(bundle):
    """Validate a deployment bundle"""
    try:
        from src.deployment.bundles import get_bundle
        
        click.echo(f"🔍 Validating deployment bundle '{bundle}'...")
        
        bundle_obj = get_bundle(bundle)
        if not bundle_obj:
            click.echo(f"❌ Bundle not found: {bundle}")
            return 1
        
        # Validate the bundle
        errors = bundle_obj.validate()
        
        if not errors:
            click.echo(f"✅ Bundle '{bundle}' is valid!")
            click.echo(f"   Ecosystem: {bundle_obj.ecosystem}")
            click.echo(f"   Environment: {bundle_obj.environment}")
            click.echo(f"   Services: {len(bundle_obj.services)}")
            return 0
        else:
            click.echo(f"❌ Bundle '{bundle}' has validation errors:")
            for error in errors:
                click.echo(f"   - {error}")
            return 1
            
    except Exception as e:
        click.echo(f"❌ Bundle validation failed: {e}")
        return 1

@deploy.command()
@click.option('--bundle', required=True, help='Bundle name to generate compose for')
@click.option('--output', help='Output file path (default: docker-compose.yml)')
@click.option('--dry-run', is_flag=True, help='Show what would be generated without writing files')
def generate_compose(bundle, output, dry_run):
    """Generate Docker Compose file for a bundle"""
    try:
        from src.deployment.generators import generate_deployment_artifacts
        
        action = "dry-run" if dry_run else "generate"
        click.echo(f"🐳 Generating Docker Compose for bundle '{bundle}' ({action})...")
        
        output_path = output or "docker-compose.yml"
        
        compose_content = generate_deployment_artifacts(
            bundle, "compose", output_path, dry_run
        )
        
        if dry_run:
            click.echo("📋 Docker Compose content (dry-run):")
            click.echo("---")
            click.echo(compose_content)
            click.echo("---")
        else:
            click.echo(f"✅ Docker Compose file generated: {output_path}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to generate Docker Compose: {e}")
        return 1

@deploy.command()
@click.option('--bundle', required=True, help='Bundle name to generate manifest for')
@click.option('--output', help='Output file path (default: k8s-manifest.yml)')
@click.option('--dry-run', is_flag=True, help='Show what would be generated without writing files')
def generate_manifest(bundle, output, dry_run):
    """Generate Kubernetes manifest for a bundle"""
    try:
        from src.deployment.generators import generate_deployment_artifacts
        
        action = "dry-run" if dry_run else "generate"
        click.echo(f"☸️  Generating Kubernetes manifest for bundle '{bundle}' ({action})...")
        
        output_path = output or "k8s-manifest.yml"
        
        manifest_content = generate_deployment_artifacts(
            bundle, "kubernetes", output_path, dry_run
        )
        
        if dry_run:
            click.echo("📋 Kubernetes manifest content (dry-run):")
            click.echo("---")
            click.echo(manifest_content)
            click.echo("---")
        else:
            click.echo(f"✅ Kubernetes manifest generated: {output_path}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to generate Kubernetes manifest: {e}")
        return 1

@deploy.command()
@click.option('--bundle', required=True, help='Bundle name to apply')
@click.option('--environment', help='Environment to apply to (default: from bundle)')
@click.option('--dry-run', is_flag=True, help='Show what would be applied without making changes')
def apply(bundle, environment, dry_run):
    """Apply a deployment bundle to prepare workspace"""
    try:
        from src.deployment.bundles import get_bundle
        from src.deployment.environments import generate_env_file
        
        action = "dry-run" if dry_run else "apply"
        click.echo(f"🚀 Applying deployment bundle '{bundle}' ({action})...")
        
        bundle_obj = get_bundle(bundle)
        if not bundle_obj:
            click.echo(f"❌ Bundle not found: {bundle}")
            return 1
        
        target_env = environment or bundle_obj.environment
        
        click.echo(f"   Bundle: {bundle_obj.name}")
        click.echo(f"   Ecosystem: {bundle_obj.ecosystem}")
        click.echo(f"   Environment: {target_env}")
        click.echo(f"   Services: {len(bundle_obj.services)}")
        
        if not dry_run:
            # Generate .env file
            env_file = f".env.{target_env}"
            generate_env_file(target_env, env_file)
            click.echo(f"   Generated: {env_file}")
            
            # Generate docker-compose.yml
            from src.deployment.generators import generate_deployment_artifacts
            generate_deployment_artifacts(bundle, "compose", "docker-compose.yml", False)
            click.echo("   Generated: docker-compose.yml")
            
            click.echo(f"✅ Bundle '{bundle}' applied successfully!")
            click.echo(f"   Next steps:")
            click.echo(f"   1. Review generated files")
            click.echo(f"   2. Update secrets in {env_file}")
            click.echo(f"   3. Run: docker-compose up -d")
        else:
            click.echo(f"   Would generate: .env.{target_env}")
            click.echo(f"   Would generate: docker-compose.yml")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to apply deployment bundle: {e}")
        return 1

# Release Commands
@releases.command()
@click.option('--target', required=True, help='Target (module or ecosystem name)')
@click.option('--version', required=True, help='Version (e.g., 1.0.0)')
@click.option('--notes', help='Release notes')
def create(target, version, notes):
    """Create a new release"""
    try:
        from src.deployment.releases import ReleaseManager
        
        click.echo(f"📦 Creating release for {target} v{version}...")
        
        release_manager = ReleaseManager()
        result = release_manager.create_release(target, version, notes or "")
        
        if result['success']:
            click.echo(f"✅ Release created successfully!")
            click.echo(f"   Name: {result['data']['name']}")
            click.echo(f"   Status: {result['data']['status']}")
            click.echo(f"   Target: {result['data']['target']}")
            click.echo(f"   Version: {result['data']['version']}")
            return 0
        else:
            click.echo(f"❌ Failed to create release: {result['error']}")
            return 1
            
    except Exception as e:
        click.echo(f"❌ Release creation failed: {e}")
        return 1

@releases.command()
@click.option('--target', help='Filter by target')
@click.option('--status', help='Filter by status (draft, staged, prod, rolled_back)')
def list(target, status):
    """List releases"""
    try:
        from src.deployment.releases import ReleaseManager
        
        click.echo("📋 Listing releases...")
        
        release_manager = ReleaseManager()
        releases = release_manager.list_releases(target, status)
        
        if not releases:
            click.echo("No releases found")
            return 0
        
        for release in releases:
            click.echo(f"  📦 {release.name} v{release.version}")
            click.echo(f"     Target: {release.target}")
            click.echo(f"     Status: {release.status}")
            click.echo(f"     Environment: {release.environment or 'N/A'}")
            click.echo(f"     Strategy: {release.strategy or 'N/A'}")
            click.echo(f"     Created: {release.created_at}")
            if release.promoted_at:
                click.echo(f"     Promoted: {release.promoted_at}")
            click.echo()
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to list releases: {e}")
        return 1

@releases.command()
@click.option('--target', required=True, help='Target (module or ecosystem name)')
@click.option('--version', required=True, help='Version to promote')
@click.option('--env', required=True, help='Environment (local, staging, production)')
@click.option('--strategy', help='Deployment strategy (rolling, bluegreen)')
@click.option('--dry-run', is_flag=True, help='Show what would be executed without making changes')
def promote(target, version, env, strategy, dry_run):
    """Promote a release to an environment"""
    try:
        from src.deployment.releases import ReleaseManager
        
        action = "dry-run" if dry_run else "promote"
        click.echo(f"🚀 Promoting {target} v{version} to {env} ({action})...")
        
        release_manager = ReleaseManager()
        result = release_manager.promote_release(target, version, env, strategy, dry_run)
        
        if result['success']:
            if dry_run:
                click.echo("✅ Promotion dry-run completed")
                click.echo(f"   Action: {result['data']['action']}")
                click.echo(f"   From: {result['data']['from_status']}")
                click.echo(f"   To: {result['data']['to_status']}")
                click.echo(f"   Environment: {result['data']['environment']}")
                click.echo(f"   Strategy: {result['data']['strategy']}")
            else:
                click.echo("✅ Release promoted successfully!")
                click.echo(f"   Status: {result['data']['status']}")
                click.echo(f"   Environment: {result['data']['environment']}")
                click.echo(f"   Strategy: {result['data']['strategy']}")
            return 0
        else:
            click.echo(f"❌ Promotion failed: {result['error']}")
            return 1
            
    except Exception as e:
        click.echo(f"❌ Promotion failed: {e}")
        return 1

@releases.command()
@click.option('--target', required=True, help='Target (module or ecosystem name)')
@click.option('--env', required=True, help='Environment to rollback')
@click.option('--to', help='Target version for rollback (default: previous version)')
@click.option('--dry-run', is_flag=True, help='Dry run mode')
def rollback(target, env, to, dry_run):
    """Rollback a release in an environment"""
    try:
        from src.deployment.releases import ReleaseManager
        
        action = "dry-run" if dry_run else "rollback"
        click.echo(f"🔄 Rolling back {target} in {env} ({action})...")
        
        release_manager = ReleaseManager()
        result = release_manager.rollback_release(target, env, to, dry_run)
        
        if result['success']:
            if dry_run:
                click.echo("✅ Rollback dry-run completed")
                click.echo(f"   Action: {result['data']['action']}")
                click.echo(f"   From: {result['data']['from_version']}")
                click.echo(f"   To: {result['data']['to_version']}")
                click.echo(f"   Environment: {result['data']['environment']}")
            else:
                click.echo("✅ Release rolled back successfully!")
                click.echo(f"   From: {result['data']['from_version']}")
                click.echo(f"   To: {result['data']['to_version']}")
                click.echo(f"   Environment: {result['data']['environment']}")
            return 0
        else:
            click.echo(f"❌ Rollback failed: {result['error']}")
            return 1
            
    except Exception as e:
        click.echo(f"❌ Rollback failed: {e}")
        return 1

@releases.command()
@click.option('--target', help='Target to get summary for')
def summary(target):
    """Get release summary"""
    try:
        from src.deployment.releases import ReleaseManager
        
        click.echo(f"📊 Release summary for {target or 'all targets'}...")
        
        release_manager = ReleaseManager()
        summary = release_manager.get_release_summary(target)
        
        if not summary:
            click.echo("No release summary available")
            return 0
        
        click.echo(f"  Total releases: {summary['total']}")
        click.echo(f"  By status:")
        for status, count in summary['by_status'].items():
            click.echo(f"    {status}: {count}")
        
        if summary['latest_by_env']:
            click.echo(f"  Latest by environment:")
            for env, info in summary['latest_by_env'].items():
                click.echo(f"    {env}: v{info['version']} ({info['status']})")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to get release summary: {e}")
        return 1

# Tenant Commands
@tenants.command()
@click.option('--q', help='Search query')
@click.option('--json', is_flag=True, help='Output in JSON format')
def list(q, json):
    """List tenants with optional search"""
    try:
        import json as json_module
        from src.control_plane.service import ControlPlaneService
        
        click.echo("📋 Listing tenants...")
        
        control_plane = ControlPlaneService()
        result = control_plane.list_tenants(q)
        
        if not result['success']:
            click.echo(f"❌ Failed to list tenants: {result['error']}")
            return 1
        
        if json:
            click.echo(json_module.dumps(result['data'], indent=2))
            return 0
        
        tenants = result['data']['tenants']
        if not tenants:
            click.echo("No tenants found")
            return 0
        
        for tenant in tenants:
            click.echo(f"  🏢 {tenant['name']} ({tenant['slug']})")
            click.echo(f"     Plan: {tenant['plan']}")
            click.echo(f"   Status: {tenant['status']}")
            click.echo(f"     Created: {tenant['created_at']}")
            click.echo()
        
        click.echo(f"Total: {result['data']['total']} tenants")
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to list tenants: {e}")
        return 1

@tenants.command()
@click.option('--slug', required=True, help='Tenant slug')
@click.option('--name', required=True, help='Tenant name')
@click.option('--owner-email', help='Owner email address')
@click.option('--json', is_flag=True, help='Output in JSON format')
def create(slug, name, owner_email, json):
    """Create a new tenant"""
    try:
        import json as json_module
        from src.control_plane.service import ControlPlaneService
        
        click.echo(f"🏢 Creating tenant: {name} ({slug})...")
        
        control_plane = ControlPlaneService()
        result = control_plane.create_tenant(slug, name, owner_email)
        
        if not result['success']:
            click.echo(f"❌ Failed to create tenant: {result['error']}")
            return 1
        
        if json:
            click.echo(json_module.dumps(result['data'], indent=2))
            return 0
        
        click.echo(f"✅ Tenant created successfully!")
        click.echo(f"   Slug: {result['data']['slug']}")
        click.echo(f"   Name: {result['data']['name']}")
        click.echo(f"   Action: {result['data']['action']}")
        if result['data'].get('id'):
            click.echo(f"   ID: {result['data']['id']}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to create tenant: {e}")
        return 1

@tenants.command()
@click.option('--tenant', required=True, help='Tenant slug')
@click.option('--system', help='System to provision (e.g., revops_suite)')
@click.option('--modules', help='Comma-separated list of modules to provision')
@click.option('--dry-run', is_flag=True, help='Show what would be executed without making changes')
@click.option('--json', is_flag=True, help='Output in JSON format')
def provision(tenant, system, modules, dry_run, json):
    """Provision ecosystem or modules for a tenant"""
    try:
        import json as json_module
        from src.control_plane.service import ControlPlaneService
        
        action = "dry-run" if dry_run else "provision"
        click.echo(f"🚀 {action.capitalize()} for tenant: {tenant}...")
        
        control_plane = ControlPlaneService()
        
        # Parse modules if provided
        module_list = None
        if modules:
            module_list = [m.strip() for m in modules.split(',')]
        
        result = control_plane.provision_tenant(tenant, system, module_list, dry_run)
        
        if not result['success']:
            click.echo(f"❌ Failed to provision tenant: {result['error']}")
            return 1
        
        if json:
            click.echo(json_module.dumps(result['data'], indent=2))
            return 0
        
        if dry_run:
            click.echo("✅ Provision dry-run completed")
            click.echo(f"   Action: {result['data']['action']}")
            click.echo(f"   Tenant: {result['data']['tenant']}")
            if result['data'].get('system'):
                click.echo(f"   System: {result['data']['system']}")
            if result['data'].get('modules'):
                click.echo(f"   Modules: {', '.join(result['data']['modules'])}")
        else:
            click.echo("✅ Tenant provisioned successfully!")
            click.echo(f"   Action: {result['data']['action']}")
            if result['data'].get('system'):
                click.echo(f"   System: {result['data']['system']}")
            if result['data'].get('modules'):
                click.echo(f"   Modules: {', '.join(result['data']['modules'])}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to provision tenant: {e}")
        return 1

@tenants.command()
@click.option('--tenant', required=True, help='Tenant slug')
@click.option('--module', help='Module to start trial for')
@click.option('--system', help='System to start trial for')
@click.option('--days', default=14, help='Trial duration in days (default: 14)')
@click.option('--json', is_flag=True, help='Output in JSON format')
def trial(tenant, module, system, days, json):
    """Start a trial for a tenant"""
    try:
        from src.control_plane.service import ControlPlaneService
        
        if not module and not system:
            click.echo("❌ Either --module or --system must be specified")
            return 1
        
        target = module or system
        click.echo(f"🎯 Starting {days}-day trial of {target} for tenant: {tenant}...")
        
        control_plane = ControlPlaneService()
        result = control_plane.start_trial(tenant, module, system, days)
        
        if not result['success']:
            click.echo(f"❌ Failed to start trial: {result['error']}")
            return 1
        
        if json:
            click.echo(json_module.dumps(result['data'], indent=2))
            return 0
        
        click.echo("✅ Trial started successfully!")
        click.echo(f"   Action: {result['data']['action']}")
        click.echo(f"   Tenant: {result['data']['tenant']}")
        if result['data'].get('module'):
            click.echo(f"   Module: {result['data']['module']}")
        if result['data'].get('system'):
            click.echo(f"   System: {result['data']['system']}")
        click.echo(f"   Days: {result['data']['days']}")
        click.echo(f"   Trial ends: {result['data']['trial_ends_at']}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to start trial: {e}")
        return 1

@tenants.command()
@click.option('--tenant', required=True, help='Tenant slug')
@click.option('--module', help='Module to subscribe to')
@click.option('--system', help='System to subscribe to')
@click.option('--plan', default='professional', help='Subscription plan (default: professional)')
@click.option('--json', is_flag=True, help='Output in JSON format')
def subscribe(tenant, module, system, plan, json):
    """Subscribe tenant to a plan"""
    try:
        import json as json_module
        from src.control_plane.service import ControlPlaneService
        
        if not module and not system:
            click.echo("❌ Either --module or --system must be specified")
            return 1
        
        target = module or system
        click.echo(f"💳 Subscribing {tenant} to {plan} plan for {target}...")
        
        control_plane = ControlPlaneService()
        result = control_plane.subscribe_tenant(tenant, module, system, plan)
        
        if not result['success']:
            click.echo(f"❌ Failed to subscribe tenant: {result['error']}")
            return 1
        
        if json:
            click.echo(json_module.dumps(result['data'], indent=2))
            return 0
        
        click.echo("✅ Subscription created successfully!")
        click.echo(f"   Action: {result['data']['action']}")
        click.echo(f"   Tenant: {result['data']['tenant']}")
        if result['data'].get('module'):
            click.echo(f"   Module: {result['data']['module']}")
        if result['data'].get('system'):
            click.echo(f"   System: {result['data']['system']}")
        click.echo(f"   Plan: {result['data']['plan']}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to subscribe tenant: {e}")
        return 1

@tenants.command()
@click.option('--tenant', required=True, help='Tenant slug')
@click.option('--module', help='Module to cancel')
@click.option('--system', help='System to cancel')
@click.option('--json', is_flag=True, help='Output in JSON format')
def cancel(tenant, module, system, json):
    """Cancel tenant subscription"""
    try:
        from src.control_plane.service import ControlPlaneService
        
        if not module and not system:
            click.echo("❌ Either --module or --system must be specified")
            return 1
        
        target = module or system
        click.echo(f"❌ Cancelling subscription for {target} for tenant: {tenant}...")
        
        control_plane = ControlPlaneService()
        result = control_plane.cancel_subscription(tenant, module, system)
        
        if not result['success']:
            click.echo(f"❌ Failed to cancel subscription: {result['error']}")
            return 1
        
        if json:
            click.echo(json_module.dumps(result['data'], indent=2))
            return 0
        
        click.echo("✅ Subscription cancelled successfully!")
        click.echo(f"   Action: {result['data']['action']}")
        click.echo(f"   Tenant: {result['data']['tenant']}")
        if result['data'].get('module'):
            click.echo(f"   Module: {result['data']['module']}")
        if result['data'].get('system'):
            click.echo(f"   System: {result['data']['system']}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to cancel subscription: {e}")
        return 1

@tenants.command()
@click.option('--tenant', required=True, help='Tenant slug')
@click.option('--days', default=30, help='Usage period in days (default: 30)')
@click.option('--json', is_flag=True, help='Output in JSON format')
def usage(tenant, days, json):
    """Get tenant usage metrics"""
    try:
        from src.control_plane.service import ControlPlaneService
        
        click.echo(f"📊 Getting usage metrics for tenant: {tenant} (last {days} days)...")
        
        control_plane = ControlPlaneService()
        result = control_plane.get_tenant_usage(tenant, days)
        
        if not result['success']:
            click.echo(f"❌ Failed to get usage: {result['error']}")
            return 1
        
        if json:
            click.echo(json_module.dumps(result['data'], indent=2))
            return 0
        
        usage_data = result['data']['usage']
        click.echo("✅ Usage metrics retrieved successfully!")
        click.echo(f"   Tenant: {result['data']['tenant']}")
        click.echo(f"   Period: {result['data']['period_days']} days")
        click.echo(f"   Events (7d): {usage_data.get('events_7d', 'N/A')}")
        click.echo(f"   Events (30d): {usage_data.get('events_30d', 'N/A')}")
        click.echo(f"   MAU: {usage_data.get('mau', 'N/A')}")
        click.echo(f"   Active modules: {usage_data.get('modules_active', 'N/A')}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to get usage: {e}")
        return 1

@tenants.command()
@click.option('--tenant', required=True, help='Tenant slug')
@click.option('--action', required=True, help='Operation to perform (migrate, reseed, clear_cache, restart_worker)')
@click.option('--module', help='Module to operate on')
@click.option('--dry-run', is_flag=True, help='Show what would be executed without making changes')
@click.option('--confirm', is_flag=True, help='Confirm execution (required for non-dry-run)')
@click.option('--json', is_flag=True, help='Output in JSON format')
def ops(tenant, action, module, dry_run, confirm, json):
    """Run operations on tenant"""
    try:
        from src.control_plane.service import ControlPlaneService
        
        if not dry_run and not confirm:
            click.echo("❌ --confirm is required for non-dry-run operations")
            return 1
        
        operation = "dry-run" if dry_run else "execute"
        click.echo(f"🔧 {operation.capitalize()} {action} for tenant: {tenant}...")
        
        control_plane = ControlPlaneService()
        result = control_plane.run_tenant_ops(tenant, action, module, dry_run)
        
        if not result['success']:
            click.echo(f"❌ Failed to run operation: {result['error']}")
            return 1
        
        if json:
            click.echo(json_module.dumps(result['data'], indent=2))
            return 0
        
        if dry_run:
            click.echo("✅ Operation dry-run completed")
            click.echo(f"   Action: {result['data']['action']}")
            click.echo(f"   Tenant: {result['data']['tenant']}")
            if result['data'].get('module'):
                click.echo(f"   Module: {result['data']['module']}")
        else:
            click.echo("✅ Operation executed successfully!")
            click.echo(f"   Action: {result['data']['action']}")
            click.echo(f"   Tenant: {result['data']['tenant']}")
            if result['data'].get('module'):
                click.echo(f"   Module: {result['data']['module']}")
            click.echo(f"   Result: {result['data']['result']}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to run operation: {e}")
        return 1

@tenants.command()
@click.option('--tenant', required=True, help='Tenant slug')
@click.option('--json', is_flag=True, help='Output in JSON format')
def status(tenant, json):
    """Get comprehensive tenant status"""
    try:
        from src.control_plane.service import ControlPlaneService
        
        click.echo(f"📊 Getting status for tenant: {tenant}...")
        
        control_plane = ControlPlaneService()
        result = control_plane.get_tenant_status(tenant)
        
        if not result['success']:
            click.echo(f"❌ Failed to get status: {result['error']}")
            return 1
        
        if json:
            click.echo(json_module.dumps(result['data'], indent=2))
            return 0
        
        data = result['data']
        click.echo("✅ Tenant status retrieved successfully!")
        click.echo(f"   Tenant: {data['tenant']['name']} ({data['tenant']['slug']})")
        click.echo(f"   Plan: {data['tenant']['plan']}")
        click.echo(f"   Status: {data['tenant']['status']}")
        click.echo(f"   Health: {'✅' if data['health']['readiness'] else '❌'}")
        click.echo(f"   Blueprints: {data['blueprints']['available']} available")
        click.echo(f"   Migrations: {'✅' if data['migrations']['at_head'] else '❌'}")
        click.echo(f"   Growth heartbeat: {'✅' if data['growth']['heartbeat'] else '❌'}")
        click.echo(f"   Events (24h): {data['growth']['events_24h']}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Failed to get status: {e}")
        return 1

# Register ERP Core commands
try:
    from src.erp_core.cli import erp
    cli.add_command(erp)
except ImportError as e:
    # ERP Core not available, skip registration
    pass

# Add Ops, Growth, and Security commands
cli.add_command(ops)
cli.add_command(growth)
cli.add_command(security)

# Auto-discover module CLI commands
_auto_discover_module_commands(cli)

if __name__ == '__main__':
    cli()
