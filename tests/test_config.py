"""
Tests for environment-based configuration.
"""

import os
import pytest
from app.config import Settings, get_settings, initialize_settings


class TestSettings:
    """Test Settings dataclass and configuration loading."""
    
    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        
        assert settings.env == "dev"
        assert settings.debug is False
        assert settings.port == 3000
        assert settings.host == "0.0.0.0"
        assert settings.database_url == "sqlite:///./data/rhcp.sqlite3"
        assert settings.log_level == "INFO"
        assert settings.log_format == "json"
    
    def test_from_env_basic(self):
        """Test loading settings from environment variables."""
        # Set some environment variables
        os.environ["RHCP_ENV"] = "production"
        os.environ["RHCP_DEBUG"] = "true"
        os.environ["RHCP_PORT"] = "8080"
        os.environ["RHCP_LOG_LEVEL"] = "DEBUG"
        
        try:
            settings = Settings.from_env()
            
            assert settings.env == "production"
            assert settings.debug is True
            assert settings.port == 8080
            assert settings.log_level == "DEBUG"
        finally:
            # Clean up environment
            for key in ["RHCP_ENV", "RHCP_DEBUG", "RHCP_PORT", "RHCP_LOG_LEVEL"]:
                os.environ.pop(key, None)
    
    def test_environment_checks(self):
        """Test environment checking methods."""
        dev_settings = Settings(env="dev")
        prod_settings = Settings(env="production")
        
        assert dev_settings.is_development() is True
        assert dev_settings.is_production() is False
        
        assert prod_settings.is_development() is False
        assert prod_settings.is_production() is True
    
    def test_validation_valid(self):
        """Test settings validation with valid values."""
        settings = Settings(
            port=8080,
            log_level="DEBUG",
            log_format="human",
            access_token_expire_minutes=60,
            bcrypt_rounds=12
        )
        
        # Should not raise any exceptions
        settings.validate()
    
    def test_validation_invalid_port(self):
        """Test settings validation with invalid port."""
        settings = Settings(port=0)  # Invalid port
        
        with pytest.raises(ValueError, match="Invalid port number"):
            settings.validate()
    
    def test_validation_invalid_log_level(self):
        """Test settings validation with invalid log level."""
        settings = Settings(log_level="INVALID")
        
        with pytest.raises(ValueError, match="Invalid log level"):
            settings.validate()
    
    def test_validation_invalid_log_format(self):
        """Test settings validation with invalid log format."""
        settings = Settings(log_format="invalid")
        
        with pytest.raises(ValueError, match="Invalid log format"):
            settings.validate()
    
    def test_validation_invalid_token_expire(self):
        """Test settings validation with invalid token expire minutes."""
        settings = Settings(access_token_expire_minutes=0)
        
        with pytest.raises(ValueError, match="Invalid access token expire minutes"):
            settings.validate()
    
    def test_validation_invalid_bcrypt_rounds(self):
        """Test settings validation with invalid bcrypt rounds."""
        settings = Settings(bcrypt_rounds=3)  # Too low
        
        with pytest.raises(ValueError, match="Invalid bcrypt rounds"):
            settings.validate()
        
        settings = Settings(bcrypt_rounds=32)  # Too high
        
        with pytest.raises(ValueError, match="Invalid bcrypt rounds"):
            settings.validate()


class TestGetSettings:
    """Test global settings management."""
    
    def test_get_settings_default(self):
        """Test getting default settings."""
        # Clear any existing settings
        initialize_settings(None)
        
        settings = get_settings()
        
        assert settings.env == "dev"
        assert settings.debug is False
        assert settings.port == 3000
    
    def test_get_settings_cached(self):
        """Test that settings are cached after first call."""
        # Clear any existing settings
        initialize_settings(None)
        
        # First call should create settings
        settings1 = get_settings()
        
        # Second call should return same instance
        settings2 = get_settings()
        
        assert settings1 is settings2
    
    def test_initialize_settings(self):
        """Test manually initializing settings."""
        custom_settings = Settings(
            env="test",
            debug=True,
            port=9999
        )
        
        initialize_settings(custom_settings)
        
        settings = get_settings()
        assert settings is custom_settings
        assert settings.env == "test"
        assert settings.debug is True
        assert settings.port == 9999
    
    def test_immutable_settings(self):
        """Test that settings are immutable after initialization."""
        settings = get_settings()
        
        # Should not be able to modify frozen dataclass
        with pytest.raises(Exception):
            settings.env = "production" 