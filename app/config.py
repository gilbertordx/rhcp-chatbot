"""
Environment-based configuration for RHCP chatbot.
"""

import os
from dataclasses import dataclass
from typing import Optional

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not available, continue without it
    pass


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""
    
    # Environment
    env: str = "dev"
    debug: bool = False
    
    # Server
    port: int = 3000
    host: str = "0.0.0.0"
    
    # Database
    database_url: str = "sqlite:///./data/rhcp.sqlite3"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Authentication
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    bcrypt_rounds: int = 12
    
    # ML Model
    model_path: str = "data/model.bin"
    
    # Data paths
    band_info_path: str = "app/chatbot/data/static/band-info.json"
    discography_path: str = "app/chatbot/data/static/discography.json"
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        return cls(
            env=os.getenv("RHCP_ENV", "dev"),
            debug=os.getenv("RHCP_DEBUG", "false").lower() == "true",
            port=int(os.getenv("RHCP_PORT", "3000")),
            host=os.getenv("RHCP_HOST", "0.0.0.0"),
            database_url=os.getenv("RHCP_DB_URL", "sqlite:///./data/rhcp.sqlite3"),
            log_level=os.getenv("RHCP_LOG_LEVEL", "INFO"),
            log_format=os.getenv("RHCP_LOG_FORMAT", "json"),
            secret_key=os.getenv("RHCP_SECRET_KEY", "your-secret-key-change-in-production"),
            algorithm=os.getenv("RHCP_ALGORITHM", "HS256"),
            access_token_expire_minutes=int(os.getenv("RHCP_ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
            bcrypt_rounds=int(os.getenv("RHCP_BCRYPT_ROUNDS", "12")),
            model_path=os.getenv("RHCP_MODEL_PATH", "data/model.bin"),
            band_info_path=os.getenv("RHCP_BAND_INFO_PATH", "app/chatbot/data/static/band-info.json"),
            discography_path=os.getenv("RHCP_DISCOGRAPHY_PATH", "app/chatbot/data/static/discography.json"),
        )
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.env.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.env.lower() in ("dev", "development")
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port number: {self.port}")
        
        if self.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError(f"Invalid log level: {self.log_level}")
        
        if self.log_format not in ("json", "human"):
            raise ValueError(f"Invalid log format: {self.log_format}")
        
        if self.access_token_expire_minutes < 1:
            raise ValueError(f"Invalid access token expire minutes: {self.access_token_expire_minutes}")
        
        if self.bcrypt_rounds < 4 or self.bcrypt_rounds > 31:
            raise ValueError(f"Invalid bcrypt rounds: {self.bcrypt_rounds}")


# Global settings instance (immutable after initialization)
_settings: Optional[Settings] = None


def get_settings(reload: bool = False) -> Settings:
    """Get the global settings instance.
    
    Args:
        reload: Force reload settings from environment variables
    """
    global _settings
    if _settings is None or reload:
        _settings = Settings.from_env()
        _settings.validate()
    return _settings


def initialize_settings(settings: Settings) -> None:
    """Initialize global settings (for testing)."""
    global _settings
    _settings = settings 