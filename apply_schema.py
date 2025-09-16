#!/usr/bin/env python3
import os
import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set.")
    exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Add 'name' column to 'users' table if it doesn't exist
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255)")

    # Create other Phase 3 tables if they don't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_tenants (
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
            role VARCHAR(50) NOT NULL,
            PRIMARY KEY (user_id, tenant_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
            started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE,
            session_metadata JSONB
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
            role VARCHAR(50) NOT NULL,
            content JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    cur.execute("""
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
    """)
    cur.execute("""
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
    """)

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database schema applied successfully!")

except Exception as e:
    logger.error(f"Schema application failed: {e}")
    exit(1)
