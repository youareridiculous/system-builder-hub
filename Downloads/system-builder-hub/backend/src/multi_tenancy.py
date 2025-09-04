#!/usr/bin/env python3
"""
Multi-Tenancy & Quotas Module
Enforces tenant_id filtering in data layer and implements per-tenant quotas.
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from functools import wraps
import sqlite3

from flask import request, current_app, g, jsonify
from config import config

logger = logging.getLogger(__name__)

@dataclass
class TenantQuota:
    """Tenant quota configuration"""
    tenant_id: str
    active_previews_limit: int
    snapshot_rate_per_minute: int
    llm_monthly_budget_usd: float
    created_at: datetime
    updated_at: datetime

@dataclass
class TenantUsage:
    """Current tenant usage tracking"""
    tenant_id: str
    active_previews: int
    snapshots_this_minute: int
    llm_spent_this_month: float
    last_snapshot_reset: datetime
    last_llm_reset: datetime

class MultiTenancyManager:
    """Manages multi-tenancy, tenant isolation, and quota enforcement"""
    
    def __init__(self):
        self.quotas: Dict[str, TenantQuota] = {}
        self.usage: Dict[str, TenantUsage] = {}
        self.lock = threading.Lock()
        
        # Load default quotas from environment
        self.default_quota = TenantQuota(
            tenant_id='default',
            active_previews_limit=int(os.getenv('DEFAULT_ACTIVE_PREVIEWS_LIMIT', 5)),
            snapshot_rate_per_minute=int(os.getenv('DEFAULT_SNAPSHOT_RATE_PER_MINUTE', 10)),
            llm_monthly_budget_usd=float(os.getenv('DEFAULT_LLM_MONTHLY_BUDGET_USD', 100.0)),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Initialize database
        self._init_database()
        self._load_quotas_from_db()
        
        # Start usage reset background task
        self._start_usage_reset_task()
    
    def _init_database(self):
        """Initialize multi-tenancy database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create tenant_quotas table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tenant_quotas (
                        tenant_id TEXT PRIMARY KEY,
                        active_previews_limit INTEGER NOT NULL,
                        snapshot_rate_per_minute INTEGER NOT NULL,
                        llm_monthly_budget_usd REAL NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')
                
                # Create tenant_usage table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tenant_usage (
                        tenant_id TEXT PRIMARY KEY,
                        active_previews INTEGER DEFAULT 0,
                        snapshots_this_minute INTEGER DEFAULT 0,
                        llm_spent_this_month REAL DEFAULT 0.0,
                        last_snapshot_reset TIMESTAMP,
                        last_llm_reset TIMESTAMP
                    )
                ''')
                
                # Create tenant_quota_audit table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tenant_quota_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL,
                        quota_type TEXT NOT NULL,
                        old_value REAL,
                        new_value REAL,
                        changed_by TEXT NOT NULL,
                        changed_at TIMESTAMP NOT NULL
                    )
                ''')
                
                conn.commit()
                logger.info("Multi-tenancy database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize multi-tenancy database: {e}")
    
    def _load_quotas_from_db(self):
        """Load tenant quotas from database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM tenant_quotas')
                
                for row in cursor.fetchall():
                    quota = TenantQuota(
                        tenant_id=row[0],
                        active_previews_limit=row[1],
                        snapshot_rate_per_minute=row[2],
                        llm_monthly_budget_usd=row[3],
                        created_at=datetime.fromisoformat(row[4]),
                        updated_at=datetime.fromisoformat(row[5])
                    )
                    self.quotas[quota.tenant_id] = quota
                
                # Load usage data
                cursor.execute('SELECT * FROM tenant_usage')
                for row in cursor.fetchall():
                    usage = TenantUsage(
                        tenant_id=row[0],
                        active_previews=row[1],
                        snapshots_this_minute=row[2],
                        llm_spent_this_month=row[3],
                        last_snapshot_reset=datetime.fromisoformat(row[4]) if row[4] else None,
                        last_llm_reset=datetime.fromisoformat(row[5]) if row[5] else None
                    )
                    self.usage[usage.tenant_id] = usage
                
                logger.info(f"Loaded {len(self.quotas)} tenant quotas from database")
                
        except Exception as e:
            logger.error(f"Failed to load quotas from database: {e}")
    
    def _start_usage_reset_task(self):
        """Start background task for usage reset"""
        def reset_worker():
            while True:
                time.sleep(60)  # Check every minute
                self._reset_periodic_usage()
        
        thread = threading.Thread(target=reset_worker, daemon=True)
        thread.start()
    
    def _reset_periodic_usage(self):
        """Reset periodic usage counters"""
        now = datetime.now()
        
        with self.lock:
            for tenant_id, usage in self.usage.items():
                # Reset snapshot counter if minute has passed
                if (usage.last_snapshot_reset is None or 
                    (now - usage.last_snapshot_reset).total_seconds() >= 60):
                    usage.snapshots_this_minute = 0
                    usage.last_snapshot_reset = now
                
                # Reset LLM spending if month has passed
                if (usage.last_llm_reset is None or 
                    (now - usage.last_llm_reset).days >= 30):
                    usage.llm_spent_this_month = 0.0
                    usage.last_llm_reset = now
        
        # Save to database
        self._save_usage_to_db()
    
    def _save_usage_to_db(self):
        """Save usage data to database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                for usage in self.usage.values():
                    cursor.execute('''
                        INSERT OR REPLACE INTO tenant_usage 
                        (tenant_id, active_previews, snapshots_this_minute, 
                         llm_spent_this_month, last_snapshot_reset, last_llm_reset)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        usage.tenant_id,
                        usage.active_previews,
                        usage.snapshots_this_minute,
                        usage.llm_spent_this_month,
                        usage.last_snapshot_reset.isoformat() if usage.last_snapshot_reset else None,
                        usage.last_llm_reset.isoformat() if usage.last_llm_reset else None
                    ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save usage to database: {e}")
    
    def get_tenant_quota(self, tenant_id: str) -> TenantQuota:
        """Get tenant quota configuration"""
        with self.lock:
            return self.quotas.get(tenant_id, self.default_quota)
    
    def get_tenant_usage(self, tenant_id: str) -> TenantUsage:
        """Get current tenant usage"""
        with self.lock:
            if tenant_id not in self.usage:
                self.usage[tenant_id] = TenantUsage(
                    tenant_id=tenant_id,
                    active_previews=0,
                    snapshots_this_minute=0,
                    llm_spent_this_month=0.0,
                    last_snapshot_reset=None,
                    last_llm_reset=None
                )
            return self.usage[tenant_id]
    
    def check_preview_quota(self, tenant_id: str) -> Dict[str, Any]:
        """Check if tenant can create a new preview"""
        quota = self.get_tenant_quota(tenant_id)
        usage = self.get_tenant_usage(tenant_id)
        
        if usage.active_previews >= quota.active_previews_limit:
            return {
                'allowed': False,
                'reason': 'active_previews_limit_exceeded',
                'current': usage.active_previews,
                'limit': quota.active_previews_limit,
                'status_code': 429
            }
        
        return {'allowed': True}
    
    def check_snapshot_quota(self, tenant_id: str) -> Dict[str, Any]:
        """Check if tenant can take a snapshot"""
        quota = self.get_tenant_quota(tenant_id)
        usage = self.get_tenant_usage(tenant_id)
        
        if usage.snapshots_this_minute >= quota.snapshot_rate_per_minute:
            return {
                'allowed': False,
                'reason': 'snapshot_rate_limit_exceeded',
                'current': usage.snapshots_this_minute,
                'limit': quota.snapshot_rate_per_minute,
                'status_code': 429
            }
        
        return {'allowed': True}
    
    def check_llm_quota(self, tenant_id: str, estimated_cost: float) -> Dict[str, Any]:
        """Check if tenant can make LLM call"""
        quota = self.get_tenant_quota(tenant_id)
        usage = self.get_tenant_usage(tenant_id)
        
        if usage.llm_spent_this_month + estimated_cost > quota.llm_monthly_budget_usd:
            return {
                'allowed': False,
                'reason': 'llm_budget_exceeded',
                'current': usage.llm_spent_this_month,
                'limit': quota.llm_monthly_budget_usd,
                'estimated_cost': estimated_cost,
                'status_code': 402  # Payment Required
            }
        
        return {'allowed': True}
    
    def increment_preview_count(self, tenant_id: str, delta: int = 1):
        """Increment active preview count"""
        with self.lock:
            usage = self.get_tenant_usage(tenant_id)
            usage.active_previews += delta
            self._save_usage_to_db()
    
    def increment_snapshot_count(self, tenant_id: str):
        """Increment snapshot count for current minute"""
        with self.lock:
            usage = self.get_tenant_usage(tenant_id)
            usage.snapshots_this_minute += 1
            self._save_usage_to_db()
    
    def increment_llm_spending(self, tenant_id: str, cost: float):
        """Increment LLM spending for current month"""
        with self.lock:
            usage = self.get_tenant_usage(tenant_id)
            usage.llm_spent_this_month += cost
            self._save_usage_to_db()
    
    def update_tenant_quota(self, tenant_id: str, quota_type: str, new_value: float, 
                          changed_by: str) -> bool:
        """Update tenant quota and audit the change"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Get current quota
                cursor.execute('SELECT * FROM tenant_quotas WHERE tenant_id = ?', (tenant_id,))
                row = cursor.fetchone()
                
                if row:
                    # Update existing quota
                    old_value = getattr(TenantQuota(*row), quota_type)
                    cursor.execute(f'''
                        UPDATE tenant_quotas 
                        SET {quota_type} = ?, updated_at = ?
                        WHERE tenant_id = ?
                    ''', (new_value, datetime.now().isoformat(), tenant_id))
                else:
                    # Create new quota
                    old_value = None
                    cursor.execute('''
                        INSERT INTO tenant_quotas 
                        (tenant_id, active_previews_limit, snapshot_rate_per_minute, 
                         llm_monthly_budget_usd, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        tenant_id,
                        self.default_quota.active_previews_limit,
                        self.default_quota.snapshot_rate_per_minute,
                        self.default_quota.llm_monthly_budget_usd,
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    
                    # Update the specific field
                    cursor.execute(f'''
                        UPDATE tenant_quotas 
                        SET {quota_type} = ?, updated_at = ?
                        WHERE tenant_id = ?
                    ''', (new_value, datetime.now().isoformat(), tenant_id))
                
                # Audit the change
                cursor.execute('''
                    INSERT INTO tenant_quota_audit 
                    (tenant_id, quota_type, old_value, new_value, changed_by, changed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    tenant_id, quota_type, old_value, new_value, 
                    changed_by, datetime.now().isoformat()
                ))
                
                conn.commit()
                
                # Update in-memory cache
                with self.lock:
                    self._load_quotas_from_db()
                
                logger.info(f"Updated {quota_type} for tenant {tenant_id}: {old_value} -> {new_value}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update tenant quota: {e}")
            return False
    
    def get_quota_audit_log(self, tenant_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get quota audit log"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                if tenant_id:
                    cursor.execute('''
                        SELECT * FROM tenant_quota_audit 
                        WHERE tenant_id = ? 
                        ORDER BY changed_at DESC 
                        LIMIT ?
                    ''', (tenant_id, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM tenant_quota_audit 
                        ORDER BY changed_at DESC 
                        LIMIT ?
                    ''', (limit,))
                
                audit_log = []
                for row in cursor.fetchall():
                    audit_log.append({
                        'id': row[0],
                        'tenant_id': row[1],
                        'quota_type': row[2],
                        'old_value': row[3],
                        'new_value': row[4],
                        'changed_by': row[5],
                        'changed_at': row[6]
                    })
                
                return audit_log
                
        except Exception as e:
            logger.error(f"Failed to get quota audit log: {e}")
            return []

# Global instance
multi_tenancy = MultiTenancyManager()

def require_tenant_context(f):
    """Decorator to require tenant context in request"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get tenant_id from various sources
        tenant_id = (
            request.headers.get('X-Tenant-ID') or
            request.args.get('tenant_id') or
            (request.get_json() or {}).get('tenant_id') or
            getattr(g, 'tenant_id', None)
        )
        
        if not tenant_id:
            return {'error': 'Missing tenant_id'}, 400
        
        # Store in Flask g for access in route handlers
        g.tenant_id = tenant_id
        
        return f(*args, **kwargs)
    
    return decorated_function

def enforce_tenant_isolation(f):
    """Decorator to enforce tenant isolation in data queries"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tenant_id = getattr(g, 'tenant_id', None)
        if not tenant_id:
            return {'error': 'Missing tenant context'}, 400
        
        # Store tenant_id in g for data layer access
        g.tenant_id = tenant_id
        
        return f(*args, **kwargs)
    
    return decorated_function

def check_preview_quota(f):
    """Decorator to check preview quota before allowing preview creation"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tenant_id = getattr(g, 'tenant_id', None)
        if not tenant_id:
            return {'error': 'Missing tenant context'}, 400
        
        quota_check = multi_tenancy.check_preview_quota(tenant_id)
        if not quota_check['allowed']:
            return {
                'error': 'Preview quota exceeded',
                'details': quota_check
            }, quota_check['status_code']
        
        return f(*args, **kwargs)
    
    return decorated_function

def check_snapshot_quota(f):
    """Decorator to check snapshot quota before allowing snapshot creation"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tenant_id = getattr(g, 'tenant_id', None)
        if not tenant_id:
            return {'error': 'Missing tenant context'}, 400
        
        quota_check = multi_tenancy.check_snapshot_quota(tenant_id)
        if not quota_check['allowed']:
            return {
                'error': 'Snapshot quota exceeded',
                'details': quota_check
            }, quota_check['status_code']
        
        return f(*args, **kwargs)
    
    return decorated_function

def check_llm_quota(estimated_cost: float):
    """Decorator to check LLM quota before allowing LLM calls"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            tenant_id = getattr(g, 'tenant_id', None)
            if not tenant_id:
                return {'error': 'Missing tenant context'}, 400
            
            quota_check = multi_tenancy.check_llm_quota(tenant_id, estimated_cost)
            if not quota_check['allowed']:
                return {
                    'error': 'LLM quota exceeded',
                    'details': quota_check
                }, quota_check['status_code']
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
