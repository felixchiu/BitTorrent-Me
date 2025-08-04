"""
Download-related data models and state management
"""

import asyncio
import threading
import time
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from concurrent.futures import ThreadPoolExecutor

from ..config.settings import Config
from .torrent import TorrentFile, Piece
from .api import DownloadSettings

logger = logging.getLogger(__name__)


class DownloadState(ABC):
    """Abstract download state"""
    
    @abstractmethod
    def start(self, download: 'Download') -> bool:
        """Start download from this state"""
        pass
    
    @abstractmethod
    def pause(self, download: 'Download') -> bool:
        """Pause download from this state"""
        pass
    
    @abstractmethod
    def resume(self, download: 'Download') -> bool:
        """Resume download from this state"""
        pass
    
    @abstractmethod
    def stop(self, download: 'Download') -> bool:
        """Stop download from this state"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get state name"""
        pass


class StoppedState(DownloadState):
    """Download is stopped"""
    
    def start(self, download: 'Download') -> bool:
        download.state = DownloadingState()
        download.downloading = True
        download.paused = False
        return True
    
    def pause(self, download: 'Download') -> bool:
        return False  # Cannot pause stopped download
    
    def resume(self, download: 'Download') -> bool:
        return False  # Cannot resume stopped download
    
    def stop(self, download: 'Download') -> bool:
        return False  # Already stopped
    
    def get_name(self) -> str:
        return "stopped"


class DownloadingState(DownloadState):
    """Download is active"""
    
    def start(self, download: 'Download') -> bool:
        return False  # Already started
    
    def pause(self, download: 'Download') -> bool:
        download.state = PausedState()
        download.paused = True
        return True
    
    def resume(self, download: 'Download') -> bool:
        return False  # Already downloading
    
    def stop(self, download: 'Download') -> bool:
        download.state = StoppedState()
        download.downloading = False
        download.paused = False
        return True
    
    def get_name(self) -> str:
        return "downloading"


class PausedState(DownloadState):
    """Download is paused"""
    
    def start(self, download: 'Download') -> bool:
        return False  # Cannot start paused download
    
    def pause(self, download: 'Download') -> bool:
        return False  # Already paused
    
    def resume(self, download: 'Download') -> bool:
        download.state = DownloadingState()
        download.paused = False
        return True
    
    def stop(self, download: 'Download') -> bool:
        download.state = StoppedState()
        download.downloading = False
        download.paused = False
        return True
    
    def get_name(self) -> str:
        return "paused"


class CompletedState(DownloadState):
    """Download is completed"""
    
    def start(self, download: 'Download') -> bool:
        return False  # Cannot restart completed download
    
    def pause(self, download: 'Download') -> bool:
        return False  # Cannot pause completed download
    
    def resume(self, download: 'Download') -> bool:
        return False  # Cannot resume completed download
    
    def stop(self, download: 'Download') -> bool:
        return False  # Cannot stop completed download
    
    def get_name(self) -> str:
        return "completed"


class Download:
    """Represents a download with enhanced controls"""
    
    def __init__(self, torrent_id: str, name: str, total_size: int, pieces: List[Piece], 
                 download_dir: Path, settings: DownloadSettings, is_multi_file: bool = False):
        self.torrent_id = torrent_id
        self.name = name
        self.total_size = total_size
        self.pieces = pieces
        self.download_dir = download_dir
        self.settings = settings
        self.is_multi_file = is_multi_file
        self.files: List[TorrentFile] = []
        
        # State
        self.downloading = False
        self.paused = False
        self.download_progress = 0.0
        self.download_speed = 0.0
        self.upload_speed = 0.0
        self.downloaded_size = 0
        self.start_time: Optional[float] = None
        self.completed = False
        self.downloaded_pieces: Set[int] = set()
        
        # Threading
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        
        # Paths
        self.download_folder = download_dir / torrent_id
        self.download_folder.mkdir(exist_ok=True)
        self.state_file = self.download_folder / "state.json"
        
        # State management
        self.state: DownloadState = StoppedState()
        
        self.load_state()
    
    def add_files(self, files_info: List[Dict]) -> None:
        """Add file information to the download"""
        offset = 0
        for file_info in files_info:
            path_parts = file_info[b'path']
            if isinstance(path_parts[0], bytes):
                path_parts = [part.decode('utf-8') for part in path_parts]
            
            file_path = '/'.join(path_parts)
            torrent_file = TorrentFile(
                path=file_path,
                length=file_info[b'length'],
                offset=offset
            )
            self.files.append(torrent_file)
            offset += file_info[b'length']
    
    def get_file_selection(self) -> Dict[str, Any]:
        """Get current file selection status"""
        return {
            'files': [f.to_dict() for f in self.files]
        }
    
    def update_file_selection(self, file_selections: Dict[str, bool]) -> bool:
        """Update which files are selected for download"""
        try:
            for file_path, selected in file_selections.items():
                for file in self.files:
                    if file.path == file_path:
                        file.selected = selected
                        break
            self.save_state()
            return True
        except Exception as e:
            logger.error(f"Error updating file selection: {e}")
            return False
    
    def load_state(self) -> None:
        """Load download state from file"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.downloaded_pieces = set(state.get('downloaded_pieces', []))
                    self.downloaded_size = state.get('downloaded_size', 0)
                    self.completed = state.get('completed', False)
                    
                    # Load file selections
                    file_selections = state.get('file_selections', {})
                    for file in self.files:
                        if file.path in file_selections:
                            file.selected = file_selections[file.path]
                    
                    self.download_progress = len(self.downloaded_pieces) / len(self.pieces) * 100 if self.pieces else 0
                    logger.info(f"Loaded state for {self.name}: {len(self.downloaded_pieces)} pieces downloaded")
        except Exception as e:
            logger.error(f"Error loading state for {self.name}: {e}")
    
    def save_state(self) -> None:
        """Save download state to file"""
        try:
            file_selections = {file.path: file.selected for file in self.files}
            state = {
                'downloaded_pieces': list(self.downloaded_pieces),
                'downloaded_size': self.downloaded_size,
                'completed': self.completed,
                'file_selections': file_selections,
                'timestamp': time.time()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state for {self.name}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current download status"""
        with self.lock:
            return {
                'torrent_id': self.torrent_id,
                'name': self.name,
                'downloading': self.downloading,
                'paused': self.paused,
                'progress': round(self.download_progress, 2),
                'downloaded_pieces': len(self.downloaded_pieces),
                'total_pieces': len(self.pieces),
                'download_dir': str(self.download_dir),
                'download_folder': str(self.download_folder),
                'download_speed': round(self.download_speed, 2),
                'upload_speed': round(self.upload_speed, 2),
                'total_size': self.total_size,
                'downloaded_size': self.downloaded_size,
                'completed': self.completed,
                'settings': self.settings.dict(),
                'is_multi_file': self.is_multi_file,
                'files': [f.to_dict() for f in self.files]
            }
    
    async def start_download(self) -> bool:
        """Start the download process"""
        if self.completed:
            logger.info(f"Download {self.name} already completed")
            return True
        
        return self.state.start(self)
    
    async def pause_download(self) -> bool:
        """Pause the download"""
        if not self.downloading:
            return False
        return self.state.pause(self)
    
    async def resume_download(self) -> bool:
        """Resume the download"""
        if not self.downloading or not self.paused:
            return False
        return self.state.resume(self)
    
    async def stop_download(self) -> bool:
        """Stop the download"""
        result = self.state.stop(self)
        self.save_state()
        logger.info(f"Download stopped: {self.name}")
        return result 