#!/usr/bin/env python3
"""
Feature Flags System for System Builder Hub
Environment and database-backed feature toggles with decorator support.
Now with audit logging for flag changes.
"""

import os
import logging
import sqlite3
from typing import Dict, Any, Optional, List
from functools import wraps
from datetime import datetime

from flask import request, jsonify, current_app, g
from config import config

logger = logging.getLogger(__name__)

class FeatureFlags:
    """Feature flags manager with audit logging"""
    
    def __init__(self):
        self.flags: Dict[str, bool] = {}
        self._load_environment_flags()
        self._init_audit_database()
    
    def _load_environment_flags(self):
        """Load feature flags from environment variables"""
        # Load all environment variables that start with FEATURE_
        for key, value in os.environ.items():
            if key.startswith('FEATURE_'):
                flag_name = key[8:].lower()  # Remove FEATURE_ prefix
                self.flags[flag_name] = value.lower() in ('true', '1', 'yes', 'on')
        
        # Set default flags
        default_flags = {
            'blackbox_inspector': True,
            'agent_negotiation': True,
            'redteam_simulator': False,
            'advanced_analytics': True,
            'preview_engine': True,
            'cost_accounting': True,
            'compliance_engine': True,
            'multi_tenant': False,
            'real_time_collaboration': True,
            'voice_processing': True,
            'visual_processing': True,
            'self_healing': True,
            'federated_learning': False,
            'edge_deployment': False,
            'quantum_optimization': False
        }
        
        for flag_name, default_value in default_flags.items():
            if flag_name not in self.flags:
                self.flags[flag_name] = default_value
    
    def _init_audit_database(self):
        """Initialize feature flag audit database table"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS feature_flag_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        flag_name TEXT NOT NULL,
                        old_value BOOLEAN,
                        new_value BOOLEAN NOT NULL,
                        changed_by TEXT NOT NULL,
                        tenant_id TEXT,
                        changed_at TIMESTAMP NOT NULL,
                        reason TEXT
                    )
                ''')
                
                conn.commit()
                logger.info("Feature flag audit database table initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize feature flag audit database: {e}")
    
    def is_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled"""
        return self.flags.get(flag_name.lower(), False)
    
    def set_flag(self, flag_name: str, enabled: bool, changed_by: str = None, tenant_id: str = None, reason: str = None):
        """Set a feature flag with audit logging"""
        flag_name = flag_name.lower()
        old_value = self.flags.get(flag_name)
        
        self.flags[flag_name] = enabled
        logger.info(f"Feature flag '{flag_name}' set to {enabled}")
        
        # Audit the change
        self._audit_flag_change(flag_name, old_value, enabled, changed_by, tenant_id, reason)
    
    def get_all_flags(self) -> Dict[str, bool]:
        """Get all feature flags"""
        return self.flags.copy()
    
    def get_enabled_flags(self) -> List[str]:
        """Get list of enabled feature flags"""
        return [flag for flag, enabled in self.flags.items() if enabled]
    
    def get_disabled_flags(self) -> List[str]:
        """Get list of disabled feature flags"""
        return [flag for flag, enabled in self.flags.items() if not enabled]
    
    def load_from_database(self):
        """Load feature flags from database"""
        if not config.ENABLE_FEATURE_FLAGS:
            return
        
        try:
            from database import get_db_session
            from sqlalchemy import text
            
            with get_db_session() as session:
                result = session.execute(text("SELECT name, enabled FROM feature_flags"))
                
                for row in result:
                    flag_name = row.name.lower()
                    self.flags[flag_name] = row.enabled
                
                logger.info(f"Loaded {len(self.flags)} feature flags from database")
                
        except Exception as e:
            logger.warning(f"Failed to load feature flags from database: {e}")
    
    def _audit_flag_change(self, flag_name: str, old_value: bool, new_value: bool, 
                          changed_by: str, tenant_id: str = None, reason: str = None):
        """Audit a feature flag change"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO feature_flag_audit 
                    (flag_name, old_value, new_value, changed_by, tenant_id, changed_at, reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    flag_name,
                    old_value,
                    new_value,
                    changed_by or 'system',
                    tenant_id,
                    datetime.now().isoformat(),
                    reason
                ))
                conn.commit()
                
                logger.info(f"Audited feature flag change: {flag_name} {old_value} -> {new_value} by {changed_by}")
                
        except Exception as e:
            logger.error(f"Failed to audit feature flag change: {e}")
    
    def get_audit_log(self, flag_name: str = None, tenant_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get feature flag audit log"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                if flag_name and tenant_id:
                    cursor.execute('''
                        SELECT * FROM feature_flag_audit 
                        WHERE flag_name = ? AND tenant_id = ?
                        ORDER BY changed_at DESC 
                        LIMIT ?
                    ''', (flag_name, tenant_id, limit))
                elif flag_name:
                    cursor.execute('''
                        SELECT * FROM feature_flag_audit 
                        WHERE flag_name = ?
                        ORDER BY changed_at DESC 
                        LIMIT ?
                    ''', (flag_name, limit))
                elif tenant_id:
                    cursor.execute('''
                        SELECT * FROM feature_flag_audit 
                        WHERE tenant_id = ?
                        ORDER BY changed_at DESC 
                        LIMIT ?
                    ''', (tenant_id, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM feature_flag_audit 
                        ORDER BY changed_at DESC 
                        LIMIT ?
                    ''', (limit,))
                
                audit_log = []
                for row in cursor.fetchall():
                    audit_log.append({
                        'id': row[0],
                        'flag_name': row[1],
                        'old_value': row[2],
                        'new_value': row[3],
                        'changed_by': row[4],
                        'tenant_id': row[5],
                        'changed_at': row[6],
                        'reason': row[7]
                    })
                
                return audit_log
                
        except Exception as e:
            logger.error(f"Failed to get feature flag audit log: {e}")
            return []
    
    def save_to_database(self):
        """Save feature flags to database"""
        if not config.ENABLE_FEATURE_FLAGS:
            return
        
        try:
            from database import get_db_session
            from sqlalchemy import text
            
            with get_db_session() as session:
                for flag_name, enabled in self.flags.items():
                    session.execute(text("""
                        INSERT OR REPLACE INTO feature_flags 
                        (id, name, enabled, description, created_at, updated_at)
                        VALUES (:id, :name, :enabled, :description, :created_at, :updated_at)
                    """), {
                        'id': flag_name,
                        'name': flag_name,
                        'enabled': enabled,
                        'description': f'Feature flag for {flag_name}',
                        'created_at': datetime.now(),
                        'updated_at': datetime.now()
                    })
                
                logger.info(f"Saved {len(self.flags)} feature flags to database")
                
        except Exception as e:
            logger.error(f"Failed to save feature flags to database: {e}")

# Global feature flags instance
feature_flags = FeatureFlags()


def flag_optional(flag_name: str, fallback_value: Any = None):
    """Decorator to make a feature optional based on flag"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not config.ENABLE_FEATURE_FLAGS:
                return f(*args, **kwargs)
            
            if not feature_flags.is_enabled(flag_name):
                return fallback_value
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def conditional_feature(flag_name: str, enabled_func: callable, disabled_func: callable = None):
    """Decorator to provide different implementations based on feature flag"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not config.ENABLE_FEATURE_FLAGS:
                return f(*args, **kwargs)
            
            if feature_flags.is_enabled(flag_name):
                return enabled_func(*args, **kwargs)
            elif disabled_func:
                return disabled_func(*args, **kwargs)
            else:
                return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def flag_required(flag_name: str, error_message: str = None):
    """Decorator to require a feature flag to be enabled"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not feature_flags.is_enabled(flag_name):
                message = error_message or f"Feature '{flag_name}' is disabled"
                return jsonify({'error': message}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Predefined feature flag decorators for common features
def require_blackbox_inspector(f):
    """Require blackbox inspector feature"""
    return flag_required('blackbox_inspector', 'Blackbox Inspector feature is disabled')(f)

def require_agent_negotiation(f):
    """Require agent negotiation feature"""
    return flag_required('agent_negotiation', 'Agent Negotiation feature is disabled')(f)

def require_redteam_simulator(f):
    """Require red team simulator feature"""
    return flag_required('redteam_simulator', 'Red Team Simulator feature is disabled')(f)

def require_preview_engine(f):
    """Require preview engine feature"""
    return flag_required('preview_engine', 'Preview Engine feature is disabled')(f)

def require_cost_accounting(f):
    """Require cost accounting feature"""
    return flag_required('cost_accounting', 'Cost Accounting feature is disabled')(f)

def require_compliance_engine(f):
    """Require compliance engine feature"""
    return flag_required('compliance_engine', 'Compliance Engine feature is disabled')(f)

def require_multi_tenant(f):
    """Require multi-tenant feature"""
    return flag_required('multi_tenant', 'Multi-tenant feature is disabled')(f)

def require_real_time_collaboration(f):
    """Require real-time collaboration feature"""
    return flag_required('real_time_collaboration', 'Real-time collaboration feature is disabled')(f)

def require_voice_processing(f):
    """Require voice processing feature"""
    return flag_required('voice_processing', 'Voice processing feature is disabled')(f)

def require_visual_processing(f):
    """Require visual processing feature"""
    return flag_required('visual_processing', 'Visual processing feature is disabled')(f)

def require_self_healing(f):
    """Require self-healing feature"""
    return flag_required('self_healing', 'Self-healing feature is disabled')(f)

def require_federated_learning(f):
    """Require federated learning feature"""
    return flag_required('federated_learning', 'Federated learning feature is disabled')(f)

def require_edge_deployment(f):
    """Require edge deployment feature"""
    return flag_required('edge_deployment', 'Edge deployment feature is disabled')(f)

def require_quantum_optimization(f):
    """Require quantum optimization feature"""
    return flag_required('quantum_optimization', 'Quantum optimization feature is disabled')(f)

# Utility functions
def get_feature_status(flag_name: str) -> Dict[str, Any]:
    """Get detailed status of a feature flag"""
    enabled = feature_flags.is_enabled(flag_name)
    
    return {
        'name': flag_name,
        'enabled': enabled,
        'source': 'environment' if flag_name.upper() in os.environ else 'default',
        'last_updated': datetime.now().isoformat()
    }

def get_all_feature_status() -> Dict[str, Any]:
    """Get status of all feature flags"""
    return {
        'enabled': feature_flags.get_enabled_flags(),
        'disabled': feature_flags.get_disabled_flags(),
        'total': len(feature_flags.flags),
        'last_updated': datetime.now().isoformat()
    }

def enable_feature(flag_name: str):
    """Enable a feature flag"""
    feature_flags.set_flag(flag_name, True)
    feature_flags.save_to_database()

def disable_feature(flag_name: str):
    """Disable a feature flag"""
    feature_flags.set_flag(flag_name, False)
    feature_flags.save_to_database()

# Initialize feature flags from database on startup
def initialize_feature_flags():
    """Initialize feature flags system"""
    if config.ENABLE_FEATURE_FLAGS:
        feature_flags.load_from_database()
        logger.info(f"Feature flags initialized: {len(feature_flags.flags)} flags loaded")
    else:
        logger.info("Feature flags disabled")
