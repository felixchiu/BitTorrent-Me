"""
Main BitTorrent client class
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..config.settings import Settings, Config
from ..models.torrent import TorrentInfo
from ..models.api import DownloadSettings
from ..models.download import Download
from ..services.torrent_service import TorrentService
from ..services.download_service import DownloadService
from ..services.file_service import FileService
from .download_worker import DownloadWorker

logger = logging.getLogger(__name__)


class BitTorrentClient:
    """Main BitTorrent client class"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Config.get_settings()
        self.torrent_service = TorrentService()
        self.download_service = DownloadService(self.settings)
        self.file_service = FileService()
        self.logger = logging.getLogger(__name__)
        
        # Ensure download directory exists
        self.settings.download_dir.mkdir(exist_ok=True)
        self.logger.info(f"Ensured download directory: {self.settings.download_dir}")
    
    def parse_torrent(self, torrent_file: Path, settings: Optional[DownloadSettings] = None) -> Tuple[Optional[str], bool]:
        """Parse torrent file and create download"""
        try:
            # Validate torrent file
            if not self.torrent_service.validate_torrent_file(torrent_file):
                self.logger.error(f"Invalid torrent file: {torrent_file}")
                return None, False
            
            # Parse torrent
            torrent_info = self.torrent_service.parse_torrent(torrent_file)
            if not torrent_info:
                self.logger.error(f"Failed to parse torrent: {torrent_file}")
                return None, False
            
            # Use default settings if none provided
            if settings is None:
                settings = DownloadSettings()
            
            # Create download
            torrent_id = self.download_service.create_download(torrent_info, settings)
            if not torrent_id:
                self.logger.error(f"Failed to create download for: {torrent_file}")
                return None, False
            
            self.logger.info(f"Successfully parsed torrent: {torrent_info.name}")
            return torrent_id, True
            
        except Exception as e:
            self.logger.error(f"Error parsing torrent: {e}")
            return None, False
    
    def get_download(self, torrent_id: str) -> Optional[Download]:
        """Get download by ID"""
        return self.download_service.get_download(torrent_id)
    
    def get_all_downloads(self) -> Dict[str, Download]:
        """Get all downloads"""
        return self.download_service.get_all_downloads()
    
    def get_download_status(self, torrent_id: str) -> Optional[Dict]:
        """Get download status"""
        return self.download_service.get_download_status(torrent_id)
    
    def get_all_status(self) -> Dict[str, Dict]:
        """Get status of all downloads"""
        return self.download_service.get_all_status()
    
    async def start_download(self, torrent_id: str) -> bool:
        """Start a specific download"""
        download = self.get_download(torrent_id)
        if not download:
            return False
        
        # Create and start download worker
        worker = DownloadWorker(download)
        success = await worker.start()
        
        if success:
            # Update download state
            download.downloading = True
            download.paused = False
            self.logger.info(f"Started download: {download.name}")
        
        return success
    
    async def pause_download(self, torrent_id: str) -> bool:
        """Pause a specific download"""
        download = self.get_download(torrent_id)
        if not download:
            return False
        
        # Create worker and pause
        worker = DownloadWorker(download)
        success = await worker.pause()
        
        if success:
            download.paused = True
            self.logger.info(f"Paused download: {download.name}")
        
        return success
    
    async def resume_download(self, torrent_id: str) -> bool:
        """Resume a specific download"""
        download = self.get_download(torrent_id)
        if not download:
            return False
        
        # Create worker and resume
        worker = DownloadWorker(download)
        success = await worker.resume()
        
        if success:
            download.paused = False
            self.logger.info(f"Resumed download: {download.name}")
        
        return success
    
    async def stop_download(self, torrent_id: str) -> bool:
        """Stop a specific download"""
        download = self.get_download(torrent_id)
        if not download:
            return False
        
        # Create worker and stop
        worker = DownloadWorker(download)
        success = await worker.stop()
        
        if success:
            download.downloading = False
            download.paused = False
            self.logger.info(f"Stopped download: {download.name}")
        
        return success
    
    def remove_download(self, torrent_id: str) -> bool:
        """Remove a download completely"""
        return self.download_service.remove_download(torrent_id)
    
    def update_download_settings(self, torrent_id: str, settings: DownloadSettings) -> bool:
        """Update download settings"""
        return self.download_service.update_download_settings(torrent_id, settings)
    
    def get_file_selection(self, torrent_id: str) -> Optional[Dict]:
        """Get file selection for a specific download"""
        return self.download_service.get_file_selection(torrent_id)
    
    def update_file_selection(self, torrent_id: str, file_selections: Dict[str, bool]) -> bool:
        """Update file selection for a specific download"""
        return self.download_service.update_file_selection(torrent_id, file_selections)
    
    def set_download_directory(self, directory: str) -> bool:
        """Set custom download directory"""
        return self.download_service.set_download_directory(directory)
    
    def get_download_directory(self) -> str:
        """Get current download directory"""
        return self.download_service.get_download_directory()
    
    def get_health_status(self) -> Dict:
        """Get application health status"""
        import psutil
        import time
        
        active_downloads = sum(1 for d in self.download_service.get_all_downloads().values() if d.downloading)
        
        return {
            'status': 'healthy',
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'version': '2.0.0',
            'uptime': int(time.time() - self.settings.start_time if hasattr(self.settings, 'start_time') else 0),
            'active_downloads': active_downloads,
            'memory_usage': psutil.virtual_memory().percent,
            'cpu_usage': psutil.cpu_percent()
        }
    
    def get_metrics(self) -> Dict:
        """Get application metrics"""
        downloads = self.download_service.get_all_downloads()
        
        total_downloads = len(downloads)
        active_downloads = sum(1 for d in downloads.values() if d.downloading)
        completed_downloads = sum(1 for d in downloads.values() if d.completed)
        failed_downloads = 0  # Not implemented yet
        
        total_downloaded = sum(d.downloaded_size for d in downloads.values())
        average_speed = sum(d.download_speed for d in downloads.values()) / max(len(downloads), 1)
        
        import psutil
        
        return {
            'downloads': {
                'total': total_downloads,
                'active': active_downloads,
                'completed': completed_downloads,
                'failed': failed_downloads
            },
            'performance': {
                'average_speed': average_speed,
                'total_downloaded': total_downloaded,
                'uptime': int(time.time() - self.settings.start_time if hasattr(self.settings, 'start_time') else 0)
            },
            'system': {
                'memory_usage': psutil.virtual_memory().percent,
                'cpu_usage': psutil.cpu_percent(),
                'disk_usage': psutil.disk_usage('/').percent
            }
        } 