"""
Plugin secrets manager
"""
import logging
from typing import Optional, Dict, Any
from src.ext.models import PluginSecret
from src.database import db_session

logger = logging.getLogger(__name__)

class SecretsManager:
    """Plugin secrets manager"""
    
    def __init__(self, tenant_id: str, plugin_installation_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.plugin_installation_id = plugin_installation_id
    
    def get(self, key: str) -> Optional[str]:
        """Get a secret value"""
        try:
            with db_session() as session:
                secret = session.query(PluginSecret).filter(
                    PluginSecret.tenant_id == self.tenant_id,
                    PluginSecret.plugin_installation_id == self.plugin_installation_id,
                    PluginSecret.key == key
                ).first()
                
                if secret:
                    # In a real implementation, this would decrypt the value
                    return secret.value_encrypted
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting secret {key}: {e}")
            return None
    
    def set(self, key: str, value: str) -> bool:
        """Set a secret value"""
        try:
            with db_session() as session:
                # In a real implementation, this would encrypt the value
                encrypted_value = value
                
                secret = session.query(PluginSecret).filter(
                    PluginSecret.tenant_id == self.tenant_id,
                    PluginSecret.plugin_installation_id == self.plugin_installation_id,
                    PluginSecret.key == key
                ).first()
                
                if secret:
                    secret.value_encrypted = encrypted_value
                    secret.updated_at = datetime.utcnow()
                else:
                    secret = PluginSecret(
                        tenant_id=self.tenant_id,
                        plugin_installation_id=self.plugin_installation_id,
                        key=key,
                        value_encrypted=encrypted_value
                    )
                    session.add(secret)
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error setting secret {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a secret"""
        try:
            with db_session() as session:
                secret = session.query(PluginSecret).filter(
                    PluginSecret.tenant_id == self.tenant_id,
                    PluginSecret.plugin_installation_id == self.plugin_installation_id,
                    PluginSecret.key == key
                ).first()
                
                if secret:
                    session.delete(secret)
                    session.commit()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error deleting secret {key}: {e}")
            return False
    
    def list(self) -> Dict[str, str]:
        """List all secrets"""
        try:
            with db_session() as session:
                secrets = session.query(PluginSecret).filter(
                    PluginSecret.tenant_id == self.tenant_id,
                    PluginSecret.plugin_installation_id == self.plugin_installation_id
                ).all()
                
                return {
                    secret.key: secret.value_encrypted
                    for secret in secrets
                }
                
        except Exception as e:
            logger.error(f"Error listing secrets: {e}")
            return {}
