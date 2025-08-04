"""
Unit tests for data models
"""

import pytest
from pathlib import Path

from src.models.api import DownloadSettings, FileSelection, DownloadDirectory
from src.models.torrent import TorrentFile, Piece, TorrentInfo
from src.models.download import Download, StoppedState, DownloadingState, PausedState, CompletedState


class TestDownloadSettings:
    """Test DownloadSettings model"""
    
    def test_download_settings_defaults(self):
        """Test default download settings"""
        settings = DownloadSettings()
        
        assert settings.speed_limit == 0
        assert settings.upload_limit == 0
        assert settings.max_peers == 50
        assert settings.max_connections == 100
        assert settings.piece_timeout == 30
        assert settings.request_timeout == 60
        assert settings.auto_stop is True
        assert settings.sequential_download is False
        assert settings.verify_pieces is True
        assert settings.pre_allocate is True
    
    def test_download_settings_custom(self):
        """Test custom download settings"""
        settings = DownloadSettings(
            speed_limit=1024,
            upload_limit=512,
            max_peers=100,
            max_connections=200,
            piece_timeout=60,
            request_timeout=120,
            auto_stop=False,
            sequential_download=True,
            verify_pieces=False,
            pre_allocate=False
        )
        
        assert settings.speed_limit == 1024
        assert settings.upload_limit == 512
        assert settings.max_peers == 100
        assert settings.max_connections == 200
        assert settings.piece_timeout == 60
        assert settings.request_timeout == 120
        assert settings.auto_stop is False
        assert settings.sequential_download is True
        assert settings.verify_pieces is False
        assert settings.pre_allocate is False
    
    def test_download_settings_dict(self):
        """Test download settings to dict conversion"""
        settings = DownloadSettings(speed_limit=1024, auto_stop=False)
        settings_dict = settings.dict()
        
        assert settings_dict['speed_limit'] == 1024
        assert settings_dict['auto_stop'] is False
        assert 'max_peers' in settings_dict
        assert 'verify_pieces' in settings_dict


class TestFileSelection:
    """Test FileSelection model"""
    
    def test_file_selection(self):
        """Test file selection model"""
        file_selection = FileSelection(
            file_selections={
                "file1.txt": True,
                "file2.txt": False,
                "file3.txt": True
            }
        )
        
        assert file_selection.file_selections["file1.txt"] is True
        assert file_selection.file_selections["file2.txt"] is False
        assert file_selection.file_selections["file3.txt"] is True


class TestDownloadDirectory:
    """Test DownloadDirectory model"""
    
    def test_download_directory(self):
        """Test download directory model"""
        directory = DownloadDirectory(directory="/custom/downloads")
        
        assert directory.directory == "/custom/downloads"


class TestTorrentFile:
    """Test TorrentFile model"""
    
    def test_torrent_file(self):
        """Test torrent file model"""
        torrent_file = TorrentFile(
            path="test/file.txt",
            length=1024,
            offset=0,
            downloaded=False,
            selected=True
        )
        
        assert torrent_file.path == "test/file.txt"
        assert torrent_file.length == 1024
        assert torrent_file.offset == 0
        assert torrent_file.downloaded is False
        assert torrent_file.selected is True
    
    def test_torrent_file_to_dict(self):
        """Test torrent file to dict conversion"""
        torrent_file = TorrentFile(
            path="test/file.txt",
            length=1024,
            offset=512,
            downloaded=True,
            selected=False
        )
        
        file_dict = torrent_file.to_dict()
        
        assert file_dict['path'] == "test/file.txt"
        assert file_dict['length'] == 1024
        assert file_dict['offset'] == 512
        assert file_dict['downloaded'] is True
        assert file_dict['selected'] is False


class TestPiece:
    """Test Piece model"""
    
    def test_piece(self):
        """Test piece model"""
        piece = Piece(
            index=0,
            size=16384,
            hash=b'0' * 20,
            data=b'test data',
            downloaded=False
        )
        
        assert piece.index == 0
        assert piece.size == 16384
        assert piece.hash == b'0' * 20
        assert piece.data == b'test data'
        assert piece.downloaded is False
    
    def test_piece_to_dict(self):
        """Test piece to dict conversion"""
        piece = Piece(
            index=1,
            size=16384,
            hash=b'1' * 20,
            data=b'test data',
            downloaded=True
        )
        
        piece_dict = piece.to_dict()
        
        assert piece_dict['index'] == 1
        assert piece_dict['size'] == 16384
        assert piece_dict['hash'] == '1' * 40  # hex string
        assert piece_dict['downloaded'] is True


class TestTorrentInfo:
    """Test TorrentInfo model"""
    
    def test_torrent_info(self):
        """Test torrent info model"""
        pieces = [
            Piece(index=0, size=16384, hash=b'0' * 20),
            Piece(index=1, size=16384, hash=b'1' * 20)
        ]
        
        files = [
            TorrentFile(path="file1.txt", length=1024, offset=0),
            TorrentFile(path="file2.txt", length=1024, offset=1024)
        ]
        
        torrent_info = TorrentInfo(
            name="test.torrent",
            total_size=2048,
            piece_length=16384,
            pieces=pieces,
            files=files,
            is_multi_file=True,
            info_hash=b'info' * 5
        )
        
        assert torrent_info.name == "test.torrent"
        assert torrent_info.total_size == 2048
        assert torrent_info.piece_length == 16384
        assert len(torrent_info.pieces) == 2
        assert len(torrent_info.files) == 2
        assert torrent_info.is_multi_file is True
        assert torrent_info.info_hash == b'info' * 5
    
    def test_torrent_info_to_dict(self):
        """Test torrent info to dict conversion"""
        pieces = [Piece(index=0, size=16384, hash=b'0' * 20)]
        files = [TorrentFile(path="file1.txt", length=1024, offset=0)]
        
        torrent_info = TorrentInfo(
            name="test.torrent",
            total_size=1024,
            piece_length=16384,
            pieces=pieces,
            files=files,
            is_multi_file=False,
            info_hash=b'info' * 5
        )
        
        info_dict = torrent_info.to_dict()
        
        assert info_dict['name'] == "test.torrent"
        assert info_dict['total_size'] == 1024
        assert info_dict['piece_length'] == 16384
        assert len(info_dict['pieces']) == 1
        assert len(info_dict['files']) == 1
        assert info_dict['is_multi_file'] is False
        assert info_dict['info_hash'] == 'info' * 10  # hex string


class TestDownloadStates:
    """Test download state classes"""
    
    def test_stopped_state(self):
        """Test stopped state"""
        state = StoppedState()
        download = Mock()
        download.downloading = False
        download.paused = False
        
        # Test start
        result = state.start(download)
        assert result is True
        assert download.downloading is True
        assert download.paused is False
        
        # Test pause (should fail)
        result = state.pause(download)
        assert result is False
    
    def test_downloading_state(self):
        """Test downloading state"""
        state = DownloadingState()
        download = Mock()
        download.downloading = True
        download.paused = False
        
        # Test pause
        result = state.pause(download)
        assert result is True
        assert download.paused is True
        
        # Test stop
        result = state.stop(download)
        assert result is True
        assert download.downloading is False
        assert download.paused is False
    
    def test_paused_state(self):
        """Test paused state"""
        state = PausedState()
        download = Mock()
        download.downloading = True
        download.paused = True
        
        # Test resume
        result = state.resume(download)
        assert result is True
        assert download.paused is False
    
    def test_completed_state(self):
        """Test completed state"""
        state = CompletedState()
        download = Mock()
        download.completed = True
        
        # All operations should fail
        assert state.start(download) is False
        assert state.pause(download) is False
        assert state.resume(download) is False
        assert state.stop(download) is False


class TestDownload:
    """Test Download model"""
    
    def test_download_creation(self, download_settings):
        """Test download creation"""
        from src.models.torrent import Piece
        
        pieces = [
            Piece(index=0, size=16384, hash=b'0' * 20),
            Piece(index=1, size=16384, hash=b'1' * 20)
        ]
        
        download = Download(
            torrent_id="test123",
            name="test.torrent",
            total_size=32768,
            pieces=pieces,
            download_dir=Path("./downloads"),
            settings=download_settings,
            is_multi_file=False
        )
        
        assert download.torrent_id == "test123"
        assert download.name == "test.torrent"
        assert download.total_size == 32768
        assert len(download.pieces) == 2
        assert download.settings == download_settings
        assert download.is_multi_file is False
        assert download.downloading is False
        assert download.paused is False
        assert download.completed is False
        assert download.download_progress == 0.0
    
    def test_download_add_files(self, download_settings):
        """Test adding files to download"""
        from src.models.torrent import Piece
        
        pieces = [Piece(index=0, size=16384, hash=b'0' * 20)]
        
        download = Download(
            torrent_id="test123",
            name="test.torrent",
            total_size=16384,
            pieces=pieces,
            download_dir=Path("./downloads"),
            settings=download_settings,
            is_multi_file=True
        )
        
        files_info = [
            {b'path': [b'file1.txt'], b'length': 8192},
            {b'path': [b'file2.txt'], b'length': 8192}
        ]
        
        download.add_files(files_info)
        
        assert len(download.files) == 2
        assert download.files[0].path == "file1.txt"
        assert download.files[0].length == 8192
        assert download.files[1].path == "file2.txt"
        assert download.files[1].length == 8192
    
    def test_download_get_status(self, download_settings):
        """Test getting download status"""
        from src.models.torrent import Piece
        
        pieces = [Piece(index=0, size=16384, hash=b'0' * 20)]
        
        download = Download(
            torrent_id="test123",
            name="test.torrent",
            total_size=16384,
            pieces=pieces,
            download_dir=Path("./downloads"),
            settings=download_settings,
            is_multi_file=False
        )
        
        status = download.get_status()
        
        assert status['torrent_id'] == "test123"
        assert status['name'] == "test.torrent"
        assert status['downloading'] is False
        assert status['paused'] is False
        assert status['progress'] == 0.0
        assert status['total_pieces'] == 1
        assert status['total_size'] == 16384
        assert status['completed'] is False
        assert 'settings' in status
        assert status['is_multi_file'] is False


# Mock class for testing
class Mock:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value) 