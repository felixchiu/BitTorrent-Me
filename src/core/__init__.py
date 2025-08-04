"""
Core functionality for Modern BitTorrent Client
"""

from .bit_torrent_client import BitTorrentClient
from .download_worker import DownloadWorker

__all__ = ['BitTorrentClient', 'DownloadWorker'] 