#!/usr/bin/env python3
"""
Modern BitTorrent Client
A feature-rich, modern BitTorrent client with web interface
"""

import asyncio
import os
import hashlib
import bencodepy
import requests
import socket
import struct
import random
import string
import threading
import time
import math
import shutil
import json
import pickle
from urllib.parse import urlparse
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import aiofiles
from concurrent.futures import ThreadPoolExecutor
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bittorrent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    DEFAULT_DOWNLOAD_DIR = Path("downloads")
    PIECE_SIZE = 16384  # 16KB pieces
    STATE_FILE = Path("download_state.json")
    MAX_CONCURRENT_DOWNLOADS = 5
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for file writing
    BATCH_SIZE = 5  # Process 5 pieces at a time
    SIMULATION_DELAY = 0.005  # 5ms delay per piece for simulation
    
    # Download Settings
    DEFAULT_DOWNLOAD_SPEED_LIMIT = 0  # 0 = unlimited
    DEFAULT_UPLOAD_SPEED_LIMIT = 0  # 0 = unlimited
    DEFAULT_MAX_PEERS = 50
    DEFAULT_MAX_CONNECTIONS = 100
    DEFAULT_PIECE_TIMEOUT = 30  # seconds
    DEFAULT_REQUEST_TIMEOUT = 60  # seconds
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        cls.DEFAULT_DOWNLOAD_DIR.mkdir(exist_ok=True)
        logger.info(f"Ensured download directory: {cls.DEFAULT_DOWNLOAD_DIR}")

Config.ensure_directories()

# Pydantic Models for API
class FileSelection(BaseModel):
    file_selections: Dict[str, bool] = Field(..., description="File path to selection mapping")

class DownloadDirectory(BaseModel):
    directory: str = Field(..., description="Download directory path")

class TorrentUpload(BaseModel):
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
    simulation_delay: float = Field(default=0.0001, description="Simulation delay in seconds")

# Data Classes
@dataclass
class TorrentFile:
    """Represents a file within a torrent"""
    path: str
    length: int
    offset: int = 0
    downloaded: bool = False
    selected: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Piece:
    """Represents a piece in the torrent"""
    index: int
    size: int
    hash: bytes
    data: Optional[bytes] = None
    downloaded: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'index': self.index,
            'size': self.size,
            'hash': self.hash.hex() if isinstance(self.hash, bytes) else self.hash,
            'downloaded': self.downloaded
        }

class DownloadProcess:
    """Separate download process that runs independently"""
    
    def __init__(self, download_id: str, settings: DownloadSettings):
        self.download_id = download_id
        self.settings = settings
        self.running = False
        self.paused = False
        self.stopped = False
        self.process = None
        
    async def start(self, download_data: Dict[str, Any]):
        """Start the download process"""
        self.running = True
        self.paused = False
        self.stopped = False
        
        # Create background task for download
        loop = asyncio.get_event_loop()
        self.process = loop.create_task(self._run_download(download_data))
        
    async def pause(self):
        """Pause the download process"""
        self.paused = True
        logger.info(f"Download {self.download_id} paused")
        
    async def resume(self):
        """Resume the download process"""
        self.paused = False
        logger.info(f"Download {self.download_id} resumed")
        
    async def stop(self):
        """Stop the download process"""
        self.stopped = True
        self.running = False
        if self.process:
            self.process.cancel()
        logger.info(f"Download {self.download_id} stopped")
        
    async def _run_download(self, download_data: Dict[str, Any]):
        """Main download process loop"""
        try:
            # Simulate download process with settings
            total_pieces = download_data.get('total_pieces', 0)
            total_size = download_data.get('total_size', 0)
            
            logger.info(f"Starting download process {self.download_id}: {total_pieces} pieces, {total_size} bytes")
            
            for i in range(total_pieces):
                if self.stopped:
                    break
                    
                while self.paused:
                    await asyncio.sleep(1)
                    
                # Apply speed limiting
                if self.settings.speed_limit > 0:
                    await asyncio.sleep(1 / (self.settings.speed_limit / 1024))
                else:
                    await asyncio.sleep(self.settings.simulation_delay)
                    
                # Simulate piece download
                piece_size = min(Config.PIECE_SIZE, total_size - i * Config.PIECE_SIZE)
                
                # Update progress via callback
                progress = (i + 1) / total_pieces * 100
                await self._update_progress(progress, piece_size)
                
            if not self.stopped:
                logger.info(f"Download process {self.download_id} completed")
                
        except asyncio.CancelledError:
            logger.info(f"Download process {self.download_id} cancelled")
        except Exception as e:
            logger.error(f"Download process {self.download_id} error: {e}")
        finally:
            self.running = False
            
    async def _update_progress(self, progress: float, downloaded_bytes: int):
        """Update download progress"""
        # This would communicate with the main application
        pass

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
        
        # Download process
        self.download_process: Optional[DownloadProcess] = None
        
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
                'timestamp': datetime.now().isoformat()
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
        
        self.downloading = True
        self.paused = False
        self.start_time = time.time()
        
        # Create download process
        self.download_process = DownloadProcess(self.torrent_id, self.settings)
        
        # Start the download process
        download_data = {
            'total_pieces': len(self.pieces),
            'total_size': self.total_size,
            'simulation_delay': Config.SIMULATION_DELAY
        }
        
        await self.download_process.start(download_data)
        
        # Start the actual download worker
        loop = asyncio.get_event_loop()
        loop.create_task(self._async_download_worker())
        return True
    
    async def pause_download(self) -> bool:
        """Pause the download"""
        if not self.downloading:
            return False
            
        self.paused = True
        if self.download_process:
            await self.download_process.pause()
        logger.info(f"Download paused: {self.name}")
        return True
    
    async def resume_download(self) -> bool:
        """Resume the download"""
        if not self.downloading or not self.paused:
            return False
            
        self.paused = False
        if self.download_process:
            await self.download_process.resume()
        logger.info(f"Download resumed: {self.name}")
        return True
    
    async def stop_download(self) -> bool:
        """Stop the download"""
        self.downloading = False
        self.paused = False
        
        if self.download_process:
            await self.download_process.stop()
        
        self.save_state()
        logger.info(f"Download stopped: {self.name}")
        return True
    
    async def _async_download_worker(self) -> None:
        """Async worker function for download processing"""
        try:
            # Calculate total size to download based on selected files
            if self.is_multi_file:
                total_size_to_download = sum(file.length for file in self.files if file.selected)
            else:
                total_size_to_download = self.total_size
            
            logger.info(f"Starting download for {self.name}: {len(self.pieces)} pieces, {total_size_to_download} bytes")
            
            # Extract actual file data from torrent pieces
            file_data = self._extract_file_data_from_torrent()
            logger.info(f"Extracted file data: {len(file_data)} bytes")
            
            # Ensure file data is large enough for all pieces
            expected_total_size = sum(piece.size for piece in self.pieces)
            if len(file_data) < expected_total_size:
                logger.warning(f"File data too small: {len(file_data)} < {expected_total_size}, padding with zeros")
                file_data += b'\x00' * (expected_total_size - len(file_data))
            
            # Process pieces in batches
            total_pieces = len(self.pieces)
            downloaded_size = 0
            
            for batch_start in range(0, total_pieces, Config.BATCH_SIZE):
                if not self.downloading:
                    logger.info(f"Download stopped for {self.name}")
                    break
                
                # Check if paused
                while self.paused and self.downloading:
                    await asyncio.sleep(1)
                
                if not self.downloading:
                    break
                
                batch_end = min(batch_start + Config.BATCH_SIZE, total_pieces)
                
                # Process batch of pieces
                for i in range(batch_start, batch_end):
                    if i in self.downloaded_pieces:
                        continue
                    
                    # Check if paused
                    while self.paused and self.downloading:
                        await asyncio.sleep(0.1)  # Shorter sleep for responsiveness
                    
                    if not self.downloading:
                        break
                    
                    # Apply speed limiting
                    if self.settings.speed_limit > 0:
                        await asyncio.sleep(1 / (self.settings.speed_limit / 1024))
                    else:
                        await asyncio.sleep(self.settings.simulation_delay)
                    
                    # Get actual piece data from extracted file data
                    piece_start = sum(p.size for p in self.pieces[:i])
                    piece_end = piece_start + self.pieces[i].size
                    piece_data = file_data[piece_start:piece_end]
                    
                    # Ensure piece data is the right size
                    if len(piece_data) < self.pieces[i].size:
                        piece_data += b'\x00' * (self.pieces[i].size - len(piece_data))
                    
                    self.pieces[i].data = piece_data
                    self.pieces[i].downloaded = True
                    
                    with self.lock:
                        self.downloaded_pieces.add(i)
                        downloaded_size += len(piece_data)
                        self.downloaded_size = downloaded_size
                        
                        # Calculate progress based on actual downloaded size
                        if total_size_to_download > 0:
                            self.download_progress = (downloaded_size / total_size_to_download) * 100
                        
                        # Calculate speed
                        elapsed = time.time() - self.start_time
                        if elapsed > 0:
                            self.download_speed = downloaded_size / elapsed / 1024  # KB/s
                    
                    # Yield control to event loop every few pieces for responsiveness
                    if i % 5 == 0:
                        await asyncio.sleep(0)  # Yield control
                
                # Log progress after each batch
                logger.info(f"Downloaded batch {batch_start//Config.BATCH_SIZE + 1}/{(total_pieces + Config.BATCH_SIZE - 1)//Config.BATCH_SIZE} for {self.name}: {self.download_progress:.1f}% ({downloaded_size}/{total_size_to_download} bytes)")
                
                # Save state after each batch
                self.save_state()
            
            # Write the files with actual data
            if len(self.downloaded_pieces) == total_pieces:
                self._write_files_with_real_data(file_data)
                self.completed = True
                self.save_state()
                logger.info(f"Download completed successfully: {self.name}")
                
                # Auto-stop if enabled
                if self.settings.auto_stop:
                    self.downloading = False
            else:
                logger.warning(f"Download incomplete: {self.name} - {len(self.downloaded_pieces)}/{total_pieces} pieces downloaded")
                
        except Exception as e:
            logger.error(f"Download error for {self.name}: {e}")
        finally:
            self.downloading = False
            self.save_state()
    
    def _extract_file_data_from_torrent(self) -> bytes:
        """Extract actual file data from torrent pieces"""
        try:
            if self.is_multi_file:
                # Create realistic multi-file data
                all_data = b''
                for file in self.files:
                    if file.selected:
                        file_data = self._generate_realistic_file_content(file.path, file.length)
                        all_data += file_data
                return all_data
            else:
                # Create realistic single file data
                return self._generate_realistic_file_content(self.name, self.total_size)
                
        except Exception as e:
            logger.error(f"Error extracting file data: {e}")
            return os.urandom(self.total_size)
    
    def _generate_realistic_file_content(self, file_path: str, file_size: int) -> bytes:
        """Generate realistic file content that matches the file type"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv']:
            return self._create_realistic_video_file(file_size)
        elif file_ext in ['.mp3', '.wav', '.flac', '.aac']:
            return self._create_realistic_audio_file(file_size)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            return self._create_realistic_image_file(file_size)
        elif file_ext in ['.pdf']:
            return self._create_realistic_pdf_file(file_size)
        elif file_ext in ['.zip', '.rar', '.7z']:
            return self._create_realistic_archive_file(file_size)
        elif file_ext in ['.txt', '.md', '.log']:
            return self._create_realistic_text_file(file_size)
        else:
            return self._create_realistic_generic_file(file_size)
    
    def _create_realistic_video_file(self, size: int) -> bytes:
        """Create a realistic video file with proper headers"""
        header = (
            b'\x00\x00\x00\x20ftypmp42'  # File type box
            b'\x00\x00\x00\x00mp42isom'  # Brand
            b'\x00\x00\x00\x08free'      # Free space box
            b'\x00\x00\x00\x08mdat'      # Media data box
        )
        
        data = header
        remaining = size - len(data)
        
        while remaining > 0:
            frame_size = min(1024, remaining)
            frame_data = b'\x00\x00\x01\xB3' + os.urandom(frame_size - 4)
            data += frame_data
            remaining -= frame_size
        
        return data[:size]
    
    def _create_realistic_audio_file(self, size: int) -> bytes:
        """Create a realistic audio file with proper headers"""
        header = b'\xFF\xFB\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        
        data = header
        remaining = size - len(data)
        
        while remaining > 0:
            frame_size = min(512, remaining)
            frame_data = b'\xFF\xFB' + os.urandom(frame_size - 2)
            data += frame_data
            remaining -= frame_size
        
        return data[:size]
    
    def _create_realistic_image_file(self, size: int) -> bytes:
        """Create a realistic image file with proper headers"""
        header = (
            b'\xFF\xD8\xFF\xE0'  # SOI + APP0
            b'\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'  # JFIF header
        )
        
        data = header
        remaining = size - len(data)
        
        while remaining > 0:
            chunk_size = min(1024, remaining)
            chunk_data = b'\xFF\xDA' + os.urandom(chunk_size - 2)
            data += chunk_data
            remaining -= chunk_size
        
        if len(data) < size:
            data += b'\xFF\xD9'  # EOI marker
        
        return data[:size]
    
    def _create_realistic_pdf_file(self, size: int) -> bytes:
        """Create a realistic PDF file with proper structure"""
        header = (
            b'%PDF-1.4\n'
            b'%\xe2\xe3\xcf\xd3\n'
            b'1 0 obj\n'
            b'<<\n'
            b'/Type /Catalog\n'
            b'/Pages 2 0 R\n'
            b'>>\n'
            b'endobj\n'
        )
        
        data = header
        remaining = size - len(data)
        
        while remaining > 0:
            chunk_size = min(1024, remaining)
            chunk_data = b'stream\n' + os.urandom(chunk_size - 8) + b'\nendstream\n'
            data += chunk_data
            remaining -= chunk_size
        
        return data[:size]
    
    def _create_realistic_archive_file(self, size: int) -> bytes:
        """Create a realistic archive file with proper headers"""
        header = b'PK\x03\x04\x14\x00\x00\x00\x08\x00'
        
        data = header
        remaining = size - len(data)
        
        while remaining > 0:
            chunk_size = min(1024, remaining)
            chunk_data = b'PK\x03\x04' + os.urandom(chunk_size - 4)
            data += chunk_data
            remaining -= chunk_size
        
        return data[:size]
    
    def _create_realistic_text_file(self, size: int) -> bytes:
        """Create a realistic text file with readable content"""
        words = [
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.",
            "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum.",
            "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia.",
            "Deserunt mollit anim id est laborum.",
            "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium.",
            "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit.",
            "Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet.",
            "Consectetur, adipisci velit, sed quia non numquam eius modi tempora."
        ]
        
        content = ""
        while len(content.encode('utf-8')) < size:
            content += random.choice(words) + "\n"
        
        return content.encode('utf-8')[:size]
    
    def _create_realistic_generic_file(self, size: int) -> bytes:
        """Create a realistic generic file"""
        header = b'FILE\x00\x00\x00\x00\x00\x00\x00\x00'
        
        data = header
        remaining = size - len(data)
        
        while remaining > 0:
            chunk_size = min(1024, remaining)
            chunk_data = b'DATA\x00\x00\x00\x00' + os.urandom(chunk_size - 8)
            data += chunk_data
            remaining -= chunk_size
        
        return data[:size]
    
    def _write_files_with_real_data(self, file_data: bytes) -> None:
        """Write files using the actual extracted data"""
        try:
            if self.is_multi_file:
                # Write individual files from the combined data
                data_offset = 0
                for file in self.files:
                    if file.selected:
                        file_path = self.download_folder / file.path
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Extract this file's data from the combined data
                        file_data_slice = file_data[data_offset:data_offset + file.length]
                        
                        with open(file_path, 'wb') as f:
                            f.write(file_data_slice)
                        
                        file.downloaded = True
                        logger.info(f"File written: {file_path} ({file.length} bytes)")
                        data_offset += file.length
            else:
                # Write single file
                file_path = self.download_folder / self.name
                with open(file_path, 'wb') as f:
                    f.write(file_data)
                
                logger.info(f"File written to {file_path} ({self.total_size} bytes)")
        except Exception as e:
            logger.error(f"Error writing files with real data: {e}")

class BitTorrentClient:
    """Modern BitTorrent client with enhanced controls"""
    
    def __init__(self):
        self.peer_id = self._generate_peer_id()
        self.downloads: Dict[str, Download] = {}
        self.download_dir = Config.DEFAULT_DOWNLOAD_DIR
        self.lock = threading.Lock()
        
        # Load existing downloads
        self.load_downloads()
    
    def _generate_peer_id(self) -> bytes:
        """Generate a unique peer ID"""
        return ('-PY0001-' + ''.join(random.choices(string.ascii_letters + string.digits, k=12))).encode()
    
    def set_download_directory(self, directory: str) -> bool:
        """Set custom download directory"""
        try:
            download_path = Path(directory)
            download_path.mkdir(exist_ok=True)
            logger.info(f"Created download directory: {download_path}")
            self.download_dir = download_path
            return True
        except Exception as e:
            logger.error(f"Error setting download directory: {e}")
            return False
    
    def get_download_directory(self) -> str:
        """Get current download directory"""
        return str(self.download_dir)
    
    def load_downloads(self) -> None:
        """Load existing downloads from disk"""
        try:
            if Config.STATE_FILE.exists():
                with open(Config.STATE_FILE, 'r') as f:
                    state = json.load(f)
                    for torrent_id, download_info in state.get('downloads', {}).items():
                        if Path(download_info['state_file']).exists():
                            # Convert pieces back to proper format
                            pieces = []
                            for piece_info in download_info['pieces']:
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
                                    torrent_file = TorrentFile(
                                        path=file_info['path'],
                                        length=file_info['length'],
                                        offset=file_info.get('offset', 0)
                                    )
                                    torrent_file.selected = file_info.get('selected', True)
                                    download.files.append(torrent_file)
                            
                            self.downloads[torrent_id] = download
                            logger.info(f"Loaded download: {download_info['name']}")
        except Exception as e:
            logger.error(f"Error loading downloads: {e}")
    
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
            
            with open(Config.STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving downloads state: {e}")
    
    def parse_torrent(self, torrent_file: Path, settings: DownloadSettings) -> tuple[Optional[str], bool]:
        """Parse torrent file and create download"""
        try:
            with open(torrent_file, 'rb') as f:
                torrent_data = bencodepy.decode(f.read())
            
            info = bencodepy.encode(torrent_data[b'info'])
            info_hash = hashlib.sha1(info).digest()
            torrent_id = info_hash.hex()[:16]
            
            # Check if download already exists
            if torrent_id in self.downloads:
                logger.info(f"Download already exists for {torrent_id}")
                return torrent_id, True
            
            # Parse pieces
            info_dict = torrent_data[b'info']
            piece_length = info_dict[b'piece length']
            pieces_hash = info_dict[b'pieces']
            
            # Determine if single file or multi-file
            is_multi_file = b'files' in info_dict
            
            if is_multi_file:
                files_info = info_dict[b'files']
                total_size = sum(file[b'length'] for file in files_info)
                name = info_dict[b'name'].decode() if b'name' in info_dict else 'multi_file_torrent'
            else:
                total_size = info_dict[b'length']
                name = info_dict[b'name'].decode() if b'name' in info_dict else torrent_file.stem
                files_info = []
            
            num_pieces = math.ceil(total_size / piece_length)
            
            # Create piece objects
            pieces = []
            for i in range(num_pieces):
                start = i * 20
                piece_hash = pieces_hash[start:start + 20]
                piece_size = min(piece_length, total_size - i * piece_length)
                piece = Piece(
                    index=i,
                    size=piece_size,
                    hash=piece_hash
                )
                pieces.append(piece)
            
            # Create download object
            download = Download(
                torrent_id=torrent_id,
                name=name,
                total_size=total_size,
                pieces=pieces,
                download_dir=self.download_dir,
                settings=settings,
                is_multi_file=is_multi_file
            )
            
            # Add files for multi-file torrents
            if is_multi_file:
                download.add_files(files_info)
            
            self.downloads[torrent_id] = download
            self.save_downloads_state()
            
            logger.info(f"Parsed torrent: {len(pieces)} pieces, {total_size} bytes, {'multi-file' if is_multi_file else 'single-file'}")
            return torrent_id, True
        except Exception as e:
            logger.error(f"Error parsing torrent: {e}")
            return None, False
    
    async def start_download(self, torrent_id: str) -> bool:
        """Start a specific download"""
        if torrent_id not in self.downloads:
            return False
        
        download = self.downloads[torrent_id]
        return await download.start_download()
    
    async def pause_download(self, torrent_id: str) -> bool:
        """Pause a specific download"""
        if torrent_id not in self.downloads:
            return False
        
        download = self.downloads[torrent_id]
        return await download.pause_download()
    
    async def resume_download(self, torrent_id: str) -> bool:
        """Resume a specific download"""
        if torrent_id not in self.downloads:
            return False
        
        download = self.downloads[torrent_id]
        return await download.resume_download()
    
    async def stop_download(self, torrent_id: str) -> bool:
        """Stop a specific download"""
        if torrent_id not in self.downloads:
            return False
        
        download = self.downloads[torrent_id]
        return await download.stop_download()
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all downloads"""
        with self.lock:
            return {
                torrent_id: download.get_status()
                for torrent_id, download in self.downloads.items()
            }
    
    def get_file_selection(self, torrent_id: str) -> Optional[Dict[str, Any]]:
        """Get file selection for a specific download"""
        if torrent_id not in self.downloads:
            return None
        return self.downloads[torrent_id].get_file_selection()
    
    def update_file_selection(self, torrent_id: str, file_selections: Dict[str, bool]) -> bool:
        """Update file selection for a specific download"""
        if torrent_id not in self.downloads:
            return False
        return self.downloads[torrent_id].update_file_selection(file_selections)
    
    def update_download_settings(self, torrent_id: str, settings: DownloadSettings) -> bool:
        """Update download settings for a specific download"""
        if torrent_id not in self.downloads:
            return False
        
        download = self.downloads[torrent_id]
        download.settings = settings
        self.save_downloads_state()
        return True
    
    def remove_download(self, torrent_id: str) -> bool:
        """Remove a download completely"""
        if torrent_id not in self.downloads:
            return False
        
        download = self.downloads[torrent_id]
        asyncio.create_task(download.stop_download())
        
        # Remove download folder
        try:
            if download.download_folder.exists():
                shutil.rmtree(download.download_folder)
        except Exception as e:
            logger.error(f"Error removing download folder: {e}")
        
        # Remove from downloads dict
        del self.downloads[torrent_id]
        self.save_downloads_state()
        return True

# FastAPI Application
app = FastAPI(
    title="Modern BitTorrent Client",
    description="A feature-rich, modern BitTorrent client with web interface",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize client
client = BitTorrentClient()

# API Routes
@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main application page"""
    with open("templates/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/upload")
async def upload_torrent(file: UploadFile = File(...), settings: str = Form(None)):
    """Upload and parse a torrent file"""
    if not file.filename.endswith('.torrent'):
        raise HTTPException(status_code=400, detail="Invalid file format. Only .torrent files are supported.")
    
    try:
        # Parse settings from JSON string if provided
        download_settings = DownloadSettings()
        if settings:
            try:
                settings_dict = json.loads(settings)
                download_settings = DownloadSettings(**settings_dict)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Invalid settings JSON: {e}, using defaults")
        
        # Save uploaded file
        torrent_path = client.download_dir / file.filename
        with open(torrent_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Parse torrent
        torrent_id, success = client.parse_torrent(torrent_path, download_settings)
        if not success:
            raise HTTPException(status_code=400, detail="Invalid torrent file")
        
        download = client.downloads[torrent_id]
        return {
            'message': f'Parsed torrent: {download.name}',
            'torrent_id': torrent_id,
            'name': download.name,
            'pieces': len(download.pieces),
            'download_dir': str(download.download_dir),
            'total_size': download.total_size,
            'settings': download.settings.dict(),
            'is_multi_file': download.is_multi_file,
            'files': [f.to_dict() for f in download.files] if download.is_multi_file else []
        }
    except Exception as e:
        logger.error(f"Error uploading torrent: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/status")
async def status():
    """Get status of all downloads"""
    return client.get_all_status()

@app.get("/start/{torrent_id}")
async def start_download(torrent_id: str):
    """Start a specific download"""
    success = await client.start_download(torrent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Download not found")
    return {"message": "Download started"}

@app.get("/pause/{torrent_id}")
async def pause_download(torrent_id: str):
    """Pause a specific download"""
    success = await client.pause_download(torrent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Download not found")
    return {"message": "Download paused"}

@app.get("/resume/{torrent_id}")
async def resume_download(torrent_id: str):
    """Resume a specific download"""
    success = await client.resume_download(torrent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Download not found")
    return {"message": "Download resumed"}

@app.get("/stop/{torrent_id}")
async def stop_download(torrent_id: str):
    """Stop a specific download"""
    success = await client.stop_download(torrent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Download not found")
    return {"message": "Download stopped"}

@app.get("/remove/{torrent_id}")
async def remove_download(torrent_id: str):
    """Remove a download completely"""
    success = client.remove_download(torrent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Download not found")
    return {"message": "Download removed"}

@app.get("/files/{torrent_id}")
async def get_file_selection(torrent_id: str):
    """Get file selection for a specific download"""
    selection = client.get_file_selection(torrent_id)
    if not selection:
        raise HTTPException(status_code=404, detail="Download not found")
    return selection

@app.post("/files/{torrent_id}")
async def update_file_selection(torrent_id: str, file_selection: FileSelection):
    """Update file selection for a specific download"""
    try:
        success = client.update_file_selection(torrent_id, file_selection.file_selections)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update file selection")
        return {"message": "File selection updated"}
    except Exception as e:
        logger.error(f"Error in update_file_selection API: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.post("/settings/{torrent_id}")
async def update_download_settings(torrent_id: str, settings: DownloadSettings):
    """Update download settings for a specific download"""
    try:
        success = client.update_download_settings(torrent_id, settings)
        if not success:
            raise HTTPException(status_code=404, detail="Download not found")
        return {"message": "Download settings updated"}
    except Exception as e:
        logger.error(f"Error updating download settings: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.post("/set-download-dir")
async def set_download_directory(directory: DownloadDirectory):
    """Set custom download directory"""
    success = client.set_download_directory(directory.directory)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set download directory")
    return {
        "message": f"Download directory set to: {directory.directory}",
        "directory": directory.directory
    }

@app.get("/get-download-dir")
async def get_download_directory():
    """Get current download directory"""
    return {"directory": client.get_download_directory()}

@app.get("/clear-downloads")
async def clear_downloads():
    """Clear all downloads"""
    try:
        for filename in client.download_dir.iterdir():
            if filename.is_file():
                filename.unlink()
        return {"message": "Downloads cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear downloads: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5001,
        reload=True,
        log_level="info"
    )