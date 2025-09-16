#!/usr/bin/env python3
"""
Idempotency Middleware for System Builder Hub
Handles Idempotency-Key headers and caches responses for mutating endpoints.
Now with durable storage and TTL sweeper task.
"""

import hashlib
import json
import logging
import threading
import time
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Optional, Any, Callable
from contextlib import contextmanager

from flask import request, jsonify, g, current_app
from config import config

logger = logging.getLogger(__name__)

class IdempotencyManager:
    """Manages idempotency keys and response caching with durable storage"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()
        
        # Initialize durable storage
        self._init_database()
        self._load_from_database()
        
        # Start TTL sweeper task
        self._start_ttl_sweeper()
    
    def _generate_key(self, method: str, path: str, body: str, user_id: Optional[str] = None, tenant_id: Optional[str] = None) -> str:
        """Generate a unique key for the request"""
        key_parts = [
            method.upper(),
            path,
            body,
            user_id or '',
            tenant_id or ''
        ]
        key_string = '|'.join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _normalize_body(self, body: bytes) -> str:
        """Normalize request body for consistent hashing"""
        try:
            # Try to parse as JSON and re-serialize for consistent ordering
            data = json.loads(body.decode('utf-8'))
            return json.dumps(data, sort_keys=True, separators=(',', ':'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # If not JSON, return as string
            return body.decode('utf-8', errors='ignore')
    
    def _init_database(self):
        """Initialize idempotency database table"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS idempotency_keys (
                        idempotency_key TEXT PRIMARY KEY,
                        method TEXT NOT NULL,
                        path TEXT NOT NULL,
                        body_hash TEXT NOT NULL,
                        user_id TEXT,
                        tenant_id TEXT,
                        status_code INTEGER NOT NULL,
                        response_body TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        is_replay BOOLEAN DEFAULT FALSE
                    )
                ''')
                
                conn.commit()
                logger.info("Idempotency database table initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize idempotency database: {e}")
    
    def _load_from_database(self):
        """Load idempotency keys from database into cache"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT idempotency_key, status_code, response_body, expires_at, is_replay
                    FROM idempotency_keys 
                    WHERE expires_at > ?
                ''', (datetime.now().isoformat(),))
                
                for row in cursor.fetchall():
                    key, status_code, response_body, expires_at, is_replay = row
                    expires_timestamp = datetime.fromisoformat(expires_at).timestamp()
                    
                    self.cache[key] = {
                        'status_code': status_code,
                        'response_body': response_body,
                        'expires_at': expires_timestamp,
                        'is_replay': bool(is_replay)
                    }
                
                logger.info(f"Loaded {len(self.cache)} idempotency keys from database")
                
        except Exception as e:
            logger.error(f"Failed to load idempotency keys from database: {e}")
    
    def _start_ttl_sweeper(self):
        """Start background TTL sweeper task"""
        def sweeper_worker():
            while True:
                time.sleep(300)  # Run every 5 minutes
                self._cleanup_expired()
        
        thread = threading.Thread(target=sweeper_worker, daemon=True)
        thread.start()
        logger.info("Started idempotency TTL sweeper task")
    
    def _cleanup_expired(self):
        """Clean up expired idempotency keys from cache and database"""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        with self.lock:
            expired_keys = []
            for key, data in self.cache.items():
                if data['expires_at'] < now:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired idempotency keys from cache")
            
            self.last_cleanup = now
        
        # Clean up from database
        self._cleanup_database_expired()
    
    def _cleanup_database_expired(self):
        """Clean up expired idempotency keys from database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM idempotency_keys WHERE expires_at <= ?', 
                             (datetime.now().isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} expired idempotency keys from database")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup expired keys from database: {e}")
    
    def get_cached_response(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response for idempotency key"""
        self._cleanup_expired()
        
        with self.lock:
            if idempotency_key in self.cache:
                data = self.cache[idempotency_key]
                if data['expires_at'] > time.time():
                    logger.info(f"Returning cached response for idempotency key: {idempotency_key[:8]}...")
                    return data
                else:
                    # Remove expired entry
                    del self.cache[idempotency_key]
        
        return None
    
    def cache_response(self, idempotency_key: str, status_code: int, response_body: str, 
                      method: str, path: str, body_hash: str, user_id: Optional[str] = None, 
                      tenant_id: Optional[str] = None, ttl_hours: int = None, is_replay: bool = False) -> None:
        """Cache response for idempotency key with durable storage"""
        if ttl_hours is None:
            ttl_hours = config.IDEMPOTENCY_TTL_HOURS
        
        expires_at = time.time() + (ttl_hours * 3600)
        expires_at_iso = datetime.fromtimestamp(expires_at).isoformat()
        
        with self.lock:
            self.cache[idempotency_key] = {
                'status_code': status_code,
                'response_body': response_body,
                'expires_at': expires_at,
                'is_replay': is_replay
            }
        
        # Store in database for durability
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO idempotency_keys 
                    (idempotency_key, method, path, body_hash, user_id, tenant_id, 
                     status_code, response_body, created_at, expires_at, is_replay)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    idempotency_key,
                    method,
                    path,
                    body_hash,
                    user_id,
                    tenant_id,
                    status_code,
                    response_body,
                    datetime.now().isoformat(),
                    expires_at_iso,
                    is_replay
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store idempotency key in database: {e}")
        
        logger.info(f"Cached response for idempotency key: {idempotency_key[:8]}... (expires in {ttl_hours}h)")
        
        logger.info(f"Cached response for idempotency key: {idempotency_key[:8]}... (expires in {ttl_hours}h)")
    


# Global idempotency manager
idempotency_manager = IdempotencyManager()

def idempotent(ttl_hours: Optional[int] = None):
    """Decorator to make endpoints idempotent"""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not config.ENABLE_IDEMPOTENCY:
                return f(*args, **kwargs)
            
            # Check for idempotency key
            idempotency_key = request.headers.get('Idempotency-Key')
            if not idempotency_key:
                return f(*args, **kwargs)
            
            # Generate request hash
            method = request.method
            path = request.path
            body = idempotency_manager._normalize_body(request.get_data())
            user_id = request.headers.get('X-User-ID')
            tenant_id = request.headers.get('X-Tenant-ID')
            
            request_hash = idempotency_manager._generate_key(method, path, body, user_id, tenant_id)
            
            # Check cache first
            cached_response = idempotency_manager.get_cached_response(request_hash)
            if cached_response:
                response = jsonify(json.loads(cached_response['response_body']))
                response.status_code = cached_response['status_code']
                response.headers['Idempotent-Replay'] = 'true'
                return response
            
            # Check database as fallback for durable idempotency
            try:
                with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT status_code, response_body, expires_at, is_replay
                        FROM idempotency_keys 
                        WHERE idempotency_key = ? AND expires_at > ?
                    ''', (request_hash, datetime.now().isoformat()))
                    
                    row = cursor.fetchone()
                    if row:
                        status_code, response_body, expires_at, is_replay = row
                        response = jsonify(json.loads(response_body))
                        response.status_code = status_code
                        response.headers['Idempotent-Replay'] = 'true'
                        logger.info(f"Returning cached response from database for idempotency key: {idempotency_key[:8]}...")
                        return response
                        
            except Exception as e:
                logger.warning(f"Database idempotency check failed: {e}")
            
            # Execute the original function
            try:
                result = f(*args, **kwargs)
                
                # Cache the response
                if hasattr(result, 'get_data'):
                    response_body = result.get_data(as_text=True)
                    status_code = result.status_code
                else:
                    response_body = json.dumps(result)
                    status_code = 200
                
                # Cache in memory and database for durability
                body_hash = hashlib.sha256(body.encode()).hexdigest()
                idempotency_manager.cache_response(
                    request_hash, status_code, response_body, 
                    method, path, body_hash, user_id, tenant_id, ttl_hours
                )
                
                return result
                
            except Exception as e:
                logger.error(f"Idempotent request failed: {e}")
                raise
        
        return decorated_function
    return decorator

def require_idempotency_key(f: Callable) -> Callable:
    """Decorator to require idempotency key for mutating operations"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not config.ENABLE_IDEMPOTENCY:
            return f(*args, **kwargs)
        
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return jsonify({
                'error': 'Idempotency-Key header required for this operation',
                'code': 'IDEMPOTENCY_KEY_REQUIRED'
            }), 400
        
        if len(idempotency_key) < 8 or len(idempotency_key) > 255:
            return jsonify({
                'error': 'Idempotency-Key must be between 8 and 255 characters',
                'code': 'INVALID_IDEMPOTENCY_KEY'
            }), 400
        
        return f(*args, **kwargs)
    
    return decorated_function
