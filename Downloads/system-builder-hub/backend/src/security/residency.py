"""
Data residency management
"""
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from src.analytics.service import AnalyticsService

logger = logging.getLogger(__name__)

@dataclass
class RegionConfig:
    """Region configuration"""
    region: str
    s3_bucket: str
    s3_prefix: str
    database_url: Optional[str] = None
    enabled: bool = True

class DataResidencyManager:
    """Data residency manager"""
    
    def __init__(self):
        self.analytics = AnalyticsService()
        
        # Region configurations
        self.regions = {
            'us-east-1': RegionConfig(
                region='us-east-1',
                s3_bucket='sbh-files-us-east-1',
                s3_prefix='files/',
                enabled=True
            ),
            'us-west-2': RegionConfig(
                region='us-west-2',
                s3_bucket='sbh-files-us-west-2',
                s3_prefix='files/',
                enabled=True
            ),
            'eu-west-1': RegionConfig(
                region='eu-west-1',
                s3_bucket='sbh-files-eu-west-1',
                s3_prefix='files/',
                enabled=True
            ),
            'ap-southeast-1': RegionConfig(
                region='ap-southeast-1',
                s3_bucket='sbh-files-ap-southeast-1',
                s3_prefix='files/',
                enabled=True
            )
        }
        
        # Default region
        self.default_region = 'us-east-1'
    
    def get_tenant_region(self, tenant_id: str) -> str:
        """Get region for tenant"""
        try:
            # In a real implementation, this would query the database
            # For now, use a simple mapping based on tenant ID
            if 'eu' in tenant_id.lower():
                return 'eu-west-1'
            elif 'ap' in tenant_id.lower():
                return 'ap-southeast-1'
            elif 'west' in tenant_id.lower():
                return 'us-west-2'
            else:
                return self.default_region
        except Exception as e:
            logger.error(f"Error getting tenant region: {e}")
            return self.default_region
    
    def get_region_config(self, region: str) -> Optional[RegionConfig]:
        """Get region configuration"""
        return self.regions.get(region)
    
    def get_storage_config(self, tenant_id: str) -> Dict[str, Any]:
        """Get storage configuration for tenant"""
        try:
            region = self.get_tenant_region(tenant_id)
            config = self.get_region_config(region)
            
            if not config:
                logger.warning(f"No config found for region {region}, using default")
                config = self.get_region_config(self.default_region)
            
            return {
                'region': config.region,
                'bucket': config.s3_bucket,
                'prefix': f"{config.s3_prefix}{tenant_id}/",
                'enabled': config.enabled
            }
        except Exception as e:
            logger.error(f"Error getting storage config: {e}")
            return self.get_storage_config(self.default_region)
    
    def validate_region_access(self, tenant_id: str, region: str) -> bool:
        """Validate that tenant can access region"""
        try:
            tenant_region = self.get_tenant_region(tenant_id)
            return tenant_region == region
        except Exception as e:
            logger.error(f"Error validating region access: {e}")
            return False
    
    def track_region_access(self, tenant_id: str, region: str, operation: str, success: bool):
        """Track region access for audit"""
        try:
            self.analytics.track(
                tenant_id=tenant_id,
                event='residency.region_access',
                user_id='system',
                source='security',
                props={
                    'region': region,
                    'operation': operation,
                    'success': success,
                    'tenant_region': self.get_tenant_region(tenant_id)
                }
            )
        except Exception as e:
            logger.error(f"Error tracking region access: {e}")
    
    def get_presigned_url_config(self, tenant_id: str, file_path: str) -> Dict[str, Any]:
        """Get presigned URL configuration for file"""
        try:
            storage_config = self.get_storage_config(tenant_id)
            
            return {
                'bucket': storage_config['bucket'],
                'key': f"{storage_config['prefix']}{file_path}",
                'region': storage_config['region'],
                'expires_in': 3600  # 1 hour
            }
        except Exception as e:
            logger.error(f"Error getting presigned URL config: {e}")
            return {}
    
    def get_backup_storage_config(self, tenant_id: str) -> Dict[str, Any]:
        """Get backup storage configuration"""
        try:
            storage_config = self.get_storage_config(tenant_id)
            
            return {
                'bucket': storage_config['bucket'],
                'prefix': f"{storage_config['prefix']}backups/",
                'region': storage_config['region']
            }
        except Exception as e:
            logger.error(f"Error getting backup storage config: {e}")
            return {}

# Global residency manager
residency_manager = DataResidencyManager()
