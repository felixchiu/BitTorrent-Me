"""
Main application entry point for Modern BitTorrent Client
"""

import uvicorn
from pathlib import Path

from .config.settings import Config
from .api.app import create_app


def main():
    """Main application entry point"""
    # Get settings
    settings = Config.get_settings()
    
    # Create application
    app = create_app(settings)
    
    # Run server
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main() 