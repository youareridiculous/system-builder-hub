"""
Configuration package
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Application configuration."""
    database_url: str = "sqlite:///system_builder_hub.db"
    secret_key: str = "dev-secret-key"
    debug: bool = False
    
    @classmethod
    def from_env(cls):
        """Create config from environment variables."""
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///system_builder_hub.db"),
            secret_key=os.getenv("SECRET_KEY", "dev-secret-key"),
            debug=os.getenv("DEBUG", "false").lower() == "true"
        )


# Global config instance
config = Config.from_env()
