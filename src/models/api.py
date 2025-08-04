"""
API models for request/response handling
"""

from typing import Dict
from pydantic import BaseModel, Field


class FileSelection(BaseModel):
    """File selection model for multi-file torrents"""
    file_selections: Dict[str, bool] = Field(..., description="File path to selection mapping")


class DownloadDirectory(BaseModel):
    """Download directory configuration"""
    directory: str = Field(..., description="Download directory path")


class TorrentUpload(BaseModel):
    """Torrent upload configuration"""
    auto_stop: bool = Field(default=True, description="Auto-stop after completion")


class DownloadSettings(BaseModel):
    """Download configuration settings"""
    speed_limit: int = Field(default=0, description="Download speed limit in KB/s (0 = unlimited)")
    upload_limit: int = Field(default=0, description="Upload speed limit in KB/s (0 = unlimited)")
    max_peers: int = Field(default=50, description="Maximum number of peers")
    max_connections: int = Field(default=100, description="Maximum connections")
    piece_timeout: int = Field(default=30, description="Piece timeout in seconds")
    request_timeout: int = Field(default=60, description="Request timeout in seconds")
    auto_stop: bool = Field(default=True, description="Auto-stop after completion")
    sequential_download: bool = Field(default=False, description="Download pieces sequentially")
    verify_pieces: bool = Field(default=True, description="Verify piece hashes")
    pre_allocate: bool = Field(default=True, description="Pre-allocate disk space")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Application status")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="Application version")
    uptime: int = Field(..., description="Uptime in seconds")
    active_downloads: int = Field(..., description="Number of active downloads")
    memory_usage: float = Field(..., description="Memory usage percentage")
    cpu_usage: float = Field(..., description="CPU usage percentage")


class MetricsResponse(BaseModel):
    """Metrics response"""
    downloads: Dict[str, int] = Field(..., description="Download statistics")
    performance: Dict[str, float] = Field(..., description="Performance metrics")
    system: Dict[str, float] = Field(..., description="System metrics") 