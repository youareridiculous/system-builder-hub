-- SBH PostgreSQL Seed Data - Phase 2 Cloud Deployment
-- This migration adds initial system configuration and default data

-- =============================================================================
-- SYSTEM CONFIGURATION
-- =============================================================================

INSERT INTO system_configs (config_key, config_value, description) VALUES
('sbh.version', '"1.0.0"', 'SBH system version'),
('sbh.environment', '"production"', 'Current environment'),
('sbh.features.persistent_memory', 'true', 'Enable persistent memory system'),
('sbh.features.s3_workspace', 'true', 'Enable S3 workspace storage'),
('sbh.features.auto_scaling', 'true', 'Enable ECS auto scaling'),
('sbh.build.max_concurrent_builds', '5', 'Maximum concurrent builds'),
('sbh.build.default_timeout_minutes', '30', 'Default build timeout'),
('sbh.chat.max_conversation_length', '1000', 'Maximum messages per conversation'),
('sbh.workspace.max_size_mb', '1000', 'Maximum workspace size in MB'),
('sbh.retention.conversation_days', '90', 'Conversation retention period'),
('sbh.retention.build_logs_days', '30', 'Build logs retention period');

-- =============================================================================
-- DEFAULT USER (for system operations)
-- =============================================================================

INSERT INTO users (id, email, username, is_active, is_admin) VALUES
('00000000-0000-0000-0000-000000000001', 'system@sbh.local', 'system', true, true);

-- =============================================================================
-- DEFAULT MEMORY ENTRIES
-- =============================================================================

INSERT INTO memory_entries (user_id, entry_type, key_path, value_data) VALUES
('00000000-0000-0000-0000-000000000001', 'system', 'sbh.defaults.build_timeout', '1800'),
('00000000-0000-0000-0000-000000000001', 'system', 'sbh.defaults.workspace_cleanup_days', '7'),
('00000000-0000-0000-0000-000000000001', 'system', 'sbh.defaults.max_build_retries', '3'),
('00000000-0000-0000-0000-000000000001', 'system', 'sbh.defaults.health_check_interval', '30'),
('00000000-0000-0000-0000-000000000001', 'system', 'sbh.defaults.log_level', '"INFO"');

-- =============================================================================
-- WORKSPACE TYPES CONFIGURATION
-- =============================================================================

INSERT INTO system_configs (config_key, config_value, description) VALUES
('sbh.workspace.types', '{
  "nextjs": {
    "name": "Next.js Application",
    "description": "Modern React application with Next.js",
    "default_pages": ["home", "about", "contact"],
    "required_dependencies": ["next", "react", "typescript"]
  },
  "api": {
    "name": "API Service",
    "description": "RESTful API service",
    "default_endpoints": ["health", "docs"],
    "required_dependencies": ["flask", "sqlalchemy"]
  },
  "dashboard": {
    "name": "Admin Dashboard",
    "description": "Administrative dashboard interface",
    "default_pages": ["dashboard", "users", "settings"],
    "required_dependencies": ["react", "chart.js"]
  }
}', 'Available workspace types and their configurations');

-- =============================================================================
-- BUILD AGENT CONFIGURATIONS
-- =============================================================================

INSERT INTO system_configs (config_key, config_value, description) VALUES
('sbh.agents.config', '{
  "product_architect": {
    "enabled": true,
    "timeout_seconds": 300,
    "max_retries": 2
  },
  "system_designer": {
    "enabled": true,
    "timeout_seconds": 600,
    "max_retries": 2
  },
  "security_compliance": {
    "enabled": true,
    "timeout_seconds": 180,
    "max_retries": 1
  },
  "codegen_engineer": {
    "enabled": true,
    "timeout_seconds": 900,
    "max_retries": 3
  },
  "qa_evaluator": {
    "enabled": true,
    "timeout_seconds": 240,
    "max_retries": 2
  },
  "devops": {
    "enabled": true,
    "timeout_seconds": 300,
    "max_retries": 2
  }
}', 'Build agent configurations and timeouts');
