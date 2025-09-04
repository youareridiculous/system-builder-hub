"""
Environment Profiles

Defines environment-specific configurations for different deployment targets.
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class EnvironmentProfile:
    """Environment-specific configuration profile"""
    name: str
    database_path: str
    debug: bool
    secret_key: str
    cors_origins: list
    rate_limits: Dict[str, int]
    logging_level: str
    feature_flags: list
    security_settings: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary"""
        return asdict(self)
    
    def to_env_file(self) -> str:
        """Generate .env file content"""
        env_lines = [
            f"# Environment: {self.name}",
            f"FLASK_ENV={self.name}",
            f"DEBUG={str(self.debug).lower()}",
            f"DATABASE={self.database_path}",
            f"SECRET_KEY={self.secret_key}",
            f"CORS_ORIGINS={','.join(self.cors_origins)}",
            f"LOG_LEVEL={self.logging_level}",
            ""
        ]
        
        # Add rate limits
        for endpoint, limit in self.rate_limits.items():
            env_lines.append(f"RATE_LIMIT_{endpoint.upper()}={limit}")
        
        # Add feature flags
        for flag in self.feature_flags:
            env_lines.append(f"FEATURE_{flag.upper()}=true")
        
        # Add security settings
        for key, value in self.security_settings.items():
            if isinstance(value, bool):
                env_lines.append(f"SECURITY_{key.upper()}={str(value).lower()}")
            else:
                env_lines.append(f"SECURITY_{key.upper()}={value}")
        
        return "\n".join(env_lines)

def get_environment_profile(environment: str) -> EnvironmentProfile:
    """Get environment profile by name"""
    profiles = {
        "local": EnvironmentProfile(
            name="local",
            database_path="./data/local.db",
            debug=True,
            secret_key="dev-secret-key-change-in-production",
            cors_origins=["*"],
            rate_limits={
                "api": 1000,
                "cobuilder": 100,
                "marketplace": 500,
                "ecosystem": 200
            },
            logging_level="DEBUG",
            feature_flags=[
                "cross_module_sync",
                "unified_dashboard",
                "advanced_analytics",
                "ai_features"
            ],
            security_settings={
                "jwt_expiration_hours": 24,
                "password_min_length": 8,
                "session_timeout_minutes": 480,
                "max_login_attempts": 10,
                "audit_logging": True,
                "rate_limiting": True
            }
        ),
        "staging": EnvironmentProfile(
            name="staging",
            database_path="/data/staging.db",
            debug=False,
            secret_key=os.getenv("STAGING_SECRET_KEY", "staging-secret-key"),
            cors_origins=[
                "https://staging.example.com",
                "https://staging-api.example.com"
            ],
            rate_limits={
                "api": 500,
                "cobuilder": 50,
                "marketplace": 200,
                "ecosystem": 100
            },
            logging_level="INFO",
            feature_flags=[
                "cross_module_sync",
                "unified_dashboard",
                "advanced_analytics"
            ],
            security_settings={
                "jwt_expiration_hours": 12,
                "password_min_length": 10,
                "session_timeout_minutes": 240,
                "max_login_attempts": 5,
                "audit_logging": True,
                "rate_limiting": True
            }
        ),
        "production": EnvironmentProfile(
            name="production",
            database_path="/data/production.db",
            debug=False,
            secret_key=os.getenv("PRODUCTION_SECRET_KEY", "production-secret-key"),
            cors_origins=[
                "https://example.com",
                "https://api.example.com"
            ],
            rate_limits={
                "api": 200,
                "cobuilder": 20,
                "marketplace": 100,
                "ecosystem": 50
            },
            logging_level="WARNING",
            feature_flags=[
                "cross_module_sync",
                "unified_dashboard"
            ],
            security_settings={
                "jwt_expiration_hours": 4,
                "password_min_length": 12,
                "session_timeout_minutes": 120,
                "max_login_attempts": 3,
                "audit_logging": True,
                "rate_limiting": True,
                "ssl_required": True,
                "secure_cookies": True
            }
        )
    }
    
    return profiles.get(environment, profiles["local"])

def list_environments() -> list:
    """List all available environments"""
    return ["local", "staging", "production"]

def validate_environment(environment: str) -> bool:
    """Validate environment name"""
    return environment in list_environments()

def get_environment_summary(environment: str) -> Dict[str, Any]:
    """Get summary of environment configuration"""
    profile = get_environment_profile(environment)
    
    return {
        "name": profile.name,
        "database_path": profile.database_path,
        "debug": profile.debug,
        "cors_origins_count": len(profile.cors_origins),
        "rate_limits": profile.rate_limits,
        "logging_level": profile.logging_level,
        "feature_flags_count": len(profile.feature_flags),
        "security_features": list(profile.security_settings.keys())
    }

def generate_env_file(environment: str, output_path: str = None) -> str:
    """Generate .env file for specified environment"""
    profile = get_environment_profile(environment)
    env_content = profile.to_env_file()
    
    if output_path:
        try:
            with open(output_path, 'w') as f:
                f.write(env_content)
            logger.info(f"Generated .env file: {output_path}")
        except Exception as e:
            logger.error(f"Failed to write .env file: {e}")
    
    return env_content

def get_environment_overrides(environment: str) -> Dict[str, str]:
    """Get environment-specific overrides for CI/CD"""
    overrides = {
        "local": {},
        "staging": {
            "SECRET_KEY": "${STAGING_SECRET_KEY}",
            "DATABASE_URL": "${STAGING_DATABASE_URL}",
            "REDIS_URL": "${STAGING_REDIS_URL}"
        },
        "production": {
            "SECRET_KEY": "${PRODUCTION_SECRET_KEY}",
            "DATABASE_URL": "${PRODUCTION_DATABASE_URL}",
            "REDIS_URL": "${PRODUCTION_REDIS_URL}",
            "SENTRY_DSN": "${SENTRY_DSN}",
            "LOG_LEVEL": "ERROR"
        }
    }
    
    return overrides.get(environment, {})

def merge_environment_config(base_config: Dict[str, Any], environment: str) -> Dict[str, Any]:
    """Merge base configuration with environment-specific overrides"""
    profile = get_environment_profile(environment)
    overrides = get_environment_overrides(environment)
    
    # Start with base config
    merged = base_config.copy()
    
    # Apply environment profile
    merged.update({
        "environment": environment,
        "debug": profile.debug,
        "database_path": profile.database_path,
        "logging_level": profile.logging_level,
        "feature_flags": profile.feature_flags,
        "security_settings": profile.security_settings
    })
    
    # Apply CI/CD overrides
    for key, value in overrides.items():
        if key in merged:
            merged[key] = value
    
    return merged
