#!/usr/bin/env python3
"""
Migration endpoint for System Builder Hub
"""
import os
import logging
from flask import Blueprint, jsonify, request
from sqlalchemy import text

logger = logging.getLogger(__name__)

migrate_bp = Blueprint('migrate_api', __name__, url_prefix='/api/migrate')

@migrate_bp.route('/fix-schema', methods=['POST'])
def fix_schema():
    """Fix the database schema by creating proper tables"""
    try:
        from .database_manager import get_db_manager
        
        db_manager = get_db_manager()
        with db_manager.get_session() as session:
            # Create users table with proper schema
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255),
                    password_hash VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # Create tenants table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # Create user_tenants table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS user_tenants (
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
                    role VARCHAR(50) NOT NULL,
                    PRIMARY KEY (user_id, tenant_id)
                )
            """))
            
            # Create sessions table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
                    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    expires_at TIMESTAMP WITH TIME ZONE,
                    session_metadata JSONB
                )
            """))
            
            # Create conversations table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # Create messages table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS messages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
                    role VARCHAR(50) NOT NULL,
                    content JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # Create build_specs table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS build_specs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
                    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
                    title VARCHAR(255) NOT NULL,
                    plan_manifest JSONB NOT NULL,
                    repo_skeleton JSONB NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'draft',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # Create build_runs table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS build_runs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
                    spec_id UUID REFERENCES build_specs(id) ON DELETE CASCADE,
                    build_id VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'queued',
                    started_at TIMESTAMP WITH TIME ZONE,
                    finished_at TIMESTAMP WITH TIME ZONE,
                    logs_pointer TEXT,
                    artifacts_pointer TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # Create indexes
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)"))
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_tenant_id ON sessions(tenant_id)"))
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_conversations_tenant_id ON conversations(tenant_id)"))
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)"))
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_build_specs_tenant_id ON build_specs(tenant_id)"))
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_build_runs_tenant_id ON build_runs(tenant_id)"))
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_build_runs_spec_id ON build_runs(spec_id)"))
            
            # Insert demo data
            session.execute(text("""
                INSERT INTO users (email, name, password_hash) 
                VALUES ('demo@example.com', 'Demo User', 'demo-password-hash')
                ON CONFLICT (email) DO NOTHING
            """))
            
            session.execute(text("""
                INSERT INTO tenants (name, slug) 
                VALUES ('Demo Tenant', 'demo')
                ON CONFLICT (slug) DO NOTHING
            """))
            
            session.execute(text("""
                INSERT INTO user_tenants (user_id, tenant_id, role)
                SELECT u.id, t.id, 'admin'
                FROM users u, tenants t
                WHERE u.email = 'demo@example.com' AND t.slug = 'demo'
                ON CONFLICT (user_id, tenant_id) DO NOTHING
            """))
            
            session.commit()
            
        return jsonify({
            "ok": True,
            "message": "Database schema fixed successfully"
        })
        
    except Exception as e:
        logger.error(f"Schema fix failed: {e}")
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500

@migrate_bp.route('/status', methods=['GET'])
def migration_status():
    """Check migration status"""
    try:
        from .database_manager import get_db_manager
        
        db_manager = get_db_manager()
        with db_manager.get_session() as session:
            # Check if tables exist
            result = session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('users', 'tenants', 'sessions', 'conversations', 'messages', 'build_specs', 'build_runs')
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result.fetchall()]
            
            return jsonify({
                "ok": True,
                "tables": tables,
                "all_tables_present": len(tables) == 7
            })
            
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500