"""
FastAPI application factory
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..config.settings import Settings
from ..core.bit_torrent_client import BitTorrentClient
from .routes import router

logger = logging.getLogger(__name__)


def create_app(settings: Settings) -> FastAPI:
    """Create FastAPI application"""
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(settings.log_file),
            logging.StreamHandler()
        ]
    )
    
    # Create FastAPI app
    app = FastAPI(
        title="Modern BitTorrent Client",
        description="A feature-rich BitTorrent client with modern web interface",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize BitTorrent client
    client = BitTorrentClient(settings)
    app.state.client = client
    
    # Include API routes
    app.include_router(router, prefix="/api/v1")
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="templates"), name="static")
    
    # Templates
    templates = Jinja2Templates(directory="templates")
    app.state.templates = templates
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting Modern BitTorrent Client")
        logger.info(f"Download directory: {settings.download_dir}")
        logger.info(f"Server running on {settings.host}:{settings.port}")
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down Modern BitTorrent Client")
    
    return app 