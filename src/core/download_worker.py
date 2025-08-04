"""
Download worker for handling download operations
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..models.download import Download
from ..models.torrent import TorrentFile
from ..services.file_service import FileService
from ..config.settings import Config

logger = logging.getLogger(__name__)


class DownloadWorker:
    """Worker for handling download operations"""
    
    def __init__(self, download: Download):
        self.download = download
        self.file_service = FileService()
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.paused = False
        self.stopped = False
        
    async def start(self) -> bool:
        """Start the download worker"""
        if self.download.completed:
            self.logger.info(f"Download {self.download.name} already completed")
            return True
        
        self.running = True
        self.paused = False
        self.stopped = False
        self.download.start_time = time.time()
        
        # Start the download process
        asyncio.create_task(self._download_worker())
        
        self.logger.info(f"Started download worker for {self.download.name}")
        return True
    
    async def pause(self) -> bool:
        """Pause the download worker"""
        self.paused = True
        self.logger.info(f"Paused download worker for {self.download.name}")
        return True
    
    async def resume(self) -> bool:
        """Resume the download worker"""
        self.paused = False
        self.logger.info(f"Resumed download worker for {self.download.name}")
        return True
    
    async def stop(self) -> bool:
        """Stop the download worker"""
        self.stopped = True
        self.running = False
        self.paused = False
        self.logger.info(f"Stopped download worker for {self.download.name}")
        return True
    
    async def _download_worker(self) -> None:
        """Main download worker loop"""
        try:
            total_pieces = len(self.download.pieces)
            downloaded_count = 0
            
            # Process pieces in batches
            batch_size = Config.BATCH_SIZE
            for i in range(0, total_pieces, batch_size):
                if self.stopped:
                    break
                
                batch_end = min(i + batch_size, total_pieces)
                batch_pieces = self.download.pieces[i:batch_end]
                
                # Process batch
                for piece in batch_pieces:
                    if self.stopped:
                        break
                    
                    # Wait if paused
                    while self.paused and not self.stopped:
                        await asyncio.sleep(0.1)
                    
                    if self.stopped:
                        break
                    
                    # Simulate piece download
                    await self._download_piece(piece)
                    
                    # Update progress
                    downloaded_count += 1
                    self.download.downloaded_pieces.add(piece.index)
                    self.download.download_progress = (downloaded_count / total_pieces) * 100
                    
                    # Apply speed limiting
                    if self.download.settings.speed_limit > 0:
                        delay = 1.0 / (self.download.settings.speed_limit / 1024)
                        await asyncio.sleep(delay)
                    else:
                        await asyncio.sleep(Config.SIMULATION_DELAY)
                
                # Save state periodically
                if downloaded_count % (batch_size * 5) == 0:
                    self.download.save_state()
            
            # Complete download
            if not self.stopped:
                await self._complete_download()
            
        except Exception as e:
            self.logger.error(f"Error in download worker: {e}")
        finally:
            self.running = False
    
    async def _download_piece(self, piece) -> None:
        """Download a single piece"""
        try:
            # Simulate piece download
            await asyncio.sleep(0.01)  # Simulate network delay
            
            # Update piece status
            piece.downloaded = True
            
            # Update download statistics
            self.download.downloaded_size += piece.size
            
            # Calculate speed
            if self.download.start_time:
                elapsed = time.time() - self.download.start_time
                if elapsed > 0:
                    self.download.download_speed = self.download.downloaded_size / elapsed
            
            self.logger.debug(f"Downloaded piece {piece.index} for {self.download.name}")
            
        except Exception as e:
            self.logger.error(f"Error downloading piece {piece.index}: {e}")
    
    async def _complete_download(self) -> None:
        """Complete the download process"""
        try:
            self.download.completed = True
            self.download.downloading = False
            self.download.download_progress = 100.0
            
            # Write files to disk
            if self.download.is_multi_file and self.download.files:
                files_info = []
                for file in self.download.files:
                    if file.selected:
                        files_info.append({
                            'path': file.path,
                            'length': file.length
                        })
                
                if files_info:
                    success = self.file_service.write_files(
                        self.download.download_folder,
                        files_info,
                        self.download.total_size
                    )
                    
                    if success:
                        self.logger.info(f"Successfully wrote files for {self.download.name}")
                    else:
                        self.logger.error(f"Failed to write files for {self.download.name}")
            else:
                # Single file download
                file_path = self.download.download_folder / self.download.name
                content = self.file_service._generate_realistic_file_content(
                    self.download.name,
                    self.download.total_size
                )
                
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                self.logger.info(f"Successfully wrote file: {file_path}")
            
            # Save final state
            self.download.save_state()
            
            # Auto-stop if enabled
            if self.download.settings.auto_stop:
                await self.stop()
            
            self.logger.info(f"Completed download: {self.download.name}")
            
        except Exception as e:
            self.logger.error(f"Error completing download: {e}")
    
    def get_progress(self) -> Dict[str, any]:
        """Get current progress information"""
        return {
            'downloaded_pieces': len(self.download.downloaded_pieces),
            'total_pieces': len(self.download.pieces),
            'progress': self.download.download_progress,
            'downloaded_size': self.download.downloaded_size,
            'total_size': self.download.total_size,
            'speed': self.download.download_speed,
            'completed': self.download.completed,
            'running': self.running,
            'paused': self.paused,
            'stopped': self.stopped
        } 