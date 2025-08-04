"""
Torrent service for parsing and managing torrent files
"""

import hashlib
import math
import logging
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any

import bencodepy

from ..models.torrent import TorrentFile, Piece, TorrentInfo
from ..models.api import DownloadSettings
from ..config.settings import Config

logger = logging.getLogger(__name__)


class TorrentService:
    """Service for handling torrent file operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_torrent(self, torrent_file: Path) -> Optional[TorrentInfo]:
        """Parse torrent file and extract information"""
        try:
            with open(torrent_file, 'rb') as f:
                torrent_data = bencodepy.decode(f.read())
            
            info = bencodepy.encode(torrent_data[b'info'])
            info_hash = hashlib.sha1(info).digest()
            
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
            
            # Create file objects for multi-file torrents
            files = []
            if is_multi_file:
                offset = 0
                for file_info in files_info:
                    path_parts = file_info[b'path']
                    if isinstance(path_parts[0], bytes):
                        path_parts = [part.decode('utf-8') for part in path_parts]
                    
                    file_path = '/'.join(path_parts)
                    torrent_file_obj = TorrentFile(
                        path=file_path,
                        length=file_info[b'length'],
                        offset=offset
                    )
                    files.append(torrent_file_obj)
                    offset += file_info[b'length']
            
            torrent_info = TorrentInfo(
                name=name,
                total_size=total_size,
                piece_length=piece_length,
                pieces=pieces,
                files=files,
                is_multi_file=is_multi_file,
                info_hash=info_hash
            )
            
            self.logger.info(f"Parsed torrent: {len(pieces)} pieces, {total_size} bytes, {'multi-file' if is_multi_file else 'single-file'}")
            return torrent_info
            
        except Exception as e:
            self.logger.error(f"Error parsing torrent: {e}")
            return None
    
    def get_torrent_id(self, torrent_info: TorrentInfo) -> str:
        """Generate torrent ID from info hash"""
        return torrent_info.info_hash.hex()[:16]
    
    def validate_torrent_file(self, torrent_file: Path) -> bool:
        """Validate torrent file integrity"""
        try:
            with open(torrent_file, 'rb') as f:
                data = bencodepy.decode(f.read())
            
            # Check required fields
            if b'info' not in data:
                return False
            
            info = data[b'info']
            if b'piece length' not in info or b'pieces' not in info:
                return False
            
            # Check for name field
            if b'name' not in info:
                return False
            
            # Check for either length (single file) or files (multi file)
            if b'length' not in info and b'files' not in info:
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_torrent_size(self, torrent_info: TorrentInfo) -> int:
        """Get total size of torrent"""
        return torrent_info.total_size
    
    def get_torrent_files(self, torrent_info: TorrentInfo) -> List[TorrentFile]:
        """Get list of files in torrent"""
        return torrent_info.files
    
    def is_multi_file_torrent(self, torrent_info: TorrentInfo) -> bool:
        """Check if torrent contains multiple files"""
        return torrent_info.is_multi_file 