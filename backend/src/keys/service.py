"""
API keys service
"""
import os
import secrets
import string
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from src.db_core import get_session
from src.integrations.models import ApiKey
import bcrypt

logger = logging.getLogger(__name__)

class ApiKeyService:
    """API key management service"""
    
    def __init__(self):
        self.env = os.environ.get('ENV', 'development')
        self.hash_scheme = os.environ.get('KEY_HASH_SCHEME', 'bcrypt')
    
    def create_key(self, tenant_id: str, name: str, scope: Dict = None, rate_limit_per_min: int = 120) -> Dict:
        """Create a new API key"""
        try:
            session = get_session()
            
            # Generate key components
            prefix = f"sbh_{self.env[:4]}_"
            random_part = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(22))
            full_key = prefix + random_part
            
            # Hash the key
            if self.hash_scheme == 'bcrypt':
                salt = bcrypt.gensalt()
                key_hash = bcrypt.hashpw(full_key.encode('utf-8'), salt).decode('utf-8')
            else:
                raise ValueError(f"Unsupported hash scheme: {self.hash_scheme}")
            
            # Create API key record
            api_key = ApiKey(
                tenant_id=tenant_id,
                name=name,
                prefix=prefix,
                hash=key_hash,
                scope=scope or {},
                rate_limit_per_min=rate_limit_per_min
            )
            
            session.add(api_key)
            session.commit()
            session.refresh(api_key)
            
            logger.info(f"Created API key '{name}' for tenant {tenant_id}")
            
            return {
                'id': str(api_key.id),
                'name': api_key.name,
                'prefix': api_key.prefix,
                'key': full_key,  # Show once only
                'scope': api_key.scope,
                'rate_limit_per_min': api_key.rate_limit_per_min,
                'created_at': api_key.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            raise
    
    def verify_key(self, raw_key: str) -> Optional[Tuple[str, Dict]]:
        """Verify API key and return (tenant_id, scopes)"""
        try:
            session = get_session()
            
            # Extract prefix
            if not raw_key.startswith('sbh_'):
                return None
            
            prefix = raw_key[:8]  # e.g., "sbh_dev_"
            
            # Find key by prefix
            api_key = session.query(ApiKey).filter(
                ApiKey.prefix == prefix,
                ApiKey.status == 'active'
            ).first()
            
            if not api_key:
                return None
            
            # Verify hash
            if self.hash_scheme == 'bcrypt':
                if not bcrypt.checkpw(raw_key.encode('utf-8'), api_key.hash.encode('utf-8')):
                    return None
            else:
                return None
            
            # Update last used
            api_key.last_used_at = datetime.utcnow()
            session.commit()
            
            return str(api_key.tenant_id), api_key.scope
            
        except Exception as e:
            logger.error(f"Error verifying API key: {e}")
            return None
    
    def rotate_key(self, key_id: str) -> Dict:
        """Rotate API key (revoke old, create new)"""
        try:
            session = get_session()
            
            # Get existing key
            api_key = session.query(ApiKey).filter(ApiKey.id == key_id).first()
            if not api_key:
                raise ValueError(f"API key {key_id} not found")
            
            # Revoke old key
            api_key.status = 'revoked'
            session.commit()
            
            # Create new key with same parameters
            new_key_data = self.create_key(
                tenant_id=str(api_key.tenant_id),
                name=f"{api_key.name} (rotated)",
                scope=api_key.scope,
                rate_limit_per_min=api_key.rate_limit_per_min
            )
            
            logger.info(f"Rotated API key {key_id}")
            
            return new_key_data
            
        except Exception as e:
            logger.error(f"Error rotating API key {key_id}: {e}")
            raise
    
    def revoke_key(self, key_id: str) -> bool:
        """Revoke API key"""
        try:
            session = get_session()
            
            api_key = session.query(ApiKey).filter(ApiKey.id == key_id).first()
            if not api_key:
                return False
            
            api_key.status = 'revoked'
            session.commit()
            
            logger.info(f"Revoked API key {key_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error revoking API key {key_id}: {e}")
            return False
    
    def list_keys(self, tenant_id: str) -> List[Dict]:
        """List API keys for tenant"""
        try:
            session = get_session()
            
            api_keys = session.query(ApiKey).filter(
                ApiKey.tenant_id == tenant_id
            ).order_by(ApiKey.created_at.desc()).all()
            
            result = []
            for key in api_keys:
                result.append({
                    'id': str(key.id),
                    'name': key.name,
                    'prefix': key.prefix,
                    'scope': key.scope,
                    'rate_limit_per_min': key.rate_limit_per_min,
                    'status': key.status,
                    'last_used_at': key.last_used_at.isoformat() if key.last_used_at else None,
                    'created_at': key.created_at.isoformat()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing API keys for tenant {tenant_id}: {e}")
            return []
    
    def touch_last_used(self, key_id: str) -> bool:
        """Update last used timestamp"""
        try:
            session = get_session()
            
            api_key = session.query(ApiKey).filter(ApiKey.id == key_id).first()
            if not api_key:
                return False
            
            api_key.last_used_at = datetime.utcnow()
            session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating last used for API key {key_id}: {e}")
            return False
    
    def get_key_by_id(self, key_id: str) -> Optional[ApiKey]:
        """Get API key by ID"""
        try:
            session = get_session()
            return session.query(ApiKey).filter(ApiKey.id == key_id).first()
        except Exception as e:
            logger.error(f"Error getting API key {key_id}: {e}")
            return None
