"""
Configuration settings for Modern BitTorrent Client
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application settings
    download_dir: Path = Field(default=Path("./downloads"), description="Download directory")
    max_concurrent_downloads: int = Field(default=5, description="Maximum concurrent downloads")
    default_speed_limit: int = Field(default=0, description="Default speed limit (0 = unlimited)")
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=5001, description="Server port")
    reload: bool = Field(default=True, description="Auto-reload in development")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Path = Field(default=Path("bittorrent.log"), description="Log file path")
    
    # Performance settings
    batch_size: int = Field(default=20, description="Batch size for processing")
    simulation_delay: float = Field(default=0.005, description="Simulation delay in seconds")
    chunk_size: int = Field(default=1024 * 1024, description="Chunk size for file writing")
    piece_size: int = Field(default=16384, description="Piece size in bytes")
    
    # Download settings
    default_auto_stop: bool = Field(default=True, description="Auto-stop after completion")
    default_verify_pieces: bool = Field(default=True, description="Verify piece hashes")
    default_pre_allocate: bool = Field(default=True, description="Pre-allocate disk space")
    default_max_peers: int = Field(default=50, description="Default max peers")
    default_max_connections: int = Field(default=100, description="Default max connections")
    
    class Config:
        env_prefix = "BT_"
        case_sensitive = False


class Config:
    """Static configuration constants"""
    
    # Ensure directories exist
    @classmethod
    def ensure_directories(cls, settings: Settings) -> None:
        """Ensure all required directories exist"""
        settings.download_dir.mkdir(exist_ok=True)
        settings.log_file.parent.mkdir(exist_ok=True)
    
    # Default settings
    DEFAULT_DOWNLOAD_DIR = Path("downloads")
    PIECE_SIZE = 16384  # 16KB pieces
    STATE_FILE = Path("download_state.json")
    MAX_CONCURRENT_DOWNLOADS = 5
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for file writing
    BATCH_SIZE = 20  # Process 20 pieces at a time
    SIMULATION_DELAY = 0.005  # 5ms delay per piece for simulation
    
    # Download Settings
    DEFAULT_DOWNLOAD_SPEED_LIMIT = 0  # 0 = unlimited
    DEFAULT_UPLOAD_SPEED_LIMIT = 0  # 0 = unlimited
    DEFAULT_MAX_PEERS = 50
    DEFAULT_MAX_CONNECTIONS = 100
    DEFAULT_PIECE_TIMEOUT = 30  # seconds
    DEFAULT_REQUEST_TIMEOUT = 60  # seconds
    
    @classmethod
    def get_settings(cls) -> Settings:
        """Get application settings"""
        settings = Settings()
        cls.ensure_directories(settings)
        return settings 