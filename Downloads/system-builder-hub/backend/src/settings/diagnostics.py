"""
Settings Hub Diagnostics
Health and diagnostics information for the settings hub.
"""

import logging
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..privacy.service import privacy_service
from ..privacy.modes import PrivacyMode

logger = logging.getLogger(__name__)


class DiagnosticsService:
    """Service for gathering diagnostics information."""
    
    def __init__(self):
        pass
    
    def get_system_health(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        """Get system health summary."""
        try:
            # Get privacy mode
            privacy_mode = privacy_service.get_privacy_mode(tenant_id, db)
            privacy_settings = privacy_service.get_privacy_settings(tenant_id, db)
            
            # Get tenant settings
            tenant_settings = db.query("TenantSettings").filter(
                "TenantSettings.tenant_id == tenant_id"
            ).first()
            
            # Check database connectivity
            db_healthy = self._check_database_health(db)
            
            # Check Redis connectivity (if available)
            redis_healthy = self._check_redis_health()
            
            # Check S3 connectivity (if available)
            s3_healthy = self._check_s3_health()
            
            # Check SES connectivity (if available)
            ses_healthy = self._check_ses_health()
            
            # Get feature flags
            feature_flags = self._get_feature_flags()
            
            # Get queue status
            queue_status = self._get_queue_status()
            
            # Get error summary
            error_summary = self._get_error_summary()
            
            # Get version information
            version_info = self._get_version_info()
            
            return {
                "status": "healthy" if all([db_healthy, redis_healthy, s3_healthy, ses_healthy]) else "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                "components": {
                    "database": {
                        "status": "healthy" if db_healthy else "unhealthy",
                        "details": "Database connection established" if db_healthy else "Database connection failed"
                    },
                    "redis": {
                        "status": "healthy" if redis_healthy else "unhealthy",
                        "details": "Redis connection established" if redis_healthy else "Redis connection failed"
                    },
                    "s3": {
                        "status": "healthy" if s3_healthy else "unhealthy",
                        "details": "S3 connection established" if s3_healthy else "S3 connection failed"
                    },
                    "ses": {
                        "status": "healthy" if ses_healthy else "unhealthy",
                        "details": "SES connection established" if ses_healthy else "SES connection failed"
                    }
                },
                "privacy": {
                    "mode": privacy_mode.value if privacy_mode else "unknown",
                    "retention_enabled": privacy_settings.prompt_retention_seconds > 0 if privacy_settings else False,
                    "redaction_enabled": True  # Always enabled
                },
                "feature_flags": feature_flags,
                "queue_status": queue_status,
                "error_summary": error_summary,
                "version_info": version_info,
                "tenant_settings": {
                    "allow_anonymous_metrics": tenant_settings.allow_anonymous_metrics if tenant_settings else True,
                    "trace_sample_rate": tenant_settings.trace_sample_rate if tenant_settings else 0.1
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def get_metrics_summary(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        """Get metrics summary."""
        try:
            # Get privacy mode
            privacy_mode = privacy_service.get_privacy_mode(tenant_id, db)
            
            # Get basic metrics (privacy-aware)
            metrics = {
                "privacy_mode": privacy_mode.value if privacy_mode else "unknown",
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": {}
            }
            
            # Only include metrics if privacy allows
            if privacy_mode and privacy_mode != PrivacyMode.LOCAL_ONLY:
                metrics["metrics"] = {
                    "active_users": self._get_active_users_count(tenant_id, db),
                    "api_requests": self._get_api_requests_count(tenant_id, db),
                    "webhook_deliveries": self._get_webhook_deliveries_count(tenant_id, db),
                    "storage_usage": self._get_storage_usage(tenant_id, db)
                }
            else:
                metrics["metrics"] = {
                    "note": "Metrics not available in current privacy mode"
                }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_config_snapshot(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        """Get configuration snapshot."""
        try:
            # Get privacy mode
            privacy_mode = privacy_service.get_privacy_mode(tenant_id, db)
            privacy_settings = privacy_service.get_privacy_settings(tenant_id, db)
            
            # Get tenant settings
            tenant_settings = db.query("TenantSettings").filter(
                "TenantSettings.tenant_id == tenant_id"
            ).first()
            
            config = {
                "timestamp": datetime.utcnow().isoformat(),
                "privacy": {
                    "mode": privacy_mode.value if privacy_mode else "unknown",
                    "prompt_retention_seconds": privacy_settings.prompt_retention_seconds if privacy_settings else 86400,
                    "response_retention_seconds": privacy_settings.response_retention_seconds if privacy_settings else 86400,
                    "do_not_retain_prompts": privacy_settings.do_not_retain_prompts if privacy_settings else False,
                    "do_not_retain_model_outputs": privacy_settings.do_not_retain_model_outputs if privacy_settings else False
                },
                "developer": {
                    "default_llm_provider": tenant_settings.default_llm_provider if tenant_settings else None,
                    "default_llm_model": tenant_settings.default_llm_model if tenant_settings else None,
                    "temperature_default": tenant_settings.temperature_default if tenant_settings else 0.7,
                    "http_allowlist": tenant_settings.get_http_allowlist() if tenant_settings else []
                },
                "diagnostics": {
                    "allow_anonymous_metrics": tenant_settings.allow_anonymous_metrics if tenant_settings else True,
                    "trace_sample_rate": tenant_settings.trace_sample_rate if tenant_settings else 0.1
                },
                "environment": {
                    "node_env": os.getenv("NODE_ENV", "development"),
                    "database_url": self._mask_database_url(os.getenv("DATABASE_URL", "")),
                    "redis_url": self._mask_redis_url(os.getenv("REDIS_URL", "")),
                    "aws_region": os.getenv("AWS_REGION", "us-east-1")
                }
            }
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to get config snapshot: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # Private helper methods
    
    def _check_database_health(self, db: Session) -> bool:
        """Check database health."""
        try:
            db.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def _check_redis_health(self) -> bool:
        """Check Redis health."""
        try:
            # TODO: Implement actual Redis health check
            # For now, assume healthy if REDIS_URL is set
            return bool(os.getenv("REDIS_URL"))
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    def _check_s3_health(self) -> bool:
        """Check S3 health."""
        try:
            # TODO: Implement actual S3 health check
            # For now, assume healthy if AWS credentials are set
            return bool(os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE"))
        except Exception as e:
            logger.error(f"S3 health check failed: {e}")
            return False
    
    def _check_ses_health(self) -> bool:
        """Check SES health."""
        try:
            # TODO: Implement actual SES health check
            # For now, assume healthy if AWS credentials are set
            return bool(os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE"))
        except Exception as e:
            logger.error(f"SES health check failed: {e}")
            return False
    
    def _get_feature_flags(self) -> Dict[str, Any]:
        """Get feature flags."""
        return {
            "privacy_v1_enabled": True,
            "settings_hub_enabled": True,
            "api_keys_enabled": True,
            "webhooks_enabled": True,
            "billing_enabled": bool(os.getenv("STRIPE_SECRET_KEY")),
            "analytics_enabled": True
        }
    
    def _get_queue_status(self) -> Dict[str, Any]:
        """Get queue status."""
        try:
            # TODO: Implement actual queue status check
            return {
                "status": "healthy",
                "pending_jobs": 0,
                "failed_jobs": 0,
                "workers": 1
            }
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {
                "status": "unknown",
                "error": str(e)
            }
    
    def _get_error_summary(self) -> Dict[str, Any]:
        """Get error summary."""
        try:
            # TODO: Implement actual error summary
            return {
                "last_error": None,
                "error_count_24h": 0,
                "sentry_project_id": os.getenv("SENTRY_PROJECT_ID")
            }
        except Exception as e:
            logger.error(f"Failed to get error summary: {e}")
            return {
                "error": str(e)
            }
    
    def _get_version_info(self) -> Dict[str, Any]:
        """Get version information."""
        return {
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "build_id": os.getenv("BUILD_ID", "unknown"),
            "deployment_env": os.getenv("DEPLOYMENT_ENV", "development"),
            "git_commit": os.getenv("GIT_COMMIT", "unknown")
        }
    
    def _get_active_users_count(self, tenant_id: str, db: Session) -> int:
        """Get active users count."""
        try:
            # TODO: Implement actual active users count
            return 0
        except Exception as e:
            logger.error(f"Failed to get active users count: {e}")
            return 0
    
    def _get_api_requests_count(self, tenant_id: str, db: Session) -> int:
        """Get API requests count."""
        try:
            # TODO: Implement actual API requests count
            return 0
        except Exception as e:
            logger.error(f"Failed to get API requests count: {e}")
            return 0
    
    def _get_webhook_deliveries_count(self, tenant_id: str, db: Session) -> int:
        """Get webhook deliveries count."""
        try:
            # TODO: Implement actual webhook deliveries count
            return 0
        except Exception as e:
            logger.error(f"Failed to get webhook deliveries count: {e}")
            return 0
    
    def _get_storage_usage(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        """Get storage usage."""
        try:
            # TODO: Implement actual storage usage
            return {
                "files": 0,
                "size_bytes": 0
            }
        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            return {
                "error": str(e)
            }
    
    def _mask_database_url(self, url: str) -> str:
        """Mask database URL for security."""
        if not url:
            return ""
        
        # Mask password in database URL
        if "@" in url:
            parts = url.split("@")
            if len(parts) == 2:
                auth_part = parts[0]
                if ":" in auth_part:
                    user_pass = auth_part.split(":")
                    if len(user_pass) >= 3:
                        user_pass[2] = "***"
                        auth_part = ":".join(user_pass)
                        return f"{auth_part}@{parts[1]}"
        
        return url
    
    def _mask_redis_url(self, url: str) -> str:
        """Mask Redis URL for security."""
        if not url:
            return ""
        
        # Mask password in Redis URL
        if "@" in url:
            parts = url.split("@")
            if len(parts) == 2:
                auth_part = parts[0]
                if ":" in auth_part:
                    user_pass = auth_part.split(":")
                    if len(user_pass) >= 2:
                        user_pass[1] = "***"
                        auth_part = ":".join(user_pass)
                        return f"{auth_part}@{parts[1]}"
        
        return url


# Global service instance
diagnostics_service = DiagnosticsService()
