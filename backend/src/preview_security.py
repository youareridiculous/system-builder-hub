#!/usr/bin/env python3
"""
Preview Security & Isolation Module
Implements short-lived signed JWTs, egress allowlists, and container runtime verification.
"""

import os
import json
import time
import logging
import threading
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from urllib.parse import urlparse
import subprocess
import tempfile

from flask import request, current_app, g
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

@dataclass
class PreviewJWTClaims:
    """Preview JWT claims structure"""
    preview_id: str
    tenant_id: str
    user_id: str
    system_id: str
    device_preset: str
    exp: int
    iat: int
    iss: str = "sbh-preview"
    aud: str = "sbh-preview-client"

@dataclass
class ContainerLimits:
    """Container resource limits"""
    cpu_limit: str
    memory_limit: str
    network_mode: str = "bridge"
    security_opts: List[str] = None

class PreviewSecurityManager:
    """Manages preview security, isolation, and JWT handling"""
    
    def __init__(self):
        self.jwt_secret = self._generate_or_load_jwt_secret()
        self.jwt_rotation_interval = 24 * 60 * 60  # 24 hours
        self.last_key_rotation = time.time()
        self.key_lock = threading.Lock()
        
        # Egress allowlist - deny-all by default
        self.egress_allowlist = self._load_egress_allowlist()
        self.egress_denylist = self._load_egress_denylist()
        
        # Container runtime verification
        self.container_limits = self._load_container_limits()
        self.runtime_verification_enabled = True
        
        # Start key rotation background task
        self._start_key_rotation_task()
    
    def _generate_or_load_jwt_secret(self) -> bytes:
        """Generate or load JWT signing secret"""
        secret_file = os.path.join(tempfile.gettempdir(), 'sbh_preview_jwt_secret')
        
        if os.path.exists(secret_file):
            with open(secret_file, 'rb') as f:
                return f.read()
        else:
            # Generate new secret
            secret = os.urandom(32)
            with open(secret_file, 'wb') as f:
                f.write(secret)
            logger.info("Generated new preview JWT secret")
            return secret
    
    def _rotate_jwt_secret(self):
        """Rotate JWT signing secret"""
        with self.key_lock:
            new_secret = os.urandom(32)
            old_secret = self.jwt_secret
            self.jwt_secret = new_secret
            
            # Save new secret
            secret_file = os.path.join(tempfile.gettempdir(), 'sbh_preview_jwt_secret')
            with open(secret_file, 'wb') as f:
                f.write(new_secret)
            
            self.last_key_rotation = time.time()
            logger.info("Rotated preview JWT secret")
            
            # Invalidate existing tokens by updating rotation timestamp
            return old_secret, new_secret
    
    def _start_key_rotation_task(self):
        """Start background task for key rotation"""
        def rotation_worker():
            while True:
                time.sleep(60)  # Check every minute
                if time.time() - self.last_key_rotation > self.jwt_rotation_interval:
                    self._rotate_jwt_secret()
        
        thread = threading.Thread(target=rotation_worker, daemon=True)
        thread.start()
    
    def _load_egress_allowlist(self) -> Set[str]:
        """Load egress allowlist from environment"""
        allowlist_str = os.getenv('PREVIEW_EGRESS_ALLOWLIST', '')
        if not allowlist_str:
            return set()
        
        domains = set()
        for domain in allowlist_str.split(','):
            domain = domain.strip().lower()
            if domain:
                domains.add(domain)
        
        logger.info(f"Loaded egress allowlist: {domains}")
        return domains
    
    def _load_egress_denylist(self) -> Set[str]:
        """Load egress denylist from environment"""
        denylist_str = os.getenv('PREVIEW_EGRESS_DENYLIST', '')
        if not denylist_str:
            return set()
        
        domains = set()
        for domain in denylist_str.split(','):
            domain = domain.strip().lower()
            if domain:
                domains.add(domain)
        
        logger.info(f"Loaded egress denylist: {domains}")
        return domains
    
    def _load_container_limits(self) -> ContainerLimits:
        """Load container resource limits"""
        return ContainerLimits(
            cpu_limit=os.getenv('PREVIEW_CPU_LIMIT', '0.5'),
            memory_limit=os.getenv('PREVIEW_MEM_LIMIT', '512m'),
            network_mode=os.getenv('PREVIEW_NETWORK_MODE', 'bridge'),
            security_opts=os.getenv('PREVIEW_SECURITY_OPTS', '').split(',') if os.getenv('PREVIEW_SECURITY_OPTS') else None
        )
    
    def generate_preview_jwt(self, preview_id: str, tenant_id: str, user_id: str, 
                           system_id: str, device_preset: str, ttl_minutes: int = 60) -> str:
        """Generate short-lived JWT for preview access"""
        now = int(time.time())
        exp = now + (ttl_minutes * 60)
        
        claims = PreviewJWTClaims(
            preview_id=preview_id,
            tenant_id=tenant_id,
            user_id=user_id,
            system_id=system_id,
            device_preset=device_preset,
            exp=exp,
            iat=now
        )
        
        # Create JWT payload
        header = {
            "alg": "HS256",
            "typ": "JWT"
        }
        
        payload = {
            "preview_id": claims.preview_id,
            "tenant_id": claims.tenant_id,
            "user_id": claims.user_id,
            "system_id": claims.system_id,
            "device_preset": claims.device_preset,
            "exp": claims.exp,
            "iat": claims.iat,
            "iss": claims.iss,
            "aud": claims.aud
        }
        
        # Encode header and payload
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b'=').decode()
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=').decode()
        
        # Create signature
        message = f"{header_b64}.{payload_b64}".encode()
        with self.key_lock:
            signature = hmac.new(self.jwt_secret, message, hashlib.sha256).digest()
        
        signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()
        
        # Return JWT
        jwt = f"{header_b64}.{payload_b64}.{signature_b64}"
        
        logger.info(f"Generated preview JWT for {preview_id}, expires in {ttl_minutes} minutes")
        return jwt
    
    def verify_preview_jwt(self, jwt: str) -> Optional[PreviewJWTClaims]:
        """Verify and decode preview JWT"""
        try:
            parts = jwt.split('.')
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, signature_b64 = parts
            
            # Decode header and payload
            header = json.loads(base64.urlsafe_b64decode(header_b64 + '===').decode())
            payload = json.loads(base64.urlsafe_b64decode(payload_b64 + '===').decode())
            
            # Verify signature
            message = f"{header_b64}.{payload_b64}".encode()
            with self.key_lock:
                expected_signature = hmac.new(self.jwt_secret, message, hashlib.sha256).digest()
            
            provided_signature = base64.urlsafe_b64decode(signature_b64 + '===')
            
            if not hmac.compare_digest(expected_signature, provided_signature):
                logger.warning("Invalid JWT signature")
                return None
            
            # Check expiration
            now = int(time.time())
            if payload.get('exp', 0) < now:
                logger.warning("JWT expired")
                return None
            
            # Check issuer and audience
            if payload.get('iss') != 'sbh-preview' or payload.get('aud') != 'sbh-preview-client':
                logger.warning("Invalid JWT issuer or audience")
                return None
            
            # Convert to claims object
            claims = PreviewJWTClaims(
                preview_id=payload['preview_id'],
                tenant_id=payload['tenant_id'],
                user_id=payload['user_id'],
                system_id=payload['system_id'],
                device_preset=payload['device_preset'],
                exp=payload['exp'],
                iat=payload['iat'],
                iss=payload['iss'],
                aud=payload['aud']
            )
            
            return claims
            
        except Exception as e:
            logger.error(f"JWT verification failed: {e}")
            return None
    
    def check_egress_permission(self, url: str) -> bool:
        """Check if egress to URL is allowed"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check denylist first (takes precedence)
            if domain in self.egress_denylist:
                logger.warning(f"Egress denied to denylisted domain: {domain}")
                return False
            
            # Check allowlist
            if not self.egress_allowlist:
                # Empty allowlist means deny-all
                logger.warning(f"Egress denied - no domains in allowlist: {domain}")
                return False
            
            if domain not in self.egress_allowlist:
                logger.warning(f"Egress denied to non-allowlisted domain: {domain}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking egress permission for {url}: {e}")
            return False
    
    def verify_container_limits(self, container_id: str) -> Dict[str, Any]:
        """Verify container resource limits are properly applied"""
        try:
            # Use docker inspect to verify limits
            cmd = [
                'docker', 'inspect', 
                '--format', '{{json .HostConfig}}',
                container_id
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return {
                    'verified': False,
                    'error': f'Failed to inspect container: {result.stderr}'
                }
            
            host_config = json.loads(result.stdout)
            
            # Check CPU limit
            cpu_quota = host_config.get('CpuQuota', 0)
            cpu_period = host_config.get('CpuPeriod', 100000)
            expected_cpu_quota = int(float(self.container_limits.cpu_limit) * cpu_period)
            
            # Check memory limit
            memory_limit = host_config.get('Memory', 0)
            expected_memory_limit = self._parse_memory_limit(self.container_limits.memory_limit)
            
            # Check network mode
            network_mode = host_config.get('NetworkMode', 'default')
            
            verification_result = {
                'verified': True,
                'cpu': {
                    'expected_quota': expected_cpu_quota,
                    'actual_quota': cpu_quota,
                    'period': cpu_period,
                    'correct': cpu_quota == expected_cpu_quota
                },
                'memory': {
                    'expected_limit': expected_memory_limit,
                    'actual_limit': memory_limit,
                    'correct': memory_limit == expected_memory_limit
                },
                'network': {
                    'expected_mode': self.container_limits.network_mode,
                    'actual_mode': network_mode,
                    'correct': network_mode == self.container_limits.network_mode
                }
            }
            
            # Overall verification
            verification_result['verified'] = (
                verification_result['cpu']['correct'] and
                verification_result['memory']['correct'] and
                verification_result['network']['correct']
            )
            
            return verification_result
            
        except Exception as e:
            return {
                'verified': False,
                'error': f'Container verification failed: {e}'
            }
    
    def _parse_memory_limit(self, memory_str: str) -> int:
        """Parse memory limit string to bytes"""
        memory_str = memory_str.lower().strip()
        
        if memory_str.endswith('b'):
            return int(memory_str[:-1])
        elif memory_str.endswith('k'):
            return int(memory_str[:-1]) * 1024
        elif memory_str.endswith('m'):
            return int(memory_str[:-1]) * 1024 * 1024
        elif memory_str.endswith('g'):
            return int(memory_str[:-1]) * 1024 * 1024 * 1024
        else:
            # Assume bytes
            return int(memory_str)
    
    def get_container_limits(self) -> ContainerLimits:
        """Get current container limits configuration"""
        return self.container_limits
    
    def update_egress_allowlist(self, domains: List[str]):
        """Update egress allowlist"""
        self.egress_allowlist = set(domain.lower().strip() for domain in domains if domain.strip())
        logger.info(f"Updated egress allowlist: {self.egress_allowlist}")
    
    def update_egress_denylist(self, domains: List[str]):
        """Update egress denylist"""
        self.egress_denylist = set(domain.lower().strip() for domain in domains if domain.strip())
        logger.info(f"Updated egress denylist: {self.egress_denylist}")

# Global instance
preview_security = PreviewSecurityManager()

def require_preview_auth(f):
    """Decorator to require valid preview JWT authentication"""
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return {'error': 'Missing or invalid Authorization header'}, 401
        
        jwt = auth_header[7:]  # Remove 'Bearer ' prefix
        claims = preview_security.verify_preview_jwt(jwt)
        
        if not claims:
            return {'error': 'Invalid or expired preview token'}, 401
        
        # Store claims in Flask g for access in route handlers
        g.preview_claims = claims
        
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function
