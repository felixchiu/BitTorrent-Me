"""
Pytest configuration and fixtures
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

from src.config.settings import Settings
from src.models.api import DownloadSettings
from src.core.bit_torrent_client import BitTorrentClient


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def settings(temp_dir):
    """Create test settings"""
    return Settings(
        download_dir=temp_dir / "downloads",
        log_level="DEBUG",
        log_file=temp_dir / "test.log"
    )


@pytest.fixture
def download_settings():
    """Create test download settings"""
    return DownloadSettings(
        speed_limit=1024,
        upload_limit=512,
        max_peers=50,
        max_connections=100,
        auto_stop=True,
        verify_pieces=True,
        pre_allocate=True
    )


@pytest.fixture
def client(settings):
    """Create test BitTorrent client"""
    return BitTorrentClient(settings)


@pytest.fixture
def mock_torrent_file(temp_dir):
    """Create a mock torrent file for testing"""
    import bencodepy
    
    # Create a simple test torrent
    info = {
        b'name': b'test.torrent',
        b'piece length': 16384,
        b'length': 1024,
        b'pieces': b'0' * 20
    }
    
    torrent_data = {
        b'announce': b'http://localhost:8080/announce',
        b'info': info
    }
    
    torrent_file = temp_dir / "test.torrent"
    with open(torrent_file, 'wb') as f:
        f.write(bencodepy.encode(torrent_data))
    
    return torrent_file


@pytest.fixture
def mock_multi_file_torrent(temp_dir):
    """Create a mock multi-file torrent for testing"""
    import bencodepy
    
    # Create a multi-file test torrent
    info = {
        b'name': b'test_folder',
        b'piece length': 16384,
        b'files': [
            {
                b'path': [b'file1.txt'],
                b'length': 512
            },
            {
                b'path': [b'file2.txt'],
                b'length': 512
            }
        ],
        b'pieces': b'0' * 20
    }
    
    torrent_data = {
        b'announce': b'http://localhost:8080/announce',
        b'info': info
    }
    
    torrent_file = temp_dir / "test_multi.torrent"
    with open(torrent_file, 'wb') as f:
        f.write(bencodepy.encode(torrent_data))
    
    return torrent_file


@pytest.fixture
def mock_download():
    """Create a mock download object"""
    from src.models.download import Download
    from src.models.torrent import Piece
    
    # Create mock pieces
    pieces = [
        Piece(index=0, size=16384, hash=b'0' * 20),
        Piece(index=1, size=16384, hash=b'1' * 20),
        Piece(index=2, size=16384, hash=b'2' * 20)
    ]
    
    settings = DownloadSettings()
    download = Download(
        torrent_id="test123",
        name="test.torrent",
        total_size=49152,
        pieces=pieces,
        download_dir=Path("./downloads"),
        settings=settings,
        is_multi_file=False
    )
    
    return download


@pytest.fixture
def mock_download_worker(mock_download):
    """Create a mock download worker"""
    from src.core.download_worker import DownloadWorker
    
    return DownloadWorker(mock_download)


@pytest.fixture
def mock_file_service():
    """Create a mock file service"""
    from src.services.file_service import FileService
    
    return FileService()


@pytest.fixture
def mock_torrent_service():
    """Create a mock torrent service"""
    from src.services.torrent_service import TorrentService
    
    return TorrentService()


@pytest.fixture
def mock_download_service(settings):
    """Create a mock download service"""
    from src.services.download_service import DownloadService
    
    return DownloadService(settings) 