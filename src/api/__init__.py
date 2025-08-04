"""
API layer for Modern BitTorrent Client
"""

from .routes import router
from .app import create_app

__all__ = ['router', 'create_app'] 