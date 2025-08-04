"""
Unit tests for configuration module
"""

import pytest
from pathlib import Path

from src.config.settings import Settings, Config


class TestSettings:
    """Test Settings class"""
    
    def test_settings_defaults(self):
        """Test default settings values"""
        settings = Settings()
        
        assert settings.download_dir == Path("./downloads")
        assert settings.max_concurrent_downloads == 5
        assert settings.default_speed_limit == 0
        assert settings.host == "0.0.0.0"
        assert settings.port == 5001
        assert settings.reload is True
        assert settings.log_level == "INFO"
        assert settings.batch_size == 20
        assert settings.simulation_delay == 0.005
    
    def test_settings_custom_values(self):
        """Test custom settings values"""
        settings = Settings(
            download_dir=Path("/custom/downloads"),
            max_concurrent_downloads=10,
            default_speed_limit=1024,
            host="127.0.0.1",
            port=8080,
            reload=False,
            log_level="DEBUG"
        )
        
        assert settings.download_dir == Path("/custom/downloads")
        assert settings.max_concurrent_downloads == 10
        assert settings.default_speed_limit == 1024
        assert settings.host == "127.0.0.1"
        assert settings.port == 8080
        assert settings.reload is False
        assert settings.log_level == "DEBUG"
    
    def test_settings_environment_variables(self, monkeypatch):
        """Test settings from environment variables"""
        monkeypatch.setenv("BT_DOWNLOAD_DIR", "/env/downloads")
        monkeypatch.setenv("BT_MAX_CONCURRENT_DOWNLOADS", "15")
        monkeypatch.setenv("BT_DEFAULT_SPEED_LIMIT", "2048")
        monkeypatch.setenv("BT_HOST", "0.0.0.0")
        monkeypatch.setenv("BT_PORT", "9000")
        monkeypatch.setenv("BT_LOG_LEVEL", "WARNING")
        
        settings = Settings()
        
        assert settings.download_dir == Path("/env/downloads")
        assert settings.max_concurrent_downloads == 15
        assert settings.default_speed_limit == 2048
        assert settings.host == "0.0.0.0"
        assert settings.port == 9000
        assert settings.log_level == "WARNING"


class TestConfig:
    """Test Config class"""
    
    def test_config_constants(self):
        """Test configuration constants"""
        assert Config.DEFAULT_DOWNLOAD_DIR == Path("downloads")
        assert Config.PIECE_SIZE == 16384
        assert Config.MAX_CONCURRENT_DOWNLOADS == 5
        assert Config.CHUNK_SIZE == 1024 * 1024
        assert Config.BATCH_SIZE == 20
        assert Config.SIMULATION_DELAY == 0.005
        assert Config.DEFAULT_DOWNLOAD_SPEED_LIMIT == 0
        assert Config.DEFAULT_UPLOAD_SPEED_LIMIT == 0
        assert Config.DEFAULT_MAX_PEERS == 50
        assert Config.DEFAULT_MAX_CONNECTIONS == 100
        assert Config.DEFAULT_PIECE_TIMEOUT == 30
        assert Config.DEFAULT_REQUEST_TIMEOUT == 60
    
    def test_config_get_settings(self):
        """Test get_settings method"""
        settings = Config.get_settings()
        
        assert isinstance(settings, Settings)
        assert settings.download_dir == Path("./downloads")
        assert settings.host == "0.0.0.0"
        assert settings.port == 5001
    
    def test_config_ensure_directories(self, temp_dir):
        """Test ensure_directories method"""
        settings = Settings(
            download_dir=temp_dir / "test_downloads",
            log_file=temp_dir / "test.log"
        )
        
        # Ensure directories don't exist initially
        assert not settings.download_dir.exists()
        assert not settings.log_file.parent.exists()
        
        # Call ensure_directories
        Config.ensure_directories(settings)
        
        # Check directories were created
        assert settings.download_dir.exists()
        assert settings.log_file.parent.exists()
    
    def test_config_ensure_directories_existing(self, temp_dir):
        """Test ensure_directories with existing directories"""
        settings = Settings(
            download_dir=temp_dir / "existing_downloads",
            log_file=temp_dir / "existing.log"
        )
        
        # Create directories manually
        settings.download_dir.mkdir()
        settings.log_file.parent.mkdir()
        
        # Call ensure_directories (should not fail)
        Config.ensure_directories(settings)
        
        # Check directories still exist
        assert settings.download_dir.exists()
        assert settings.log_file.parent.exists() 