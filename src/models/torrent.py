"""
Torrent-related data models
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class TorrentFile:
    """Represents a file within a torrent"""
    path: str
    length: int
    offset: int = 0
    downloaded: bool = False
    selected: bool = True
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'path': self.path,
            'length': self.length,
            'offset': self.offset,
            'downloaded': self.downloaded,
            'selected': self.selected
        }


@dataclass
class Piece:
    """Represents a piece in the torrent"""
    index: int
    size: int
    hash: bytes
    data: Optional[bytes] = None
    downloaded: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'index': self.index,
            'size': self.size,
            'hash': self.hash.hex() if isinstance(self.hash, bytes) else self.hash,
            'downloaded': self.downloaded
        }


@dataclass
class TorrentInfo:
    """Torrent information"""
    name: str
    total_size: int
    piece_length: int
    pieces: List[Piece]
    files: List[TorrentFile]
    is_multi_file: bool
    info_hash: bytes
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'total_size': self.total_size,
            'piece_length': self.piece_length,
            'pieces': [piece.to_dict() for piece in self.pieces],
            'files': [file.to_dict() for file in self.files],
            'is_multi_file': self.is_multi_file,
            'info_hash': self.info_hash.hex()
        } 