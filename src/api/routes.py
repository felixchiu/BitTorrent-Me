"""
API routes for Modern BitTorrent Client
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..models.api import (
    DownloadSettings, FileSelection, DownloadDirectory, 
    HealthResponse, MetricsResponse
)
from ..core.bit_torrent_client import BitTorrentClient

logger = logging.getLogger(__name__)

router = APIRouter()


def get_client(request: Request) -> BitTorrentClient:
    """Get BitTorrent client from request state"""
    return request.app.state.client


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main web interface"""
    templates = request.app.state.templates
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/upload")
async def upload_torrent(
    file: UploadFile = File(...),
    settings: Optional[DownloadSettings] = None,
    client: BitTorrentClient = Depends(get_client)
):
    """Upload and parse a torrent file"""
    try:
        # Validate file
        if not file.filename.endswith('.torrent'):
            raise HTTPException(status_code=400, detail="Invalid file format. Only .torrent files are supported.")
        
        # Save uploaded file temporarily
        temp_path = Path(f"temp_{file.filename}")
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        try:
            # Parse torrent
            torrent_id, success = client.parse_torrent(temp_path, settings)
            
            if not success:
                raise HTTPException(status_code=400, detail="Failed to parse torrent file")
            
            # Get download info
            download = client.get_download(torrent_id)
            if not download:
                raise HTTPException(status_code=500, detail="Failed to create download")
            
            return {
                "message": f"Parsed torrent: {download.name}",
                "torrent_id": torrent_id,
                "name": download.name,
                "pieces": len(download.pieces),
                "total_size": download.total_size,
                "is_multi_file": download.is_multi_file,
                "files": [f.to_dict() for f in download.files]
            }
            
        finally:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading torrent: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/status")
async def get_status(client: BitTorrentClient = Depends(get_client)):
    """Get status of all downloads"""
    try:
        return client.get_all_status()
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get download status")


@router.get("/start/{torrent_id}")
async def start_download(torrent_id: str, client: BitTorrentClient = Depends(get_client)):
    """Start a specific download"""
    try:
        success = await client.start_download(torrent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Download not found")
        
        return {"message": "Download started"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting download: {e}")
        raise HTTPException(status_code=500, detail="Failed to start download")


@router.get("/pause/{torrent_id}")
async def pause_download(torrent_id: str, client: BitTorrentClient = Depends(get_client)):
    """Pause a specific download"""
    try:
        success = await client.pause_download(torrent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Download not found")
        
        return {"message": "Download paused"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing download: {e}")
        raise HTTPException(status_code=500, detail="Failed to pause download")


@router.get("/resume/{torrent_id}")
async def resume_download(torrent_id: str, client: BitTorrentClient = Depends(get_client)):
    """Resume a specific download"""
    try:
        success = await client.resume_download(torrent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Download not found")
        
        return {"message": "Download resumed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming download: {e}")
        raise HTTPException(status_code=500, detail="Failed to resume download")


@router.get("/stop/{torrent_id}")
async def stop_download(torrent_id: str, client: BitTorrentClient = Depends(get_client)):
    """Stop a specific download"""
    try:
        success = await client.stop_download(torrent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Download not found")
        
        return {"message": "Download stopped"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping download: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop download")


@router.get("/remove/{torrent_id}")
async def remove_download(torrent_id: str, client: BitTorrentClient = Depends(get_client)):
    """Remove a specific download"""
    try:
        success = client.remove_download(torrent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Download not found")
        
        return {"message": "Download removed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing download: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove download")


@router.get("/files/{torrent_id}")
async def get_file_selection(torrent_id: str, client: BitTorrentClient = Depends(get_client)):
    """Get file selection for a specific download"""
    try:
        selection = client.get_file_selection(torrent_id)
        if selection is None:
            raise HTTPException(status_code=404, detail="Download not found")
        
        return selection
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file selection: {e}")
        raise HTTPException(status_code=500, detail="Failed to get file selection")


@router.post("/files/{torrent_id}")
async def update_file_selection(
    torrent_id: str, 
    file_selection: FileSelection,
    client: BitTorrentClient = Depends(get_client)
):
    """Update file selection for a specific download"""
    try:
        success = client.update_file_selection(torrent_id, file_selection.file_selections)
        if not success:
            raise HTTPException(status_code=404, detail="Download not found")
        
        return {"message": "File selection updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating file selection: {e}")
        raise HTTPException(status_code=500, detail="Failed to update file selection")


@router.post("/settings/{torrent_id}")
async def update_download_settings(
    torrent_id: str,
    settings: DownloadSettings,
    client: BitTorrentClient = Depends(get_client)
):
    """Update download settings for a specific download"""
    try:
        success = client.update_download_settings(torrent_id, settings)
        if not success:
            raise HTTPException(status_code=404, detail="Download not found")
        
        return {"message": "Download settings updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating download settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update download settings")


@router.post("/set-download-dir")
async def set_download_directory(
    directory: DownloadDirectory,
    client: BitTorrentClient = Depends(get_client)
):
    """Set custom download directory"""
    try:
        success = client.set_download_directory(directory.directory)
        if not success:
            raise HTTPException(status_code=400, detail="Invalid directory path")
        
        return {"message": "Download directory updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting download directory: {e}")
        raise HTTPException(status_code=500, detail="Failed to set download directory")


@router.get("/get-download-dir")
async def get_download_directory(client: BitTorrentClient = Depends(get_client)):
    """Get current download directory"""
    try:
        directory = client.get_download_directory()
        return {"directory": directory}
    except Exception as e:
        logger.error(f"Error getting download directory: {e}")
        raise HTTPException(status_code=500, detail="Failed to get download directory")


@router.get("/health", response_model=HealthResponse)
async def health_check(client: BitTorrentClient = Depends(get_client)):
    """Health check endpoint"""
    try:
        return client.get_health_status()
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(client: BitTorrentClient = Depends(get_client)):
    """Get application metrics"""
    try:
        return client.get_metrics()
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics") 