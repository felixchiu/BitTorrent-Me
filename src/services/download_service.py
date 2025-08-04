"""
Download service for managing download operations
"""

import asyncio
import json
import logging
import os
import random
import string
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

from ..models.download import Download
from ..models.torrent import TorrentInfo
from ..models.api import DownloadSettings
from ..config.settings import Config, Settings

logger = logging.getLogger(__name__)


class DownloadService:
    """Service for managing download operations"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.downloads: Dict[str, Download] = {}
        self.logger = logging.getLogger(__name__)
        self.state_file = Path("download_state.json")
        
        # Load existing downloads
        self.load_downloads()
    
    def _generate_peer_id(self) -> bytes:
        """Generate a unique peer ID"""
        return ('-PY0001-' + ''.join(random.choices(string.ascii_letters + string.digits, k=12))).encode()
    
    def create_download(self, torrent_info: TorrentInfo, settings: DownloadSettings) -> Optional[str]:
        """Create a new download"""
        try:
            torrent_id = torrent_info.info_hash.hex()[:16]
            
            # Check if download already exists
            if torrent_id in self.downloads:
                self.logger.info(f"Download already exists for {torrent_id}")
                return torrent_id
            
            # Create download object
            download = Download(
                torrent_id=torrent_id,
                name=torrent_info.name,
                total_size=torrent_info.total_size,
                pieces=torrent_info.pieces,
                download_dir=self.settings.download_dir,
                settings=settings,
                is_multi_file=torrent_info.is_multi_file
            )
            
            # Add files for multi-file torrents
            if torrent_info.is_multi_file:
                files_info = []
                for file in torrent_info.files:
                    files_info.append({
                        b'path': file.path.split('/'),
                        b'length': file.length
                    })
                download.add_files(files_info)
            
            self.downloads[torrent_id] = download
            self.save_downloads_state()
            
            self.logger.info(f"Created download: {torrent_info.name}")
            return torrent_id
            
        except Exception as e:
            self.logger.error(f"Error creating download: {e}")
            return None
    
    def get_download(self, torrent_id: str) -> Optional[Download]:
        """Get download by ID"""
        return self.downloads.get(torrent_id)
    
    def get_all_downloads(self) -> Dict[str, Download]:
        """Get all downloads"""
        return self.downloads
    
    def get_download_status(self, torrent_id: str) -> Optional[Dict[str, Any]]:
        """Get download status"""
        download = self.get_download(torrent_id)
        if download:
            return download.get_status()
        return None
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all downloads"""
        return {
            torrent_id: download.get_status()
            for torrent_id, download in self.downloads.items()
        }
    
    async def start_download(self, torrent_id: str) -> bool:
        """Start a specific download"""
        download = self.get_download(torrent_id)
        if not download:
            return False
        
        return await download.start_download()
    
    async def pause_download(self, torrent_id: str) -> bool:
        """Pause a specific download"""
        download = self.get_download(torrent_id)
        if not download:
            return False
        
        return await download.pause_download()
    
    async def resume_download(self, torrent_id: str) -> bool:
        """Resume a specific download"""
        download = self.get_download(torrent_id)
        if not download:
            return False
        
        return await download.resume_download()
    
    async def stop_download(self, torrent_id: str) -> bool:
        """Stop a specific download"""
        download = self.get_download(torrent_id)
        if not download:
            return False
        
        return await download.stop_download()
    
    def remove_download(self, torrent_id: str) -> bool:
        """Remove a download completely"""
        download = self.get_download(torrent_id)
        if not download:
            return False
        
        try:
            # Stop download if running
            asyncio.create_task(download.stop_download())
            
            # Remove download folder
            if download.download_folder.exists():
                import shutil
                shutil.rmtree(download.download_folder)
            
            # Remove from downloads dict
            del self.downloads[torrent_id]
            self.save_downloads_state()
            
            self.logger.info(f"Removed download: {torrent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing download: {e}")
            return False
    
    def update_download_settings(self, torrent_id: str, settings: DownloadSettings) -> bool:
        """Update download settings"""
        download = self.get_download(torrent_id)
        if not download:
            return False
        
        download.settings = settings
        self.save_downloads_state()
        return True
    
    def get_file_selection(self, torrent_id: str) -> Optional[Dict[str, Any]]:
        """Get file selection for a specific download"""
        download = self.get_download(torrent_id)
        if not download:
            return None
        return download.get_file_selection()
    
    def update_file_selection(self, torrent_id: str, file_selections: Dict[str, bool]) -> bool:
        """Update file selection for a specific download"""
        download = self.get_download(torrent_id)
        if not download:
            return False
        return download.update_file_selection(file_selections)
    
    def load_downloads(self) -> None:
        """Load existing downloads from disk"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    for torrent_id, download_info in state.get('downloads', {}).items():
                        if Path(download_info['state_file']).exists():
                            # Convert pieces back to proper format
                            pieces = []
                            for piece_info in download_info['pieces']:
                                from ..models.torrent import Piece
                                piece = Piece(
                                    index=piece_info['index'],
                                    size=piece_info['size'],
                                    hash=bytes.fromhex(piece_info['hash']) if isinstance(piece_info['hash'], str) else piece_info['hash'],
                                    downloaded=piece_info.get('downloaded', False)
                                )
                                pieces.append(piece)
                            
                            # Load settings
                            settings_data = download_info.get('settings', {})
                            settings = DownloadSettings(**settings_data)
                            
                            download = Download(
                                torrent_id=torrent_id,
                                name=download_info['name'],
                                total_size=download_info['total_size'],
                                pieces=pieces,
                                download_dir=Path(download_info['download_dir']),
                                settings=settings,
                                is_multi_file=download_info.get('is_multi_file', False)
                            )
                            
                            # Load files if multi-file
                            if download.is_multi_file and 'files' in download_info:
                                download.files = []
                                for file_info in download_info['files']:
                                    from ..models.torrent import TorrentFile
                                    torrent_file = TorrentFile(
                                        path=file_info['path'],
                                        length=file_info['length'],
                                        offset=file_info.get('offset', 0)
                                    )
                                    torrent_file.selected = file_info.get('selected', True)
                                    download.files.append(torrent_file)
                            
                            self.downloads[torrent_id] = download
                            self.logger.info(f"Loaded download: {download_info['name']}")
        except Exception as e:
            self.logger.error(f"Error loading downloads: {e}")
    
    def save_downloads_state(self) -> None:
        """Save downloads state to disk"""
        try:
            state = {'downloads': {}}
            for torrent_id, download in self.downloads.items():
                # Convert pieces to JSON-serializable format
                serializable_pieces = [piece.to_dict() for piece in download.pieces]
                
                download_info = {
                    'name': download.name,
                    'total_size': download.total_size,
                    'pieces': serializable_pieces,
                    'download_dir': str(download.download_dir),
                    'state_file': str(download.state_file),
                    'settings': download.settings.dict(),
                    'is_multi_file': download.is_multi_file
                }
                
                # Save file information for multi-file torrents
                if download.is_multi_file:
                    download_info['files'] = [f.to_dict() for f in download.files]
                
                state['downloads'][torrent_id] = download_info
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving downloads state: {e}")
    
    def set_download_directory(self, directory: str) -> bool:
        """Set custom download directory"""
        try:
            download_path = Path(directory)
            download_path.mkdir(exist_ok=True)
            self.logger.info(f"Created download directory: {download_path}")
            self.settings.download_dir = download_path
            return True
        except Exception as e:
            self.logger.error(f"Error setting download directory: {e}")
            return False
    
    def get_download_directory(self) -> str:
        """Get current download directory"""
        return str(self.settings.download_dir) 